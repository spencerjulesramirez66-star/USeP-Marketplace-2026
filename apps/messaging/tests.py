from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from .link_previews import _MetadataParser, _clean_drive_title, _google_drive_preview, _is_safe_url, _site_fallback_preview, _youtube_preview
from .message_urls import extract_message_urls
from .templatetags.message_links import message_links


class MessageLinksTests(SimpleTestCase):
    def test_urlize_makes_http_https_and_www_links_safe(self):
        rendered = str(message_links(
            'Visit https://example.com, http://example.org or www.example.net.'
        ))

        self.assertEqual(rendered.count('<a '), 3)
        self.assertIn('href="https://example.com"', rendered)
        self.assertIn('href="http://example.org"', rendered)
        self.assertIn('href="https://www.example.net"', rendered)
        self.assertIn('target="_blank"', rendered)
        self.assertIn('rel="noopener noreferrer nofollow"', rendered)

    def test_urlize_escapes_message_html(self):
        rendered = str(message_links('<script>alert(1)</script> https://example.com'))

        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('href="https://example.com"', rendered)

    def test_bare_domains_render_as_https_links(self):
        rendered = str(message_links('Check youtube.com and www.facebook.com'))

        self.assertIn('href="https://youtube.com"', rendered)
        self.assertIn('href="https://www.facebook.com"', rendered)

    def test_shared_url_extraction_matches_chat_linkification(self):
        urls = extract_message_urls(
            'Watch youtube.com/watch?v=123, then https://example.com/item?size=large#details.'
        )

        self.assertEqual(urls, [
            'https://youtube.com/watch?v=123',
            'https://example.com/item?size=large#details',
        ])

    def test_markdown_emoji_asset_does_not_hide_a_following_drive_link(self):
        message = (
            'Good morning everyone..[😀](https://static.xx.fbcdn.net/images/emoji.php/'
            'v9/tce/1/16/1f600.png)..https://drive.google.com/drive/folders/'
            '1S5q26dMrG5-IjwD4VA58KolEjtbnKtI3?usp=sharing'
        )

        self.assertEqual(extract_message_urls(message), [
            'https://static.xx.fbcdn.net/images/emoji.php/v9/tce/1/16/1f600.png',
            'https://drive.google.com/drive/folders/1S5q26dMrG5-IjwD4VA58KolEjtbnKtI3?usp=sharing',
        ])
        from .message_urls import extract_meaningful_message_urls
        self.assertEqual(extract_meaningful_message_urls(message), [
            'https://drive.google.com/drive/folders/1S5q26dMrG5-IjwD4VA58KolEjtbnKtI3?usp=sharing',
        ])

    def test_plain_image_url_remains_a_meaningful_shared_link(self):
        from .message_urls import extract_meaningful_message_urls

        self.assertEqual(
            extract_meaningful_message_urls('https://example.com/image.jpg'),
            ['https://example.com/image.jpg'],
        )


class LinkPreviewSafetyTests(SimpleTestCase):
    def test_private_and_unsupported_urls_are_rejected(self):
        self.assertFalse(_is_safe_url('http://127.0.0.1/admin'))
        self.assertFalse(_is_safe_url('http://[::1]/'))
        self.assertFalse(_is_safe_url('file:///etc/passwd'))

    @patch('apps.messaging.link_previews.build_opener')
    def test_youtube_urls_use_the_oembed_video_title(self, mock_build_opener):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"title": "Actual Video Title"}'
        mock_build_opener.return_value.open.return_value.__enter__.return_value = response

        preview = _youtube_preview('https://youtu.be/dQw4w9WgXcQ')

        self.assertEqual(preview['site_name'], 'YouTube')
        self.assertEqual(preview['title'], 'Actual Video Title')
        self.assertIn('/dQw4w9WgXcQ/', preview['image'])

    @patch('apps.messaging.link_previews.build_opener')
    def test_youtube_shorts_urls_are_supported(self, mock_build_opener):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"title": "Short Title"}'
        mock_build_opener.return_value.open.return_value.__enter__.return_value = response

        preview = _youtube_preview('https://www.youtube.com/shorts/dQw4w9WgXcQ')

        self.assertEqual(preview['title'], 'Short Title')
        self.assertIn('/dQw4w9WgXcQ/', preview['image'])

    def test_generic_metadata_parser_prefers_open_graph_fields(self):
        parser = _MetadataParser()
        parser.feed('''
            <title>Fallback title</title>
            <meta property="og:title" content="Open Graph title">
            <meta property="og:image" content="/images/article.jpg">
            <meta property="og:description" content="Tom &amp; Jerry">
            <meta property="og:site_name" content="Example News">
            <link rel="icon" href="/favicon.ico">
        ''')

        self.assertEqual(parser.meta['og:title'], 'Open Graph title')
        self.assertEqual(parser.meta['og:image'], '/images/article.jpg')
        self.assertEqual(parser.meta['og:description'], 'Tom & Jerry')
        self.assertEqual(parser.meta['og:site_name'], 'Example News')
        self.assertEqual(parser.title.strip(), 'Fallback title')
        self.assertEqual(parser.icon, '/favicon.ico')

    def test_google_drive_has_a_safe_visual_fallback(self):
        preview = _google_drive_preview('https://drive.google.com/drive/folders/example')

        self.assertEqual(preview['title'], 'Google Drive folder')
        self.assertEqual(preview['site_name'], 'Google Drive')
        self.assertIn('gstatic.com', preview['favicon'])

    def test_drive_page_titles_drop_only_the_google_drive_suffix(self):
        self.assertEqual(_clean_drive_title('Assembly Photos - Google Drive'), 'Assembly Photos')
        self.assertEqual(_clean_drive_title('Google Drive'), 'Google Drive')

    def test_site_fallback_has_a_compact_favicon(self):
        preview = _site_fallback_preview('https://www.facebook.com')

        self.assertEqual(preview['title'], 'facebook.com')
        self.assertEqual(preview['favicon'], 'https://facebook.com/favicon.ico')
