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


def normalize_skill_entries(raw) -> list[dict]:
    """Return a list of {\"skill\": str, \"years_experience\": int | None} for templates."""
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
            out.append({'skill': item['skill'], 'years_experience': y})
    return out
