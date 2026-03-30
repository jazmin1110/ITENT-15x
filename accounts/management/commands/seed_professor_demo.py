"""
Purge all users except a keep-list (phones + superusers), then seed professor demo data.

Usage:
  python manage.py seed_professor_demo --force

Refuses without --force (destructive).
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from accounts.models import User, WorkerProfile, EmployerProfile
from jobs.models import Job, Application, ApplicationContract

PROTECTED_PHONES = frozenset(
    {'09173010251', '09177988286', '09778137452'}
)

DEMO_PASSWORD = 'ProfDemo2026!'

# Account phones (also usernames)
JOLLY_PHONE = '09178153228'
FOURACES_PHONE = '09178332328'

# Demo workers: avoid protected + employer phones
WORKER_SEEDS = [
    # (phone, full_name, city, skills_json, apply_job_key or None, app_status or None)
    # apply_job_key: jolly_td, jolly_janitor, jolly_sewer, fouraces_td
    (
        '09178501001',
        'Rommel Bautista',
        'Quezon City',
        [{'skill': 'Masonry', 'years_experience': 4}, {'skill': 'Helper', 'years_experience': 2}],
        None,
        None,
    ),
    (
        '09178501002',
        'Angeline Mercado',
        'Makati',
        [{'skill': 'Painting', 'years_experience': 3}],
        None,
        None,
    ),
    (
        '09178501003',
        'Joseph Dela Cruz',
        'Pasig',
        [{'skill': 'Carpentry', 'years_experience': 6}],
        None,
        None,
    ),
    (
        '09178501004',
        'Mario Reyes',
        'Valenzuela',
        [{'skill': 'Driver', 'years_experience': 8}],
        'jolly_td',
        'hired',
    ),
    (
        '09178501005',
        'Elena Santos',
        'Malabon',
        [{'skill': 'Janitor', 'years_experience': 5}],
        'jolly_janitor',
        'viewed',
    ),
    (
        '09178501006',
        'Carlo Mendoza',
        'Navotas',
        [{'skill': 'Sewer', 'years_experience': 4}],
        'jolly_sewer',
        'shortlisted',
    ),
    (
        '09178501007',
        'Patricia Cruz',
        'Caloocan',
        [{'skill': 'Driver', 'years_experience': 3}],
        'fouraces_td',
        'sent',
    ),
]

SHORT_DESCRIPTION = (
    'Minimum wage: PHP 695 per day (NCR). Work hours 8:00 AM to 5:00 PM. '
    'Contract duration: 6 months.'
)


def _aware_dt(d: date, hour: int = 10, minute: int = 0) -> datetime:
    tz = timezone.get_current_timezone()
    naive = datetime.combine(d, time(hour, minute), tzinfo=None)
    return timezone.make_aware(naive, tz)


def _aware_date_range(start: date, end: date) -> date:
    """Inclusive random date between start and end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


class Command(BaseCommand):
    help = (
        'DANGEROUS: Delete all users except protected phone numbers and superusers, '
        'then create Jolly/FourAces demo employers, 4 jobs, 7 workers, 4 applications '
        '(1 hired with completed contract). Requires --force.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Required. Confirms intentional database wipe + demo seed.',
        )

    def handle(self, *args, **options):
        if not options['force']:
            raise CommandError(
                'This command deletes almost all users. Re-run with --force to proceed.'
            )

        protected = User.objects.filter(
            Q(phone_number__in=PROTECTED_PHONES) | Q(is_superuser=True)
        )
        keep_count = protected.count()
        delete_qs = User.objects.exclude(
            Q(phone_number__in=PROTECTED_PHONES) | Q(is_superuser=True)
        )
        deleted_total, _ = delete_qs.delete()
        self.stdout.write(
            self.style.WARNING(
                f'Purged users (and cascaded data). Deleted row total: {deleted_total}. '
                f'Kept {keep_count} user(s) (protected phones + superusers).'
            )
        )

        # --- Employers ---
        employer_dates = [
            date(2026, 3, 19),
            date(2026, 3, 21),
            date(2026, 3, 23),
            date(2026, 3, 25),
            date(2026, 3, 26),
        ]
        j_join = _aware_dt(random.choice(employer_dates), 9, 30)
        f_join = _aware_dt(random.choice(employer_dates), 14, 15)

        jolly_user = User.objects.create_user(
            username=JOLLY_PHONE,
            email='',
            password=DEMO_PASSWORD,
            phone_number=JOLLY_PHONE,
            first_name='Raquel',
            last_name='Mendoza',
            role='employer',
        )
        User.objects.filter(pk=jolly_user.pk).update(date_joined=j_join)

        EmployerProfile.objects.create(
            user=jolly_user,
            company_name='Jolly',
            city='Valenzuela City',
            contact_person='Raquel',
            contact_number=JOLLY_PHONE,
            verification_status='verified',
        )

        four_user = User.objects.create_user(
            username=FOURACES_PHONE,
            email='',
            password=DEMO_PASSWORD,
            phone_number=FOURACES_PHONE,
            first_name='Clarissa',
            last_name='Valdez',
            role='employer',
        )
        User.objects.filter(pk=four_user.pk).update(date_joined=f_join)

        EmployerProfile.objects.create(
            user=four_user,
            company_name='FourAces',
            city='Caloocan City',
            contact_person='Clarissa',
            contact_number=FOURACES_PHONE,
            verification_status='verified',
        )

        start_date = date(2026, 4, 1)
        jobs_map = {}

        td_j = Job.objects.create(
            employer=jolly_user,
            title='Truck Driver',
            city='Valenzuela',
            daily_rate=Decimal('695.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=SHORT_DESCRIPTION,
            required_skills=[{'skill': 'Driver', 'years_experience': None}],
            start_date=start_date,
            positions_needed=1,
            status='open',
        )
        jobs_map['jolly_td'] = td_j

        jan_j = Job.objects.create(
            employer=jolly_user,
            title='Janitor',
            city='Valenzuela',
            daily_rate=Decimal('695.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=SHORT_DESCRIPTION,
            required_skills=[{'skill': 'Janitor', 'years_experience': None}],
            start_date=start_date,
            positions_needed=6,
            status='open',
        )
        jobs_map['jolly_janitor'] = jan_j

        sew_j = Job.objects.create(
            employer=jolly_user,
            title='Sewer',
            city='Valenzuela',
            daily_rate=Decimal('695.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=SHORT_DESCRIPTION,
            required_skills=[{'skill': 'Sewer', 'years_experience': None}],
            start_date=start_date,
            positions_needed=2,
            status='open',
        )
        jobs_map['jolly_sewer'] = sew_j

        td_f = Job.objects.create(
            employer=four_user,
            title='Truck Driver',
            city='Caloocan',
            daily_rate=Decimal('695.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=SHORT_DESCRIPTION,
            required_skills=[{'skill': 'Driver', 'years_experience': None}],
            start_date=start_date,
            positions_needed=10,
            status='open',
        )
        jobs_map['fouraces_td'] = td_f

        worker_join_start = date(2026, 3, 27)
        worker_join_end = date(2026, 3, 30)

        for phone, full_name, city, skills, job_key, app_status in WORKER_SEEDS:
            parts = full_name.split(' ', 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ''
            w_user = User.objects.create_user(
                username=phone,
                email='',
                password=DEMO_PASSWORD,
                phone_number=phone,
                first_name=first,
                last_name=last,
                role='worker',
            )
            w_join = _aware_dt(
                _aware_date_range(worker_join_start, worker_join_end),
                random.randint(8, 16),
                random.choice([0, 15, 30, 45]),
            )
            User.objects.filter(pk=w_user.pk).update(date_joined=w_join)

            WorkerProfile.objects.create(
                user=w_user,
                full_name=full_name,
                city=city,
                contact_number=phone,
                years_experience=max(
                    (s.get('years_experience') or 0) for s in skills if isinstance(s, dict)
                )
                or 2,
                skills=skills,
                date_of_birth=date(1992, 5, 10),
                gender='male' if first in ('Rommel', 'Joseph', 'Mario', 'Carlo') else 'female',
                marital_status='single',
                nationality='Filipino',
                religion='',
                languages_known='Filipino, English',
                national_id_status='verified',
                verification_status='verified',
            )

            if job_key and app_status:
                job = jobs_map[job_key]
                app = Application.objects.create(
                    job=job,
                    worker=w_user,
                    status=app_status,
                )
                if app_status == 'hired':
                    ApplicationContract.objects.create(
                        application=app,
                        contract_status=ApplicationContract.STATUS_COMPLETE,
                    )
                    hire_time = _aware_dt(date(2026, 3, 30), 11, 0)
                    Application.objects.filter(pk=app.pk).update(
                        hired_at=hire_time,
                        updated_at=hire_time,
                    )
                # Align application timestamps for believable ordering
                app_created = _aware_dt(
                    _aware_date_range(worker_join_start, worker_join_end),
                    18,
                    0,
                )
                Application.objects.filter(pk=app.pk).update(
                    created_at=app_created,
                    updated_at=app_created,
                )

        self.stdout.write(self.style.SUCCESS('Professor demo seed complete.'))
        self.stdout.write(
            f'Demo login password for all new accounts: {DEMO_PASSWORD}\n'
            f'  Employers: {JOLLY_PHONE} (Jolly), {FOURACES_PHONE} (FourAces)\n'
            f'  Workers: 09178501001–09178501007\n'
            f'Protected phones (unchanged): {", ".join(sorted(PROTECTED_PHONES))}'
        )
