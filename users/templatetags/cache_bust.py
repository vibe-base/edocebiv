from django import template
import time

register = template.Library()

@register.simple_tag
def cache_bust():
    """
    Returns a timestamp for cache busting.
    Usage: {% load cache_bust %}{% cache_bust %}
    """
    return int(time.time())
