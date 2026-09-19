"""Safe, bounded metadata retrieval for message link previews."""
from html.parser import HTMLParser
import ipaddress
import json
import socket
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.core.cache import cache


MAX_RESPONSE_BYTES = 512 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class _SafeRedirect(HTTPRedirectHandler):
    max_redirections = 3

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not _is_safe_url(newurl):
            return None
        return Request(newurl, headers={'User-Agent': 'USeP-Marketplace-LinkPreview/1.0'})


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.title = ''
        self.icon = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'meta':
            key = (attributes.get('property') or attributes.get('name') or '').lower()
            content = attributes.get('content')
            if key and content and key not in self.meta:
                self.meta[key] = content.strip()
        elif tag == 'title':
            self._in_title = True
        elif tag == 'link' and not self.icon:
            rel = attributes.get('rel', '').lower()
            if 'icon' in rel and attributes.get('href'):
                self.icon = attributes['href'].strip()

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def _is_safe_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return False
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, None)}
        return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)
    except (OSError, ValueError):
        return False


def _youtube_preview(url):
    parsed = urlparse(url)
    video_id = ''
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        video_id = parsed.path.strip('/').split('/')[0]
    elif parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        path_parts = parsed.path.strip('/').split('/')
        video_id = path_parts[1] if len(path_parts) > 1 and path_parts[0] == 'shorts' else parse_qs(parsed.query).get('v', [''])[0]
    if not video_id or not video_id.replace('-', '').replace('_', '').isalnum():
        return None
    title = 'YouTube video'
    try:
        oembed_url = f'https://www.youtube.com/oembed?{urlencode({"url": url, "format": "json"})}'
        opener = build_opener(_NoRedirect)
        request = Request(oembed_url, headers={'User-Agent': 'USeP-Marketplace-LinkPreview/1.0'})
        with opener.open(request, timeout=3) as response:
            if response.status != 200:
                raise ValueError('YouTube oEmbed request failed')
            content = response.read(64 * 1024 + 1)
            if len(content) > 64 * 1024:
                raise ValueError('YouTube oEmbed response is too large')
        title = json.loads(content.decode('utf-8')).get('title', '').strip() or title
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        pass
    return {
        'url': url,
        'title': title,
        'site_name': 'YouTube',
        'description': '',
        'image': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
    }


def _google_drive_preview(url):
    hostname = urlparse(url).hostname or ''
    if hostname not in ('drive.google.com', 'www.drive.google.com'):
        return None
    resource_type = 'folder' if '/folders/' in urlparse(url).path else 'file'
    return {
        'url': url,
        'title': f'Google Drive {resource_type}',
        'site_name': 'Google Drive',
        'description': '',
        'image': '',
        'favicon': 'https://ssl.gstatic.com/docs/doclist/images/drive_2022q3_32dp.png',
    }


def _site_fallback_preview(url):
    parsed = urlparse(url)
    hostname = (parsed.hostname or '').removeprefix('www.')
    return {
        'url': url,
        'title': hostname,
        'site_name': hostname,
        'description': '',
        'image': '',
        'favicon': f'https://{hostname}/favicon.ico',
    }


def _clean_drive_title(title):
    for suffix in (' - Google Drive', ' | Google Drive'):
        if title.endswith(suffix):
            return title[:-len(suffix)].strip()
    return title.strip()


def get_link_preview(url):
    """Return sanitized Open Graph data or None; never raise to message sending."""
    if not _is_safe_url(url):
        return None
    cached = cache.get(f'link-preview:{url}')
    if cached is not None and not (
        cached and cached.get('site_name') == 'YouTube' and cached.get('title') == 'YouTube video'
    ):
        return cached or None

    preview = _youtube_preview(url)
    if preview is None:
        try:
            opener = build_opener(_SafeRedirect)
            request = Request(url, headers={'User-Agent': 'USeP-Marketplace-LinkPreview/1.0'})
            with opener.open(request, timeout=3) as response:
                if response.status != 200 or 'text/html' not in response.headers.get('Content-Type', '').lower():
                    raise ValueError('Not an HTML page')
                content = response.read(MAX_RESPONSE_BYTES + 1)
                if len(content) > MAX_RESPONSE_BYTES:
                    raise ValueError('Page is too large')
                parser = _MetadataParser()
                parser.feed(content.decode(response.headers.get_content_charset() or 'utf-8', errors='replace'))
            parsed = urlparse(url)
            image_url = parser.meta.get('og:image') or parser.meta.get('twitter:image') or parser.meta.get('twitter:image:src') or ''
            image_url = urljoin(response.geturl(), image_url) if image_url else ''
            if image_url and not _is_safe_url(image_url):
                image_url = ''
            favicon_url = urljoin(response.geturl(), parser.icon) if parser.icon else ''
            if favicon_url and not _is_safe_url(favicon_url):
                favicon_url = ''
            title = parser.meta.get('og:title') or parser.meta.get('twitter:title') or parser.title.strip() or parsed.hostname
            drive_fallback = _google_drive_preview(url)
            if drive_fallback:
                title = _clean_drive_title(title)
                if title in (parsed.hostname, 'Google Drive', 'Drive'):
                    title = drive_fallback['title']
            preview = {
                'url': url,
                'title': title,
                'site_name': parser.meta.get('og:site_name') or parsed.hostname.removeprefix('www.'),
                'description': parser.meta.get('og:description') or parser.meta.get('description') or '',
                'image': image_url,
                'favicon': favicon_url or _site_fallback_preview(url)['favicon'],
            }
            if drive_fallback:
                preview['site_name'] = 'Google Drive'
                preview['favicon'] = preview['favicon'] or drive_fallback['favicon']
        except (OSError, ValueError, UnicodeError):
            preview = _google_drive_preview(url) or _site_fallback_preview(url)
    cache.set(f'link-preview:{url}', preview or False, 60 * 60)
    return preview
