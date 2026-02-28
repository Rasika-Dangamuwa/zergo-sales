"""
Custom template filters for products app
"""
from django import template

register = template.Library()

@register.filter(name='abs_value')
def abs_value(value):
    """Return the absolute value of a number"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value
