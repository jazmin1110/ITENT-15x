import random
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from accounts.models import User, WorkerProfile, EmployerProfile
from jobs.models import Job, Application, Rating
from chat.models import Conversation, Message

fake = Faker('en_PH')

SKILLS = ['Masonry', 'Carpentry', 'Helper', 'Painting', 'Driver']
CITIES = [
    'Manila', 'Quezon City', 'Cebu City', 'Davao City',
    'Bacolod', 'Makati', 'Taguig', 'Pasig',
]

JOB_TITLES = [
    'Mason needed for residential project',
    'Carpenter for office renovation',
    'Helper for warehouse operations',
    'Painter for commercial building',
    'Driver for delivery service',
    'Mason for road construction',
    'Carpenter for furniture workshop',
    'Helper for construction site',
    'Painter for house repainting',
    'Driver for logistics company',
    'Mason for building foundation',
    'Carpenter for roofing project',
    'General helper for moving company',
    'Painter for interior design project',
    'Driver for corporate transport',
    'Mason for concrete works',
    'Carpenter for kitchen installation',
    'Helper for event setup',
    'Painter for school renovation',
    'Driver for cargo transport',
]

WORKER_REVIEWS = [
    'Very hardworking and reliable.',
    'Great skills, finished ahead of schedule.',
    'Good worker, would hire again.',
    'Punctual and professional.',
    'Did a decent job overall.',
    'Excellent craftsmanship.',
    'Needs improvement on time management.',
    'Very skilled and easy to work with.',
    'Completed the work as expected.',
    'Outstanding performance, highly recommended.',
]

EMPLOYER_REVIEWS = [
    'Fair employer, paid on time.',
    'Good working conditions on site.',
    'Professional and organized.',
    'Clear instructions, easy to work with.',
    'Respectful and fair treatment.',
    'Paid promptly after completion.',
    'Provided all necessary materials.',
    'Great employer, would work for again.',
    'Reasonable expectations and good communication.',
    'Safe work environment.',
]

CHAT_MESSAGES_WORKER = [
    'Hi po, interested ako sa job posting niyo.',
    'Good day! Available po ako for this job.',
    'Kailan po ang start date?',
    'May experience po ako sa ganitong trabaho.',
    'Pwede po ba mag-inquire about the daily rate?',
    'Ready po ako mag-start anytime.',
    'Thank you po sa opportunity.',
    'I can bring my own tools po.',
    'Ilang araw po ang project?',
    'Saan po exactly ang location ng site?',
]

CHAT_MESSAGES_EMPLOYER = [
    'Hello! Thank you for your interest.',
    'Can you start next week?',
    'Do you have experience with this type of work?',
    'The job site is accessible by jeepney.',
    'We provide lunch and safety gear.',
    'Please bring your NBI clearance on the first day.',
    'The project will last about 2 weeks.',
    'We pay every Saturday.',
    'Welcome aboard! See you on Monday.',
    'Let me know if you have any questions.',
]

PH_COMPANY_SUFFIXES = [
    'Construction Corp.', 'Builders Inc.', 'Development Corp.',
    'Engineering Services', 'Contractors Co.', 'Properties Inc.',
    'Trading Corp.', 'General Services', 'Infrastructure Inc.',
    'Enterprises',
]

TEST_PREFIX = 'test_'
TEST_PASSWORD = 'TestPass123!'


def weighted_choice(choices_weights):
    """Pick from a list of (value, weight) tuples."""
    values, weights = zip(*choices_weights)
    return random.choices(values, weights=weights, k=1)[0]


class Command(BaseCommand):
    help = 'Populate database with realistic test data for workers, employers, jobs, applications, ratings, and chats.'

    def add_arguments(self, parser):
        parser.add_argument('--workers', type=int, default=20, help='Number of test workers (default: 20)')
        parser.add_argument('--employers', type=int, default=8, help='Number of test employers (default: 8)')
        parser.add_argument('--jobs', type=int, default=25, help='Number of test jobs (default: 25)')
        parser.add_argument('--flush', action='store_true', help='Delete all test data then repopulate')
        parser.add_argument('--clear', action='store_true', help='Delete all test data only (no repopulate)')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_test_data()
            return

        if options['flush']:
            self._clear_test_data()

        existing = User.objects.filter(phone_number__startswith=TEST_PREFIX).count()
        if existing and not options['flush']:
            self.stdout.write(self.style.WARNING(
                f'Found {existing} existing test users. Use --flush to delete and recreate, or --clear to just delete.'
            ))
            return

        num_workers = options['workers']
        num_employers = options['employers']
        num_jobs = options['jobs']

        workers = self._create_workers(num_workers)
        employers = self._create_employers(num_employers)
        jobs = self._create_jobs(employers, num_jobs)
        applications = self._create_applications(workers, jobs)
        self._create_ratings(applications)
        self._create_conversations_and_messages(applications)

        self.stdout.write(self.style.SUCCESS('\nTest data populated successfully!'))
        self._print_summary()

    def _clear_test_data(self):
        test_users = User.objects.filter(phone_number__startswith=TEST_PREFIX)
        count = test_users.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No test data found to delete.'))
            return

        deleted = test_users.delete()
        # deleted is a tuple: (total_deleted, {model_label: count, ...})
        self.stdout.write(self.style.SUCCESS(f'\nDeleted {deleted[0]} records total:'))
        for model_label, num in sorted(deleted[1].items()):
            if num > 0:
                self.stdout.write(f'  {model_label}: {num}')
        self.stdout.write(self.style.SUCCESS('All test data cleared.'))

    def _create_workers(self, count):
        self.stdout.write(f'Creating {count} workers...')
        workers = []
        verified_statuses = (
            [('verified', 'verified')] * 6
            + [('pending', 'pending')] * 2
            + [('not_submitted', 'not_verified')] * 2
        )

        for i in range(1, count + 1):
            phone = f'{TEST_PREFIX}09{170000000 + i}'
            first = fake.first_name()
            last = fake.last_name()
            user = User.objects.create_user(
                username=phone,
                email=f'test_worker_{i:02d}@test.com',
                password=TEST_PASSWORD,
                first_name=first,
                last_name=last,
                role='worker',
                phone_number=phone,
            )
            v_status, nid_status = random.choice(verified_statuses)
            nid_number = f'{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}'

            WorkerProfile.objects.create(
                user=user,
                full_name=f'{first} {last}',
                city=random.choice(CITIES),
                contact_number=user.phone_number,
                years_experience=random.randint(0, 15),
                skills=random.sample(SKILLS, k=random.randint(1, 3)),
                national_id_number=nid_number,
                national_id_status=nid_status,
                verification_status=v_status,
            )
            workers.append(user)

        self.stdout.write(self.style.SUCCESS(f'  Created {count} workers with profiles.'))
        return workers

    def _create_employers(self, count):
        self.stdout.write(f'Creating {count} employers...')
        employers = []
        verified_statuses = (
            ['verified'] * 6
            + ['pending'] * 2
            + ['not_submitted'] * 2
        )

        ph_surnames = [
            'Santos', 'Reyes', 'Cruz', 'Garcia', 'Del Rosario',
            'Mendoza', 'Rivera', 'Tan', 'Lim', 'Gonzales',
            'Torres', 'Ramos', 'Aquino', 'Villanueva', 'Dizon',
        ]

        for i in range(1, count + 1):
            phone = f'{TEST_PREFIX}09{180000000 + i}'
            first = fake.first_name()
            last = fake.last_name()
            user = User.objects.create_user(
                username=phone,
                email=f'test_employer_{i:02d}@test.com',
                password=TEST_PASSWORD,
                first_name=first,
                last_name=last,
                role='employer',
                phone_number=phone,
            )
            surname = random.choice(ph_surnames)
            suffix = random.choice(PH_COMPANY_SUFFIXES)
            v_status = random.choice(verified_statuses)

            EmployerProfile.objects.create(
                user=user,
                company_name=f'{surname} {suffix}',
                city=random.choice(CITIES),
                contact_person=f'{first} {last}',
                contact_number=user.phone_number,
                verification_status=v_status,
            )
            employers.append(user)

        self.stdout.write(self.style.SUCCESS(f'  Created {count} employers with profiles.'))
        return employers

    def _create_jobs(self, employers, count):
        self.stdout.write(f'Creating {count} jobs...')
        verified_employers = [
            e for e in employers
            if e.employer_profile.verification_status == 'verified'
        ]
        if not verified_employers:
            verified_employers = employers

        jobs = []
        now = timezone.now().date()
        for i in range(count):
            employer = random.choice(verified_employers)
            title = random.choice(JOB_TITLES)
            picked = random.sample(SKILLS, k=random.randint(1, 3))
            required_skills = [
                {
                    'skill': s,
                    'years_experience': random.choice([None, random.randint(0, 10)]),
                }
                for s in picked
            ]
            job = Job.objects.create(
                employer=employer,
                title=title,
                city=random.choice(CITIES),
                daily_rate=Decimal(random.randrange(500, 1550, 50)),
                working_hours=random.choice(['7am–4pm', '8 oras', '6am–2pm']),
                short_description='' if random.random() < 0.5 else f'Test work: {title}.',
                required_skills=required_skills,
                positions_needed=random.randint(1, 3),
                start_date=now + timedelta(days=random.randint(1, 30)),
                status='open' if random.random() < 0.8 else 'closed',
            )
            jobs.append(job)

        self.stdout.write(self.style.SUCCESS(f'  Created {count} jobs.'))
        return jobs

    def _create_applications(self, workers, jobs):
        self.stdout.write('Creating applications...')
        verified_workers = [
            w for w in workers
            if w.worker_profile.verification_status == 'verified'
        ]
        if not verified_workers:
            verified_workers = workers

        status_weights = [
            ('sent', 20),
            ('viewed', 15),
            ('shortlisted', 15),
            ('hired', 30),
            ('completed', 20),
        ]

        applications = []
        seen = set()
        for worker in verified_workers:
            num_apps = random.randint(2, min(5, len(jobs)))
            chosen_jobs = random.sample(jobs, k=num_apps)
            for job in chosen_jobs:
                key = (worker.pk, job.pk)
                if key in seen:
                    continue
                seen.add(key)
                status = weighted_choice(status_weights)
                app = Application.objects.create(
                    job=job,
                    worker=worker,
                    status=status,
                )
                applications.append(app)

        self.stdout.write(self.style.SUCCESS(f'  Created {len(applications)} applications.'))
        return applications

    def _create_ratings(self, applications):
        self.stdout.write('Creating ratings...')
        completed = [a for a in applications if a.status == 'completed']
        count = 0

        for app in completed:
            employer = app.job.employer
            worker = app.worker

            Rating.objects.create(
                application=app,
                rater=employer,
                ratee=worker,
                score=weighted_choice([(3, 10), (4, 40), (5, 40), (2, 8), (1, 2)]),
                review=random.choice(WORKER_REVIEWS),
            )
            count += 1

            if random.random() < 0.7:
                Rating.objects.create(
                    application=app,
                    rater=worker,
                    ratee=employer,
                    score=weighted_choice([(3, 10), (4, 40), (5, 40), (2, 8), (1, 2)]),
                    review=random.choice(EMPLOYER_REVIEWS),
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {count} ratings.'))

    def _create_conversations_and_messages(self, applications):
        self.stdout.write('Creating conversations and messages...')
        eligible = [
            a for a in applications
            if a.status in ('shortlisted', 'hired', 'completed')
        ]

        conv_count = 0
        msg_count = 0
        seen = set()

        for app in eligible:
            key = (app.job.pk, app.worker.pk, app.job.employer.pk)
            if key in seen:
                continue
            seen.add(key)

            conv, created = Conversation.objects.get_or_create(
                job=app.job,
                worker=app.worker,
                employer=app.job.employer,
            )
            if not created:
                continue
            conv_count += 1

            num_messages = random.randint(2, 6)
            for j in range(num_messages):
                if j % 2 == 0:
                    sender = app.worker
                    content = random.choice(CHAT_MESSAGES_WORKER)
                else:
                    sender = app.job.employer
                    content = random.choice(CHAT_MESSAGES_EMPLOYER)
                Message.objects.create(
                    conversation=conv,
                    sender=sender,
                    content=content,
                )
                msg_count += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {conv_count} conversations with {msg_count} messages.'))

    def _print_summary(self):
        self.stdout.write('\n--- Summary ---')
        self.stdout.write(f'  Workers:       {User.objects.filter(phone_number__startswith=TEST_PREFIX, role="worker").count()}')
        self.stdout.write(f'  Employers:     {User.objects.filter(phone_number__startswith=TEST_PREFIX, role="employer").count()}')
        self.stdout.write(f'  Jobs:          {Job.objects.filter(employer__phone_number__startswith=TEST_PREFIX).count()}')
        self.stdout.write(f'  Applications:  {Application.objects.filter(worker__phone_number__startswith=TEST_PREFIX).count()}')
        self.stdout.write(f'  Ratings:       {Rating.objects.filter(rater__phone_number__startswith=TEST_PREFIX).count()}')
        self.stdout.write(f'  Conversations: {Conversation.objects.filter(worker__phone_number__startswith=TEST_PREFIX).count()}')
        self.stdout.write(f'  Messages:      {Message.objects.filter(sender__phone_number__startswith=TEST_PREFIX).count()}')
