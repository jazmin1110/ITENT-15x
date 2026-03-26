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
