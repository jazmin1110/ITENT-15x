"""Centralized choice lists shared across apps."""

METRO_MANILA_CITIES = [
    "Las Piñas",
    "Makati",
    "Muntinlupa",
    "Parañaque",
    "Pasay",
    "Taguig",
    "Pateros",
    "Caloocan",
    "Malabon",
    "Navotas",
    "Valenzuela",
    "Quezon City",
    "Mandaluyong",
    "Marikina",
    "Pasig",
    "San Juan",
    "Manila",
]

CITY_CHOICES = [(c, c) for c in METRO_MANILA_CITIES]

GENDER_CHOICES = [
    ('female', 'Female'),
    ('male', 'Male'),
    ('non_binary', 'Non-binary'),
    ('prefer_not_to_say', 'Prefer not to say'),
    ('self_describe', 'Self-describe'),
]

MARITAL_STATUS_CHOICES = [
    ('', '—'),
    ('single', 'Single'),
    ('married', 'Married'),
    ('divorced', 'Divorced'),
    ('widowed', 'Widowed'),
    ('separated', 'Separated'),
]
