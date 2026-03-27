from django import template

register = template.Library()


@register.simple_tag
def qs_drop(request, key, value):
    """Build query string for the current GET, removing one value from the given key."""
    q = request.GET.copy()
    vals = [v for v in q.getlist(key) if str(v) != str(value)]
    if vals:
        q.setlist(key, vals)
    else:
        q.pop(key, None)
    return q.urlencode()
