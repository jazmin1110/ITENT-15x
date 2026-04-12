"""
Purge all users except a keep-list (phones + superusers), then seed professor demo data.

Five employers (unique join dates Mar 22–Apr 8, 2026), Jolly/FourAces plus three new companies with jobs.
Ten worker profiles (unique join dates Mar 29–Apr 10, 2026). Three hired placements
(one employer each), seven workers with 1–2 mixed-status applications, sample chats.
Workers are not verified. All job posts timestamped before Apr 10, 2026.

Usage:
  python manage.py seed_professor_demo --force

Refuses without --force (destructive).
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import User, WorkerProfile, EmployerProfile
from chat.models import Conversation, Message
from jobs.employer_job_utils import maybe_autoclose_job_when_filled
from jobs.models import Application, ApplicationContract, Job

PROTECTED_PHONES = frozenset(
    {'09173010251', '09177988286', '09778137452'}
)

DEMO_PASSWORD = 'ProfDemo2026!'

# Account phones (also usernames)
JOLLY_PHONE = '09178153228'
FOURACES_PHONE = '09178332328'
EGLOBAL_PHONE = '09173090545'
NEWPRO_PHONE = '09175202420'
HANDO_PHONE = '09178961965'

# Demo workers (10): unique signup dates (Mar 29–Apr 10, 2026). Tuple: phone, name, city, skills, signup_date
WORKER_SEEDS = [
    (
        '09184729356',
        'Darnell Ortega',
        'Quezon City',
        [{'skill': 'Masonry', 'years_experience': 4}, {'skill': 'Helper', 'years_experience': 2}],
        date(2026, 3, 29),
    ),
    (
        '09451287319',
        'Vince Calderon',
        'Valenzuela',
        [{'skill': 'Driver', 'years_experience': 8}],
        date(2026, 3, 30),
    ),
    (
        '09951238467',
        'Charmaine Tolentino',
        'Malabon',
        [{'skill': 'Janitor', 'years_experience': 5}],
        date(2026, 3, 31),
    ),
    (
        '09294817230',
        'Rico Navarro',
        'Manila',
        [{'skill': 'Carpentry', 'years_experience': 6}],
        date(2026, 4, 1),
    ),
    (
        '09051239482',
        'Janine Mercado',
        'Calamba, Laguna',
        [{'skill': 'Electrician', 'years_experience': 4}],
        date(2026, 4, 2),
    ),
    (
        '09673829174',
        'Buddy Lacson',
        'Muntinlupa',
        [{'skill': 'Machine Operator', 'years_experience': 3}],
        date(2026, 4, 3),
    ),
    (
        '09219384765',
        'Sophia Uy',
        'Pasig',
        [{'skill': 'Plumber', 'years_experience': 5}],
        date(2026, 4, 5),
    ),
    (
        '09166372840',
        'Lorenzo Abad',
        'Marikina',
        [{'skill': 'Sewer', 'years_experience': 4}],
        date(2026, 4, 6),
    ),
    (
        '09572819463',
        'Irish Fernandez',
        'Las Piñas',
        [{'skill': 'Furniture Assembler', 'years_experience': 2}],
        date(2026, 4, 8),
    ),
    (
        '09483927158',
        'Harold Sy',
        'Taguig',
        [{'skill': 'Electrician', 'years_experience': 4}],
        date(2026, 4, 10),
    ),
]

# One hire per employer: Jolly (driver), eGlobal (carpenter), Newpro (machine op). Phone -> job key.
HIRED_PLACEMENTS = [
    ('09451287319', 'jolly_td'),
    ('09294817230', 'eg_carp'),
    ('09673829174', 'np_mach'),
]

# Workers not in HIRED_PLACEMENTS: 1–2 applications each (phone, job_key, status).
# "sent" = employer not viewed yet in pipeline terms.
EXTRA_APPLICATIONS = [
    ('09184729356', 'jolly_janitor', 'sent'),
    ('09184729356', 'fouraces_td', 'viewed'),
    ('09951238467', 'jolly_janitor', 'sent'),
    ('09951238467', 'fouraces_td', 'viewed'),
    ('09051239482', 'np_elec', 'shortlisted'),
    ('09051239482', 'eg_elec', 'viewed'),
    ('09219384765', 'eg_plumb', 'viewed'),
    ('09219384765', 'np_elec', 'sent'),
    ('09166372840', 'jolly_sewer', 'viewed'),
    ('09166372840', 'jolly_janitor', 'sent'),
    ('09572819463', 'ho_fasm', 'sent'),
    ('09572819463', 'ho_drv', 'shortlisted'),
    ('09483927158', 'np_elec', 'sent'),
    ('09483927158', 'eg_elec', 'viewed'),
]

# Chats for three non-hired applications (phone, job_key) -> CONVO_SCRIPTS key
CONVO_FOR_APPLICATIONS = [
    ('09051239482', 'np_elec', 'np_elec'),
    ('09951238467', 'jolly_janitor', 'jolly_janitor'),
    ('09572819463', 'ho_fasm', 'ho_fasm'),
]

SHORT_DESCRIPTION = (
    'Minimum wage: PHP 695 per day (NCR). Work hours 8:00 AM to 5:00 PM. '
    'Contract duration: 6 months.'
)


def _random_clock_time() -> time:
    """Plausible daytime / early evening registration activity."""
    return time(
        random.randint(6, 22),
        random.randint(0, 59),
        random.randint(0, 59),
    )


def _aware_dt(d: date, hour: int = 10, minute: int = 0, second: int = 0) -> datetime:
    tz = timezone.get_current_timezone()
    naive = datetime.combine(d, time(hour, minute, second), tzinfo=None)
    return timezone.make_aware(naive, tz)


def _aware_random_on_date(d: date) -> datetime:
    """Timezone-aware datetime on a calendar day with random clock time."""
    t = _random_clock_time()
    return _aware_dt(d, t.hour, t.minute, t.second)


def _aware_date_range(start: date, end: date) -> date:
    """Inclusive random date between start and end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _random_aware_between_dates(d0: date, d1: date) -> datetime:
    """Random moment on a random calendar day in [d0, d1] inclusive."""
    d = _aware_date_range(d0, d1)
    return _aware_random_on_date(d)


def _random_aware_between(dt_start: datetime, dt_end: datetime) -> datetime:
    """Random aware datetime in [dt_start, dt_end] inclusive (by second)."""
    if dt_start >= dt_end:
        return dt_start + timedelta(seconds=random.randint(0, 300))
    span = int((dt_end - dt_start).total_seconds())
    return dt_start + timedelta(seconds=random.randint(0, max(span, 1)))


def _five_unique_dates_mar22_apr8_2026() -> list[date]:
    """Five distinct calendar days between 2026-03-22 and 2026-04-08 inclusive."""
    pool: list[date] = []
    d = date(2026, 3, 22)
    end = date(2026, 4, 8)
    while d <= end:
        pool.append(d)
        d += timedelta(days=1)
    return random.sample(pool, 5)


def _stamp_job_timestamps(job: Job, employer_joined: datetime) -> None:
    """Job posted after employer exists; created_at/updated_at strictly before Apr 10, 2026."""
    ceiling = _aware_dt(date(2026, 4, 9), 23, 59, random.randint(0, 59))
    lo = employer_joined + timedelta(minutes=random.randint(30, 72 * 60))
    if lo > ceiling:
        lo = max(
            employer_joined + timedelta(minutes=30),
            ceiling - timedelta(days=random.randint(3, 10)),
        )
    hi = min(lo + timedelta(days=random.randint(1, 18)), ceiling)
    if lo >= hi:
        hi = min(lo + timedelta(hours=random.randint(2, 36)), ceiling)
    if lo >= hi:
        lo = max(employer_joined + timedelta(minutes=45), ceiling - timedelta(days=1))
    jc = _random_aware_between(lo, min(hi, ceiling))
    ju = jc + timedelta(seconds=random.randint(120, 72 * 3600))
    if ju > ceiling:
        ju = min(ceiling, jc + timedelta(minutes=random.randint(20, 90)))
    if ju <= jc:
        ju = min(ceiling, jc + timedelta(minutes=random.randint(15, 120)))
    Job.objects.filter(pk=job.pk).update(created_at=jc, updated_at=ju)
    job.refresh_from_db()


def _stamp_application_times(
    app: Application,
    w_user: User,
    job: Job,
    app_window_end: datetime,
    *,
    mark_hired: bool = False,
) -> None:
    """Backfill application created_at/updated_at; sets hired_at when mark_hired."""
    job.refresh_from_db()
    lo = max(w_user.date_joined, job.created_at) + timedelta(minutes=random.randint(20, 360))
    hi = app_window_end
    if lo >= hi:
        lo = hi - timedelta(hours=random.randint(2, 12))
    if lo >= hi:
        lo = hi - timedelta(minutes=30)

    if mark_hired:
        # At least a few days between application sent and hire; hire_at stays within app_window_end.
        min_days = random.randint(3, 8)
        min_gap = timedelta(days=min_days) + timedelta(hours=random.randint(1, 12))
        latest_apply = app_window_end - min_gap
        if latest_apply < lo:
            min_gap = timedelta(days=3) + timedelta(hours=random.randint(1, 12))
            latest_apply = app_window_end - min_gap
        apply_hi = min(hi, latest_apply)
        if apply_hi < lo:
            app_created = lo
            hired_at = min(
                app_created + timedelta(days=3) + timedelta(hours=random.randint(2, 18)),
                app_window_end,
            )
        else:
            app_created = _random_aware_between(lo, apply_hi)
            earliest_hire = app_created + min_gap
            if earliest_hire < app_created + timedelta(days=3):
                earliest_hire = app_created + timedelta(days=3) + timedelta(hours=random.randint(0, 8))
            hired_at = _random_aware_between(earliest_hire, app_window_end)
        app_updated = _random_aware_between(
            app_created + timedelta(minutes=30),
            min(app_created + timedelta(days=2), hired_at - timedelta(hours=2)),
        )
        if app_updated <= app_created:
            app_updated = app_created + timedelta(hours=random.randint(2, 36))
        if app_updated >= hired_at:
            app_updated = app_created + timedelta(hours=random.randint(4, 48))
        Application.objects.filter(pk=app.pk).update(
            created_at=app_created,
            updated_at=app_updated,
            hired_at=hired_at,
        )
        return

    app_created = _random_aware_between(lo, hi)
    app_updated = _random_aware_between(
        app_created + timedelta(minutes=5),
        min(app_created + timedelta(days=5), app_window_end),
    )
    if app_updated <= app_created:
        app_updated = app_created + timedelta(seconds=random.randint(400, 86400))
    Application.objects.filter(pk=app.pk).update(created_at=app_created, updated_at=app_updated)


# Short Taglish threads for sample chats (less formal tone).
CONVO_SCRIPTS: dict[str, list[tuple[str, str]]] = {
    'np_elec': [
        (
            'worker',
            'sir nag apply ako sa electrician post nyo. nc2 ako tapos may experience sa planta',
        ),
        (
            'employer',
            'hi janine ok noted. san ka banda nagwork before',
        ),
        (
            'worker',
            'calamba area dati. motors panels minsan nag rerewiring kami pag may sira',
        ),
        (
            'employer',
            'sige pag usapan natin safety bukas pag free ka saglit call lang',
        ),
        (
            'worker',
            'sige po after 5 ok sakin',
        ),
    ],
    'jolly_janitor': [
        (
            'worker',
            'maam hello nag apply ako sa janitor. 5 years na ako sa cleaning sa warehouse',
        ),
        (
            'employer',
            'hi charmaine thanks sa message. night shift ba ok sayo or day shift lang',
        ),
        (
            'worker',
            'pwede po pareho basta may day off. sanay ako sa mopping tsaka waste segregation',
        ),
        (
            'employer',
            'copy. send mo lang id pic dito sa chat pag may time',
        ),
        (
            'worker',
            'sige maam send ko mamaya pag uwi',
        ),
    ],
    'ho_fasm': [
        (
            'worker',
            'hi po apply ako sa furniture assembler. nag assemble ako ng office tables dati',
        ),
        (
            'employer',
            'hi irish ok. marunong ka magbasa ng simple drawing',
        ),
        (
            'worker',
            'oo naman po may label naman usually tapos may allen wrench ako sarili',
        ),
        (
            'employer',
            'sige punta ka site interview next week text kita day',
        ),
        (
            'worker',
            'sige po salamat',
        ),
    ],
}


def _seed_conversation_for_application(
    app: Application,
    script_key: str,
) -> None:
    """Create one conversation with staggered Taglish messages after an application exists."""
    script = CONVO_SCRIPTS.get(script_key)
    if not script:
        return
    job = app.job
    worker = app.worker
    employer = job.employer
    conv = Conversation.objects.create(job=job, worker=worker, employer=employer)
    t0 = app.created_at + timedelta(minutes=random.randint(45, 180))
    Conversation.objects.filter(pk=conv.pk).update(created_at=t0)
    for i, (role, content) in enumerate(script):
        sender = worker if role == 'worker' else employer
        msg = Message.objects.create(conversation=conv, sender=sender, content=content)
        msg_t = t0 + timedelta(minutes=5 + i * random.randint(8, 35))
        Message.objects.filter(pk=msg.pk).update(created_at=msg_t)


class Command(BaseCommand):
    help = (
        'DANGEROUS: Delete all users except protected phone numbers and superusers, '
        'then create 5 employers (incl. Jolly/FourAces + 3 new companies), their jobs '
        '(created before Apr 10, 2026), 10 workers, 3 hired + mixed applications, sample chats. '
        'Workers unverified. Requires --force.'
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

        # Atomic: avoid partial state on Postgres if any insert fails (e.g. field length).
        with transaction.atomic():
            self._seed_all()

        self.stdout.write(self.style.SUCCESS('Professor demo seed complete.'))
        worker_phones = ', '.join(row[0] for row in WORKER_SEEDS)
        self.stdout.write(
            f'Demo login password for all new accounts: {DEMO_PASSWORD}\n'
            f'  Employers: {JOLLY_PHONE} (Jolly), {FOURACES_PHONE} (FourAces), '
            f'{EGLOBAL_PHONE} (eGlobal), {NEWPRO_PHONE} (Newpro), {HANDO_PHONE} (HandO)\n'
            f'  Workers: {worker_phones}\n'
            f'Protected phones (unchanged): {", ".join(sorted(PROTECTED_PHONES))}'
        )

    def _seed_all(self) -> None:
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

        # --- Employers: five unique calendar join dates (Mar 22–Apr 8, 2026), random times ---
        d_jolly, d_fouraces, d_eglobal, d_newpro, d_hando = _five_unique_dates_mar22_apr8_2026()
        j_join = _aware_random_on_date(d_jolly)
        f_join = _aware_random_on_date(d_fouraces)
        eg_join = _aware_random_on_date(d_eglobal)
        np_join = _aware_random_on_date(d_newpro)
        ho_join = _aware_random_on_date(d_hando)

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

        eg_user = User.objects.create_user(
            username=EGLOBAL_PHONE,
            email='',
            password=DEMO_PASSWORD,
            phone_number=EGLOBAL_PHONE,
            first_name='Clement',
            last_name='del Rosario',
            role='employer',
        )
        User.objects.filter(pk=eg_user.pk).update(date_joined=eg_join)
        EmployerProfile.objects.create(
            user=eg_user,
            company_name='eGlobal Outsourcing Management Services',
            city='Manila',
            contact_person='Clement del Rosario',
            contact_number='0917 309 0545',
            verification_status='verified',
        )

        np_user = User.objects.create_user(
            username=NEWPRO_PHONE,
            email='',
            password=DEMO_PASSWORD,
            phone_number=NEWPRO_PHONE,
            first_name='Philip',
            last_name='Dee',
            role='employer',
        )
        User.objects.filter(pk=np_user.pk).update(date_joined=np_join)
        EmployerProfile.objects.create(
            user=np_user,
            company_name='Newpro Industrial Manufacturing Corporation',
            city='Calamba, Laguna',
            contact_person='Philip Dee',
            contact_number=NEWPRO_PHONE,
            verification_status='verified',
        )

        ho_user = User.objects.create_user(
            username=HANDO_PHONE,
            email='',
            password=DEMO_PASSWORD,
            phone_number=HANDO_PHONE,
            first_name='Kitchie',
            last_name='-',
            role='employer',
        )
        User.objects.filter(pk=ho_user.pk).update(date_joined=ho_join)
        EmployerProfile.objects.create(
            user=ho_user,
            company_name='HandO Home and Office Furniture',
            city='Muntinlupa City, Metro Manila',
            contact_person='Kitchie',
            contact_number=HANDO_PHONE,
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

        eg_carp = Job.objects.create(
            employer=eg_user,
            title='Carpenter (formworks, ceiling, finishing)',
            city='Manila',
            daily_rate=Decimal('800.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=(
                'Specializing in formworks, ceiling, and finishing. '
                'Rates and terms per company policy.'
            ),
            required_skills=[{'skill': 'Carpentry', 'years_experience': None}],
            start_date=date(2026, 4, 10),
            positions_needed=2,
            status='open',
        )
        eg_elec = Job.objects.create(
            employer=eg_user,
            title='Electrician (NC II/III certification required)',
            city='Manila',
            daily_rate=Decimal('950.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description='NC II or NC III certification required.',
            required_skills=[{'skill': 'Electrician', 'years_experience': None}],
            start_date=date(2026, 4, 12),
            positions_needed=1,
            status='open',
        )
        eg_plumb = Job.objects.create(
            employer=eg_user,
            title='Plumber',
            city='Manila',
            daily_rate=Decimal('695.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description='Plumbing installation and repair.',
            required_skills=[{'skill': 'Plumber', 'years_experience': None}],
            start_date=date(2026, 4, 8),
            positions_needed=3,
            status='open',
        )

        np_elec = Job.objects.create(
            employer=np_user,
            title='Electrician (NC II/III certification required)',
            city='Calamba, Laguna',
            daily_rate=Decimal('700.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description='NC II or NC III certification required.',
            required_skills=[{'skill': 'Electrician', 'years_experience': None}],
            start_date=date(2026, 4, 5),
            positions_needed=1,
            status='open',
        )
        np_mach = Job.objects.create(
            employer=np_user,
            title='Machine Operator',
            city='Calamba, Laguna',
            daily_rate=Decimal('600.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description='Industrial manufacturing; machine operation and line support.',
            required_skills=[{'skill': 'Machine Operator', 'years_experience': None}],
            start_date=date(2026, 4, 7),
            positions_needed=2,
            status='open',
        )

        ho_drv = Job.objects.create(
            employer=ho_user,
            title='Driver (Professional License)',
            city='Muntinlupa',
            daily_rate=Decimal('800.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=(
                'Professional driver license required. Must know how to drive '
                'automatic and manual transmission.'
            ),
            required_skills=[{'skill': 'Driver', 'years_experience': None}],
            start_date=date(2026, 4, 15),
            positions_needed=1,
            status='open',
        )
        ho_fasm = Job.objects.create(
            employer=ho_user,
            title='Furniture Assembler',
            city='Muntinlupa',
            daily_rate=Decimal('695.00'),
            rate_type=Job.RATE_TYPE_DAILY,
            working_hours='8am–5pm',
            short_description=(
                'Male, 18–40 years old, willing to learn, can read drawings and instructions.'
            ),
            required_skills=[{'skill': 'Furniture Assembler', 'years_experience': None}],
            start_date=date(2026, 4, 12),
            positions_needed=1,
            status='open',
        )

        jobs_map['eg_carp'] = eg_carp
        jobs_map['eg_elec'] = eg_elec
        jobs_map['eg_plumb'] = eg_plumb
        jobs_map['np_elec'] = np_elec
        jobs_map['np_mach'] = np_mach
        jobs_map['ho_drv'] = ho_drv
        jobs_map['ho_fasm'] = ho_fasm

        all_jobs = [
            td_j,
            jan_j,
            sew_j,
            td_f,
            eg_carp,
            eg_elec,
            eg_plumb,
            np_elec,
            np_mach,
            ho_drv,
            ho_fasm,
        ]
        employer_joins = {
            jolly_user.pk: j_join,
            four_user.pk: f_join,
            eg_user.pk: eg_join,
            np_user.pk: np_join,
            ho_user.pk: ho_join,
        }
        for job in all_jobs:
            _stamp_job_timestamps(job, employer_joins[job.employer_id])

        app_window_end = _aware_dt(date(2026, 4, 10), 23, 59, random.randint(10, 55))

        _female_first = {'Charmaine', 'Janine', 'Sophia', 'Irish'}
        worker_by_phone: dict[str, User] = {}

        for phone, full_name, city, skills, signup_day in WORKER_SEEDS:
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
            w_join = _aware_random_on_date(signup_day)
            User.objects.filter(pk=w_user.pk).update(date_joined=w_join)
            w_user.refresh_from_db()
            worker_by_phone[phone] = w_user

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
                gender='female' if first in _female_first else 'male',
                marital_status='single',
                nationality='Filipino',
                religion='',
                languages_known='Filipino, English',
                national_id_status='not_verified',
                verification_status='not_submitted',
            )

        for phone, job_key in HIRED_PLACEMENTS:
            u = worker_by_phone[phone]
            job = jobs_map[job_key]
            job.refresh_from_db()
            app = Application.objects.create(job=job, worker=u, status='hired')
            _stamp_application_times(app, u, job, app_window_end, mark_hired=True)
            app.refresh_from_db()
            ht = app.hired_at
            ApplicationContract.objects.create(
                application=app,
                contract_status=ApplicationContract.STATUS_COMPLETE,
                worker_accepted_at=ht,
                employer_confirmed_at=ht,
            )
            maybe_autoclose_job_when_filled(job)

        for phone, job_key, app_status in EXTRA_APPLICATIONS:
            u = worker_by_phone[phone]
            job = jobs_map[job_key]
            job.refresh_from_db()
            app = Application.objects.create(job=job, worker=u, status=app_status)
            _stamp_application_times(app, u, job, app_window_end)

        for phone, job_key, script_key in CONVO_FOR_APPLICATIONS:
            u = worker_by_phone[phone]
            job = jobs_map[job_key]
            app = Application.objects.get(job=job, worker=u)
            _seed_conversation_for_application(app, script_key)

        # Ensure all five demo employers exist (full profile rows).
        demo_employer_phones = (
            JOLLY_PHONE,
            FOURACES_PHONE,
            EGLOBAL_PHONE,
            NEWPRO_PHONE,
            HANDO_PHONE,
        )
        for phone in demo_employer_phones:
            u = User.objects.filter(phone_number=phone, role='employer').first()
            if not u:
                raise CommandError(f'Seed incomplete: missing employer user {phone}')
            if not EmployerProfile.objects.filter(user=u).exists():
                raise CommandError(f'Seed incomplete: missing employer profile for {phone}')

        # All employer profiles verified (including any pre-existing rows kept with protected users).
        EmployerProfile.objects.all().update(
            verification_status='verified',
            rejection_reason='',
        )
