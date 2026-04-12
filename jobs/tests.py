from datetime import date

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmployerProfile, User, WorkerProfile
from jobs.employer_job_utils import hired_count_for_job, show_vacancy_reopen_banner
from jobs.models import Application, ApplicationContract, Job
from jobs.skill_utils import normalize_skill_entries, required_skill_names


class ApplicationHiredAtTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username='09991234501',
            email='e@test.com',
            password='pass',
            role='employer',
            phone_number='09991234501',
        )
        self.worker = User.objects.create_user(
            username='09991234502',
            email='w@test.com',
            password='pass',
            role='worker',
            phone_number='09991234502',
        )
        EmployerProfile.objects.create(
            user=self.employer,
            company_name='Test Co',
            city='Manila',
            contact_person='A',
            contact_number='09991234501',
        )
        WorkerProfile.objects.create(
            user=self.worker,
            full_name='Worker One',
            city='Manila',
            contact_number='09991234502',
            years_experience=0,
            skills=[],
        )
        self.job = Job.objects.create(
            employer=self.employer,
            title='Laborer',
            city='Manila',
            daily_rate=500,
            working_hours='7am–4pm',
            required_skills=[{'skill': 'Helper', 'years_experience': None}],
            start_date=date.today(),
            status='open',
            positions_needed=1,
        )
        self.application = Application.objects.create(job=self.job, worker=self.worker)
        self.client = Client()

    def test_hired_sets_hired_at_once(self):
        self.client.force_login(self.employer)
        ApplicationContract.objects.create(
            application=self.application,
            contract_status=ApplicationContract.STATUS_COMPLETE,
            worker_accepted_terms=True,
            worker_accepted_at=timezone.now(),
            employer_confirmed_at=timezone.now(),
        )
        self.client.get(
            reverse('update_application_status', args=[self.application.pk, 'hired'])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'hired')
        self.assertIsNotNone(self.application.hired_at)
        first = self.application.hired_at
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'closed')
        self.assertTrue(self.job.auto_closed_when_filled)

        self.client.get(
            reverse('update_application_status', args=[self.application.pk, 'completed'])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'completed')
        self.assertEqual(self.application.hired_at, first)


class StaffExportHiresTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='09990000001',
            email='admin@test.com',
            password='pass',
            role='admin',
            phone_number='09990000001',
        )
        self.worker = User.objects.create_user(
            username='09991234503',
            email='w2@test.com',
            password='pass',
            role='worker',
            phone_number='09991234503',
        )
        EmployerProfile.objects.create(
            user=self.staff,
            company_name='Staff Co',
            city='QC',
            contact_person='S',
            contact_number='09990000001',
        )
        WorkerProfile.objects.create(
            user=self.worker,
            full_name='W2',
            city='QC',
            contact_number='09991234503',
            years_experience=0,
            skills=[],
        )
        self.job = Job.objects.create(
            employer=self.staff,
            title='Site work',
            city='QC',
            daily_rate=600,
            working_hours='8 oras',
            required_skills=[{'skill': 'Helper', 'years_experience': 1}],
            start_date=date.today(),
            status='open',
            positions_needed=1,
        )
        self.application = Application.objects.create(
            job=self.job,
            worker=self.worker,
            status='hired',
            hired_at=timezone.now(),
        )
        self.client = Client()

    def test_staff_gets_csv(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('staff_export_hires'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn(b'application_id', response.content)
        self.assertIn(str(self.application.pk).encode(), response.content)

    def test_worker_redirected(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse('staff_export_hires'))
        self.assertEqual(response.status_code, 302)

class ContractHireGateTests(TestCase):
    """Hire requires completed contract workflow."""

    def setUp(self):
        self.employer = User.objects.create_user(
            username='09991234510',
            email='e10@test.com',
            password='pass',
            role='employer',
            phone_number='09991234510',
        )
        self.worker = User.objects.create_user(
            username='09991234511',
            email='w11@test.com',
            password='pass',
            role='worker',
            phone_number='09991234511',
        )
        EmployerProfile.objects.create(
            user=self.employer,
            company_name='Gate Co',
            city='Manila',
            contact_person='G',
            contact_number='09991234510',
        )
        WorkerProfile.objects.create(
            user=self.worker,
            full_name='Gate Worker',
            city='Manila',
            contact_number='09991234511',
            years_experience=0,
            skills=[],
        )
        self.job = Job.objects.create(
            employer=self.employer,
            title='Gate Job',
            city='Manila',
            daily_rate=400,
            working_hours='7am–3pm',
            required_skills=[{'skill': 'Helper', 'years_experience': None}],
            start_date=date.today(),
            status='open',
            positions_needed=1,
        )
        self.application = Application.objects.create(job=self.job, worker=self.worker)
        self.client = Client()

    def test_hire_blocked_without_complete_contract(self):
        self.client.force_login(self.employer)
        response = self.client.get(
            reverse('update_application_status', args=[self.application.pk, 'hired']),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertNotEqual(self.application.status, 'hired')


class SkillUtilsTests(TestCase):
    def test_required_skill_names_legacy_and_new(self):
        names = required_skill_names(['Masonry', {'skill': 'Driver'}])
        self.assertEqual(names, {'Masonry', 'Driver'})

    def test_normalize_skill_entries(self):
        out = normalize_skill_entries(['A', {'skill': 'B', 'years_experience': 3}])
        self.assertEqual(
            out,
            [
                {'skill': 'A', 'years_experience': None},
                {'skill': 'B', 'years_experience': 3},
            ],
        )

    def test_normalize_skill_entries_self_rating(self):
        out = normalize_skill_entries([
            {'skill': 'Helper', 'years_experience': 2, 'self_rating': 4},
        ])
        self.assertEqual(
            out,
            [{'skill': 'Helper', 'years_experience': 2, 'self_rating': 4}],
        )

    def test_overlap_with_dict_shaped_worker_skills_matches_legacy_strings(self):
        job_skills = required_skill_names(
            [{'skill': 'Helper', 'years_experience': None}]
        )
        worker_dicts = [
            {'skill': 'Helper', 'years_experience': 5},
            {'skill': 'Masonry', 'years_experience': 1},
        ]
        self.assertEqual(
            len(job_skills & required_skill_names(worker_dicts)),
            len(job_skills & required_skill_names(['Helper', 'Masonry'])),
        )


class JobAutoCloseVacancyTests(TestCase):
    """Auto-close when hired >= positions_needed; vacancy banner after completion."""

    def setUp(self):
        self.employer = User.objects.create_user(
            username='09992222001',
            email='e22@test.com',
            password='pass',
            role='employer',
            phone_number='09992222001',
        )
        self.worker = User.objects.create_user(
            username='09992222002',
            email='w22@test.com',
            password='pass',
            role='worker',
            phone_number='09992222002',
        )
        EmployerProfile.objects.create(
            user=self.employer,
            company_name='AC Co',
            city='Manila',
            contact_person='A',
            contact_number='09992222001',
        )
        WorkerProfile.objects.create(
            user=self.worker,
            full_name='AC Worker',
            city='Manila',
            contact_number='09992222002',
            years_experience=0,
            skills=[],
        )
        self.job = Job.objects.create(
            employer=self.employer,
            title='AutoClose Job',
            city='Manila',
            daily_rate=700,
            working_hours='8 oras',
            required_skills=[{'skill': 'Helper', 'years_experience': None}],
            start_date=date.today(),
            status='open',
            positions_needed=2,
        )
        self.w2 = User.objects.create_user(
            username='09992222003',
            email='w23@test.com',
            password='pass',
            role='worker',
            phone_number='09992222003',
        )
        WorkerProfile.objects.create(
            user=self.w2,
            full_name='AC Worker Two',
            city='Manila',
            contact_number='09992222003',
            years_experience=1,
            skills=[],
        )
        self.app1 = Application.objects.create(job=self.job, worker=self.worker)
        self.app2 = Application.objects.create(job=self.job, worker=self.w2)
        self.client = Client()

    def _complete_contract(self, application):
        ApplicationContract.objects.create(
            application=application,
            contract_status=ApplicationContract.STATUS_COMPLETE,
            worker_accepted_terms=True,
            worker_accepted_at=timezone.now(),
            employer_confirmed_at=timezone.now(),
        )

    def test_first_hire_does_not_close_when_two_needed(self):
        self.client.force_login(self.employer)
        self._complete_contract(self.app1)
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'hired']),
        )
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'open')
        self.assertFalse(self.job.auto_closed_when_filled)
        self.assertEqual(hired_count_for_job(self.job), 1)

    def test_second_hire_closes_job(self):
        self.client.force_login(self.employer)
        self._complete_contract(self.app1)
        self._complete_contract(self.app2)
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'hired']),
        )
        self.client.get(
            reverse('update_application_status', args=[self.app2.pk, 'hired']),
        )
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'closed')
        self.assertTrue(self.job.auto_closed_when_filled)
        self.assertEqual(hired_count_for_job(self.job), 2)

    def test_vacancy_prompt_after_completion(self):
        self.client.force_login(self.employer)
        self._complete_contract(self.app1)
        self._complete_contract(self.app2)
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'hired']),
        )
        self.client.get(
            reverse('update_application_status', args=[self.app2.pk, 'hired']),
        )
        self.job.refresh_from_db()
        self.assertFalse(show_vacancy_reopen_banner(self.job))
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'completed']),
        )
        self.job.refresh_from_db()
        self.assertTrue(show_vacancy_reopen_banner(self.job))

    def test_reopen_after_vacancy(self):
        self.client.force_login(self.employer)
        self._complete_contract(self.app1)
        self._complete_contract(self.app2)
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'hired']),
        )
        self.client.get(
            reverse('update_application_status', args=[self.app2.pk, 'hired']),
        )
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'completed']),
        )
        self.job.refresh_from_db()
        res = self.client.post(reverse('reopen_job_after_vacancy', args=[self.job.pk]))
        self.assertEqual(res.status_code, 302)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'open')
        self.assertFalse(self.job.auto_closed_when_filled)

    def test_worker_cannot_apply_when_listing_closed(self):
        self.client.force_login(self.employer)
        self._complete_contract(self.app1)
        self._complete_contract(self.app2)
        self.client.get(
            reverse('update_application_status', args=[self.app1.pk, 'hired']),
        )
        self.client.get(
            reverse('update_application_status', args=[self.app2.pk, 'hired']),
        )
        w3 = User.objects.create_user(
            username='09992222004',
            email='w24@test.com',
            password='pass',
            role='worker',
            phone_number='09992222004',
        )
        WorkerProfile.objects.create(
            user=w3,
            full_name='Third',
            city='Manila',
            contact_number='09992222004',
            years_experience=0,
            skills=[],
        )
        before = Application.objects.filter(job=self.job).count()
        self.client.force_login(w3)
        self.client.get(reverse('apply_job', args=[self.job.pk]))
        self.assertEqual(Application.objects.filter(job=self.job).count(), before)

    def test_job_detail_hides_headcount_from_worker(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'employer lang')
