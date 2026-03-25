from datetime import date

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmployerProfile, User, WorkerProfile
from jobs.models import Application, Job


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
            required_skills=[],
            start_date=date.today(),
            status='open',
        )
        self.application = Application.objects.create(job=self.job, worker=self.worker)
        self.client = Client()

    def test_hired_sets_hired_at_once(self):
        self.client.force_login(self.employer)
        self.client.get(
            reverse('update_application_status', args=[self.application.pk, 'hired'])
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'hired')
        self.assertIsNotNone(self.application.hired_at)
        first = self.application.hired_at

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
            required_skills=[],
            start_date=date.today(),
            status='open',
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
