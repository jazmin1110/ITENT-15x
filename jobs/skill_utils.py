"""Normalize job required_skills JSON (legacy list of str or list of objects)."""
from __future__ import annotations

# Shared with JobForm and WorkerProfileForm — keep in sync across the app.
PREDEFINED_SKILL_CHOICES = [
    ('Masonry', 'Masonry'),
    ('Carpentry', 'Carpentry'),
    ('Helper', 'Helper'),
    ('Painting', 'Painting'),
    ('Driver', 'Driver'),
]
PREDEFINED_SKILL_CODES = frozenset(code for code, _ in PREDEFINED_SKILL_CHOICES)

_PREDEFINED_BY_LOWER: dict[str, str] = {code.lower(): code for code in PREDEFINED_SKILL_CODES}


def canonical_predefined_skill(name: str | None) -> str | None:
    """Return the canonical predefined code if name matches case-insensitively, else None."""
    if name is None:
        return None
    key = str(name).strip().lower()
    if not key:
        return None
    return _PREDEFINED_BY_LOWER.get(key)


def required_skill_names(raw) -> set[str]:
    """Return the set of skill names required for a job."""
    if not raw:
        return set()
    names = set()
    for item in raw:
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, dict) and item.get('skill'):
            names.add(item['skill'])
    return names


def _coerce_self_rating(val) -> int | None:
    """Optional 1–5 self-rating; invalid or empty → None."""
    if val is None or val == '':
        return None
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    if 1 <= n <= 5:
        return n
    return None


def normalize_skill_entries(raw) -> list[dict]:
    """Return a list of dicts with skill, years_experience, and optional self_rating (1–5)."""
    if not raw:
        return []
    out = []
    for item in raw:
        if isinstance(item, str):
            out.append({'skill': item, 'years_experience': None})
        elif isinstance(item, dict) and item.get('skill'):
            y = item.get('years_experience')
            if y is not None and y != '':
                try:
                    y = int(y)
                except (TypeError, ValueError):
                    y = None
            else:
                y = None
            row = {'skill': item['skill'], 'years_experience': y}
            sr = _coerce_self_rating(item.get('self_rating'))
            if sr is not None:
                row['self_rating'] = sr
            out.append(row)
    return out
