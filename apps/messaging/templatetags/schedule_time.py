from django import template
from django.utils import timezone

from apps.messaging.schedule_config import SCHEDULE_TIMEZONE

register = template.Library()


@register.filter
def pht_datetime(value, date_format='%a, %b %d, %I:%M %p'):
    if not value:
        return ''
    label = timezone.localtime(value, SCHEDULE_TIMEZONE).strftime(date_format).replace(' 0', ' ')
    return f'{label} PHT'
