import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

URL_RE = re.compile(r'(https?://[^\s<>"\']+)')


@register.filter(name='message_links')
@register.filter(name='linkify')
def linkify(value):
    """Escape message text, then turn URLs into safe clickable links."""
    if not value:
        return ""

    def _replace(match):
        url = match.group(1)
        trailing = ""
        while url and url[-1] in ".,;:!?)":
            trailing = url[-1] + trailing
            url = url[:-1]
        return (
            f'<a href="{url}" target="_blank" '
            f'rel="noopener noreferrer">{url}</a>{trailing}'
        )

    return mark_safe(URL_RE.sub(_replace, escape(value)).replace("\n", "<br>"))