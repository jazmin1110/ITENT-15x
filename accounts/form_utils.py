"""Helpers for Django forms used in views."""


def first_invalid_field_name(form) -> str | None:
    """First field name with a validation error, in declared field order."""
    if not form.errors:
        return None
    for name in form.fields:
        if name in form.errors:
            return name
    return None
