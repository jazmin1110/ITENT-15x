from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .permissions import is_platform_admin


def staff_member_required(view_func):
    """Require login and platform admin (role admin or superuser)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_platform_admin(request.user):
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return _wrapped
