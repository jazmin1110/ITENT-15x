"""Per-skill work photos on WorkerPortfolioItem (related_skill = canonical skill name)."""
from __future__ import annotations

from collections import defaultdict

from django.core.exceptions import ValidationError

from jobs.skill_utils import PREDEFINED_SKILL_CODES, canonical_predefined_skill

from .models import WorkerPortfolioItem

PORTFOLIO_PHOTO_MAX_BYTES = 2 * 1024 * 1024
WORKER_PORTFOLIO_MAX_ITEMS = 40
MAX_NEW_PHOTOS_PER_SKILL_PER_SAVE = 8


def build_portfolio_map(profile) -> dict[str, list]:
    """Map canonical skill key -> list of WorkerPortfolioItem (photo rows)."""
    if not profile or not profile.pk:
        return {}
    m: dict[str, list] = defaultdict(list)
    for item in profile.portfolio_items.all():
        raw = (item.related_skill or '').strip()
        if not raw:
            continue
        key = canonical_predefined_skill(raw) or raw
        m[key].append(item)
    return dict(m)


def _validate_image_upload(f) -> None:
    if f.size > PORTFOLIO_PHOTO_MAX_BYTES:
        raise ValidationError('Masyadong malaki ang isa sa mga larawan (max 2MB bawat file).')
    ct = (getattr(f, 'content_type', None) or '').lower()
    if ct and not ct.startswith('image/'):
        raise ValidationError('Mga larawan lang (JPEG, PNG, GIF, WebP).')


def process_skill_portfolio_uploads(request, profile) -> None:
    """
    Handle delete_portfolio IDs, skill_photo_<Code> files, and custom_skill_photo_<i> files.
    Called after WorkerProfileForm save (profile is saved).
    """
    if not profile or not profile.pk:
        return

    # Deletes
    for pid in request.POST.getlist('delete_portfolio'):
        try:
            pk = int(pid)
        except (TypeError, ValueError):
            continue
        WorkerPortfolioItem.objects.filter(pk=pk, worker_profile=profile).delete()

    current_count = WorkerPortfolioItem.objects.filter(worker_profile=profile).count()
    if current_count >= WORKER_PORTFOLIO_MAX_ITEMS:
        return

    # Predefined skills
    for code in PREDEFINED_SKILL_CODES:
        key = f'skill_photo_{code}'
        files = request.FILES.getlist(key)
        for f in files[:MAX_NEW_PHOTOS_PER_SKILL_PER_SAVE]:
            if current_count >= WORKER_PORTFOLIO_MAX_ITEMS:
                return
            _validate_image_upload(f)
            WorkerPortfolioItem.objects.create(
                worker_profile=profile,
                related_skill=code,
                photo=f,
            )
            current_count += 1

    # Custom skill rows (index matches POST order)
    names = []
    if hasattr(request.POST, 'getlist'):
        names = request.POST.getlist('custom_skill_name')
    else:
        names = request.POST.get('custom_skill_name') or []
        if isinstance(names, str):
            names = [names]

    for i, raw_name in enumerate(names):
        name = (raw_name or '').strip()
        if not name:
            continue
        skill_key = canonical_predefined_skill(name) or name
        field = f'custom_skill_photo_{i}'
        files = request.FILES.getlist(field)
        for f in files[:MAX_NEW_PHOTOS_PER_SKILL_PER_SAVE]:
            if current_count >= WORKER_PORTFOLIO_MAX_ITEMS:
                return
            _validate_image_upload(f)
            WorkerPortfolioItem.objects.create(
                worker_profile=profile,
                related_skill=skill_key,
                photo=f,
            )
            current_count += 1
