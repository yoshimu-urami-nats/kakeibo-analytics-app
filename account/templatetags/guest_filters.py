# account\templatetags\guest_filters.py

from django import template

from account.utils.guest_utils import mask_shop_name

register = template.Library()


@register.filter(name="hoge_shop")
def hoge_shop(value: str) -> str:
    return mask_shop_name(value or "")