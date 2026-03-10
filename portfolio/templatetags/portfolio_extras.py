from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def thousands_k(value):
    if value in (None, ""):
        return ""

    try:
        thousands = Decimal(value) / Decimal("1000")
    except (InvalidOperation, TypeError, ValueError):
        return value

    return f"{thousands:,.0f}k"