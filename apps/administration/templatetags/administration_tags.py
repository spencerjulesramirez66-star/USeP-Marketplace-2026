from django import template

from apps.administration.formatters import format_money

register = template.Library()


@register.filter
def money(value):
    return format_money(value)
