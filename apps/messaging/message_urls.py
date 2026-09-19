"""Shared URL extraction for rendered chat messages and conversation details."""
from html import unescape
import re
from urllib.parse import urlparse

from django.template.defaultfilters import urlize


_ANCHOR_RE = re.compile(r'<a href="([^"]+)"(?:[^>]*)>([^<]+)</a>')
_MARKDOWN_DESTINATION_RE = re.compile(r'\[[^\]]*\]\((https?://[^)\s]+)\)', re.IGNORECASE)
_URL_CANDIDATE_RE = re.compile(
    r'''(?ix)(?<![\w@])(?P<url>
        (?:https?://|www\.)[^\s<>\]\)]+ |
        (?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|co|uk|ph|dev|app|info|me|tv|gg|ai|us|ca|de|jp|fr|au|news|site|online|store)(?:[/?#][^\s<>\]\)]*)?
    )'''
)
_TRAILING_PUNCTUATION_RE = re.compile(r'[.,!?;:]+$')


def linkify_message_text(value):
    """Use Django's URL parser as the single recognition rule for messages."""
    return urlize(value or '', autoescape=True)


def _normalise_url(href, label):
    """Match the HTTPS upgrade applied to bare domains in ``message_links``."""
    href = unescape(href)
    label = unescape(label)
    if href.startswith('http://') and label == href.removeprefix('http://'):
        href = f'https://{label}'
    parsed = urlparse(href)
    return href if parsed.scheme in ('http', 'https') and parsed.hostname else None


def _trim_url_punctuation(url):
    url = _TRAILING_PUNCTUATION_RE.sub('', url)
    for opening, closing in (('(', ')'), ('[', ']')):
        while url.endswith(closing) and url.count(closing) > url.count(opening):
            url = url[:-1]
    return url


def extract_message_urls(value):
    """Return every valid URL that Django's chat linkifier recognises, in order."""
    # urlize covers conventional prose. The candidate scan also covers valid
    # URLs immediately following Markdown/punctuation, such as ")]..https".
    candidates = []
    for match in _URL_CANDIDATE_RE.finditer(value or ''):
        raw_url = _trim_url_punctuation(match.group('url'))
        if normalised := _normalise_url(raw_url, raw_url):
            candidates.append((match.start(), normalised))
    linked = linkify_message_text(value)
    search_from = 0
    for index, (href, label) in enumerate(_ANCHOR_RE.findall(linked)):
        if normalised := _normalise_url(href, label):
            position = (value or '').find(unescape(label), search_from)
            if position >= 0:
                search_from = position + len(unescape(label))
            else:
                position = len(value or '') + index
            candidates.append((position, normalised))
    return list(dict.fromkeys(url for _, url in sorted(candidates)).keys())


def _is_rendering_asset_url(url):
    """Recognise known emoji/static assets without excluding ordinary image links."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or '').lower()
    path = parsed.path.lower()
    if hostname == 'static.xx.fbcdn.net' and '/emoji' in path:
        return True
    return (
        (hostname.startswith('static.') or hostname.startswith('cdn.'))
        and any(marker in path for marker in ('/emoji', '/emoticon', '/stickers/'))
    )


def extract_meaningful_message_urls(value):
    """Exclude asset destinations embedded in Markdown while keeping all real links."""
    markdown_assets = {
        normalised
        for destination in _MARKDOWN_DESTINATION_RE.findall(value or '')
        if (normalised := _normalise_url(destination, destination))
        and _is_rendering_asset_url(normalised)
    }
    return [url for url in extract_message_urls(value) if url not in markdown_assets]
