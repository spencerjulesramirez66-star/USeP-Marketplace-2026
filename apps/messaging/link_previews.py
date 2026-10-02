"""Fetches a small amount of metadata (title/image/domain) for a URL a user
pasted into a message, for the link-preview card.

This makes a server-side request to a user-supplied URL, which is a classic
SSRF vector, so every request is restricted:
  * scheme must be http/https
  * the resolved IP must be a public address (no loopback/private/link-local)
  * redirects are re-checked the same way, not followed blindly
  * a short timeout and a small byte cap
"""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests

REQUEST_TIMEOUT_SECONDS = 4
MAX_RESPONSE_BYTES = 512 * 1024
MAX_REDIRECTS = 3
USER_AGENT = 'USePMarketplaceLinkPreview/1.0 (+https://usepmarketplace.example)'

_META_TAG = re.compile(rb'<meta[^>]+>', re.IGNORECASE)
_PROPERTY = re.compile(rb'(?:property|name)=["\'](og:title|og:image|og:site_name|twitter:title|twitter:image)["\']', re.IGNORECASE)
_CONTENT = re.compile(rb'content=["\']([^"\']*)["\']', re.IGNORECASE)
_TITLE_TAG = re.compile(rb'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)


class UnsafeURLError(Exception):
    pass


def _assert_public_host(hostname):
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as error:
        raise UnsafeURLError('Could not resolve host.') from error

    for family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified
        ):
            raise UnsafeURLError('That host is not reachable for previews.')


def _assert_safe_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise UnsafeURLError('Only http/https links can be previewed.')
    if not parsed.hostname:
        raise UnsafeURLError('Invalid URL.')
    _assert_public_host(parsed.hostname)
    return parsed


def _fetch(url):
    """A manual, capped redirect loop: each hop is re-validated so a public
    URL can't redirect to an internal address."""
    for _ in range(MAX_REDIRECTS + 1):
        _assert_safe_url(url)
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'},
            timeout=REQUEST_TIMEOUT_SECONDS,
            stream=True,
            allow_redirects=False,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get('Location')
            response.close()
            if not location:
                raise UnsafeURLError('Redirected without a destination.')
            url = urljoin(url, location)
            continue

        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            response.close()
            return None

        chunks, total = [], 0
        for chunk in response.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                break
            chunks.append(chunk)
        response.close()
        return b''.join(chunks)

    raise UnsafeURLError('Too many redirects.')


def _extract_meta(html_bytes):
    values = {}
    for tag in _META_TAG.findall(html_bytes):
        prop_match = _PROPERTY.search(tag)
        content_match = _CONTENT.search(tag)
        if prop_match and content_match:
            values.setdefault(prop_match.group(1).lower().decode(), content_match.group(1).decode('utf-8', 'ignore'))
    title_match = _TITLE_TAG.search(html_bytes)
    if title_match and 'og:title' not in values:
        values['title_tag'] = re.sub(rb'\s+', b' ', title_match.group(1)).strip().decode('utf-8', 'ignore')
    return values


def get_link_preview(url):
    """Return {'url', 'title', 'image', 'domain'} or None if unavailable."""
    try:
        html_bytes = _fetch(url)
    except (UnsafeURLError, requests.RequestException):
        return None
    if not html_bytes:
        return None

    meta = _extract_meta(html_bytes)
    domain = urlparse(url).netloc.lower().removeprefix('www.')
    title = meta.get('og:title') or meta.get('twitter:title') or meta.get('title_tag') or domain
    image = meta.get('og:image') or meta.get('twitter:image')
    if image:
        image = urljoin(url, image)
        try:
            _assert_safe_url(image)  # the image URL gets embedded in the page too
        except UnsafeURLError:
            image = None

    return {'url': url, 'title': title[:200], 'image': image, 'domain': domain}
