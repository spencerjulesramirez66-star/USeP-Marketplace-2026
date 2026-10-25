from decimal import Decimal

from django.utils import timezone

from .transaction_queries import ADMIN_TIMEZONE


def format_money(value):
    amount = Decimal('0') if value is None else Decimal(value)

    formatted = f'{amount:,.2f}'
    if formatted.endswith('.00'):
        formatted = formatted[:-3]
    return f'₱{formatted}'


def local_datetime(value):
    if value is None:
        return ''
    return timezone.localtime(value, ADMIN_TIMEZONE)


def local_datetime_iso(value):
    local_value = local_datetime(value)
    return local_value.isoformat() if local_value else ''


def local_datetime_display(value):
    local_value = local_datetime(value)
    if not local_value:
        return ''
    hour = local_value.strftime('%I').lstrip('0')
    return f'{local_value:%b} {local_value.day}, {local_value:%Y} {hour}:{local_value:%M} {local_value:%p} PHT'
