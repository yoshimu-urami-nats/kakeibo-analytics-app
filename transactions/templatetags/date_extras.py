from django import template

register = template.Library()

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]

@register.filter
def weekday_ja(value):
    if not value:
        return ""
    return WEEKDAYS_JA[value.weekday()]