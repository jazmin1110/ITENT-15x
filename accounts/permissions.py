"""Shared access checks for staff / platform admin features."""


def is_platform_admin(user):
    """True if user may access in-app staff console (role admin or Django superuser)."""
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)
