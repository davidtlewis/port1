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


@register.filter
def signed_thousands_k(value):
    if value in (None, ""):
        return ""

    try:
        thousands = Decimal(value) / Decimal("1000")
    except (InvalidOperation, TypeError, ValueError):
        return value

    if thousands > 0:
        return f"+{thousands:,.0f}k"
    if thousands < 0:
        return f"-{abs(thousands):,.0f}k"
    return "0k"