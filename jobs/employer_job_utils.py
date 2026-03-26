"""Employer-only job state: auto-close when filled, vacancy reopen banner."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Max
from django.utils import timezone


def hired_count_for_job(job) -> int:
    """Active hires for capacity (status hired only, not completed)."""
    from .models import Application

    return Application.objects.filter(job=job, status='hired').count()


@transaction.atomic
def maybe_autoclose_job_when_filled(job) -> None:
    """Close listing when hired count reaches positions_needed (call inside hiring flow)."""
    from .models import Job

    job = Job.objects.select_for_update().get(pk=job.pk)
    if hired_count_for_job(job) >= job.positions_needed:
        job.status = 'closed'
        job.auto_closed_when_filled = True
        job.save(update_fields=['status', 'auto_closed_when_filled', 'updated_at'])


def latest_completed_at(job):
    from .models import Application

    agg = Application.objects.filter(job=job, status='completed').aggregate(
        m=Max('updated_at'),
    )
    return agg['m']


def show_vacancy_reopen_banner(job) -> bool:
    """
    Employer sees reopen/keep-closed prompt when listing was auto-closed for fill
    but there is now a headcount vacancy (e.g. a hire moved to completed).
    """
    if not job.auto_closed_when_filled or job.status != 'closed':
        return False
    if hired_count_for_job(job) >= job.positions_needed:
        return False
    latest = latest_completed_at(job)
    if latest is None:
        return False
    ack = job.employer_acknowledged_vacancy_at
    if ack is None or latest > ack:
        return True
    return False


def reopen_job_listing(job) -> None:
    job.status = 'open'
    job.auto_closed_when_filled = False
    job.employer_acknowledged_vacancy_at = None
    job.save(
        update_fields=[
            'status',
            'auto_closed_when_filled',
            'employer_acknowledged_vacancy_at',
            'updated_at',
        ]
    )


def acknowledge_vacancy_keep_closed(job) -> None:
    job.employer_acknowledged_vacancy_at = timezone.now()
    job.save(update_fields=['employer_acknowledged_vacancy_at', 'updated_at'])
