from django import template
import re
from django.template.defaultfilters import linebreaksbr
from django.utils.safestring import mark_safe

from apps.messaging.message_urls import _normalise_url, linkify_message_text


register = template.Library()


@register.filter(is_safe=True)
def message_links(value):
    """Linkify only URLs using Django's escaped URL utility."""
    linked = linkify_message_text(value)
    linked = linked.replace(
        '<a href=',
        '<a target="_blank" rel="noopener noreferrer nofollow" href=',
    ).replace(
        ' rel="nofollow"',
        '',
    )
    # Django urlize defaults bare domains to HTTP. Preserve explicitly typed
    # protocols, but upgrade only anchors whose visible text was a bare domain.
    def use_https_for_bare_domain(match):
        href, label = match.groups()
        normalised = _normalise_url(href, label)
        if normalised and normalised != href:
            return f'<a target="_blank" rel="noopener noreferrer nofollow" href="{normalised}">{label}</a>'
        return match.group(0)

    linked = re.sub(
        r'<a target="_blank" rel="noopener noreferrer nofollow" href="(http://[^"]+)">([^<]+)</a>',
        use_https_for_bare_domain,
        linked,
    )
    return mark_safe(linebreaksbr(linked, autoescape=False))
