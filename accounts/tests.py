import io

from django.contrib.auth import authenticate
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from PIL import Image
from django.urls import reverse

from accounts.forms import EmployerProfileForm
from accounts.models import User, EmployerProfile


class ProfileHeaderPhotoSectionTests(TestCase):
    """Profile photo upload lives in page header with anchor id=profile-photo."""

    def test_worker_profile_has_header_photo_section(self):
        user = User.objects.create_user(
            username='09170001001',
            email='',
            password='secret',
            phone_number='09170001001',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('worker_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="profile-photo"')
        self.assertContains(response, 'Baguhin ang larawan')

    def test_employer_profile_has_header_photo_section(self):
        user = User.objects.create_user(
            username='09170001002',
            email='',
            password='secret',
            phone_number='09170001002',
            role='employer',
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('employer_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="profile-photo"')
        self.assertContains(response, 'Baguhin ang larawan')


class DashboardRedirectTests(TestCase):
    def test_superuser_goes_to_staff_overview_even_if_role_worker(self):
        """createsuperuser defaults leave role=worker; admins should still land on staff home."""
        user = User.objects.create_user(
            username='09999999999',
            email='su@test.com',
            password='secret',
            phone_number='09999999999',
            role='worker',
            is_superuser=True,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dashboard'), follow=False)
        self.assertRedirects(
            response,
            reverse('staff_home'),
            fetch_redirect_response=False,
        )


class WorkerProfileTests(TestCase):
    def test_contact_prefilled_from_account_phone(self):
        user = User.objects.create_user(
            username='09171234567',
            email='w@test.com',
            password='secret',
            phone_number='09171234567',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('worker_profile'))
        self.assertContains(response, 'value="09171234567"')

    def test_post_save_shows_job_cta(self):
        user = User.objects.create_user(
            username='09179876543',
            email='w2@test.com',
            password='secret',
            phone_number='09179876543',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'Juan Worker',
                'city': 'Quezon City',
                'contact_number': '09179876543',
                'years_experience': 2,
                'skills': ['Helper'],
                'email': 'w2@test.com',
                'national_id_number': '',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tingnan ang mga trabaho')

    def test_email_saved_to_user(self):
        user = User.objects.create_user(
            username='09171111111',
            email='',
            password='secret',
            phone_number='09171111111',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'Worker Three',
                'city': 'Manila',
                'contact_number': '09171111111',
                'years_experience': 0,
                'skills': ['Driver'],
                'email': 'newmail@test.com',
                'national_id_number': '',
            },
        )
        user.refresh_from_db()
        self.assertEqual(user.email, 'newmail@test.com')

    def test_phone_change_updates_user_logs_out_and_allows_login_with_new_number(self):
        user = User.objects.create_user(
            username='09172000001',
            email='flow@test.com',
            password='secret',
            phone_number='09172000001',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'Flow Worker',
                'city': 'Cebu',
                'contact_number': '09172000002',
                'years_experience': 1,
                'skills': ['Helper'],
                'email': 'flow@test.com',
                'national_id_number': '',
            },
            follow=False,
        )
        self.assertRedirects(
            response,
            reverse('login'),
            fetch_redirect_response=False,
        )
        user.refresh_from_db()
        self.assertEqual(user.phone_number, '09172000002')
        self.assertEqual(user.username, '09172000002')
        self.assertIsNone(authenticate(username='09172000001', password='secret'))
        self.assertIsNotNone(authenticate(username='09172000002', password='secret'))

    def test_duplicate_contact_phone_rejected(self):
        User.objects.create_user(
            username='09173000001',
            email='',
            password='x',
            phone_number='09173000001',
            role='worker',
        )
        user_b = User.objects.create_user(
            username='09173000002',
            email='b@test.com',
            password='secret',
            phone_number='09173000002',
            role='worker',
        )
        client = Client()
        client.force_login(user_b)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'B Worker',
                'city': 'Davao',
                'contact_number': '09173000001',
                'years_experience': 0,
                'skills': ['Driver'],
                'email': 'b@test.com',
                'national_id_number': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ginagamit na ang phone number')
        user_b.refresh_from_db()
        self.assertEqual(user_b.phone_number, '09173000002')


class EmployerProfileTests(TestCase):
    def test_employer_form_includes_uploaded_avatar_in_cleaned_data(self):
        user = User.objects.create_user(
            username='09170000005',
            email='',
            password='secret',
            phone_number='09170000005',
            role='employer',
        )
        buf = io.BytesIO()
        Image.new('RGB', (10, 10), color=(0, 255, 0)).save(buf, format='PNG')
        buf.seek(0)
        avatar_file = SimpleUploadedFile('g.png', buf.read(), content_type='image/png')
        form = EmployerProfileForm(
            data={
                'company_name': 'Co',
                'city': 'X',
                'contact_person': 'Y',
                'contact_number': '021',
                'account_phone': '09170000005',
                'email': '',
            },
            files={'avatar': avatar_file},
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNotNone(form.cleaned_data.get('avatar'))

    def test_account_phone_shown_distinct_from_company_contact(self):
        user = User.objects.create_user(
            username='09170000002',
            email='emp@test.com',
            password='secret',
            phone_number='09170000002',
            role='employer',
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('employer_profile'))
        self.assertContains(response, '09170000002')
        self.assertContains(response, 'id_account_phone')
        # company contact field should not duplicate account phone as value="" empty first visit
        self.assertNotContains(response, 'id_contact_number" value="09170000002"')

    def test_post_save_shows_post_job_cta(self):
        user = User.objects.create_user(
            username='09170000003',
            email='e3@test.com',
            password='secret',
            phone_number='09170000003',
            role='employer',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('employer_profile'),
            data={
                'company_name': 'ACME Co',
                'city': 'Makati',
                'contact_person': 'Maria',
                'contact_number': '0288880000',
                'account_phone': '09170000003',
                'email': 'e3@test.com',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mag-post ng trabaho')

    def test_avatar_upload_updates_user(self):
        user = User.objects.create_user(
            username='09170000004',
            email='',
            password='secret',
            phone_number='09170000004',
            role='employer',
        )
        buf = io.BytesIO()
        Image.new('RGB', (32, 32), color=(255, 0, 0)).save(buf, format='PNG')
        buf.seek(0)
        avatar_file = SimpleUploadedFile('a.png', buf.read(), content_type='image/png')
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('employer_profile'),
            data={
                'company_name': 'Pixel Corp',
                'city': 'Taguig',
                'contact_person': 'Lee',
                'contact_number': '0212345678',
                'account_phone': '09170000004',
                'email': '',
                'avatar': avatar_file,
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, 'content', b'')[:800])
        db_user = User.objects.get(pk=user.pk)
        profile = EmployerProfile.objects.get(user=db_user)
        self.assertEqual(profile.company_name, 'Pixel Corp')
        self.assertTrue(db_user.avatar, 'Expected avatar file on User after profile save')

    def test_company_contact_change_does_not_change_login_phone(self):
        user = User.objects.create_user(
            username='09174000001',
            email='ec@test.com',
            password='secret',
            phone_number='09174000001',
            role='employer',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('employer_profile'),
            data={
                'company_name': 'East Corp',
                'city': 'Pasig',
                'contact_person': 'Pat',
                'contact_number': '0281234567',
                'account_phone': '09174000001',
                'email': 'ec@test.com',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.phone_number, '09174000001')
        profile = EmployerProfile.objects.get(user=user)
        self.assertEqual(profile.contact_number, '0281234567')

    def test_login_phone_change_updates_user_and_redirects_to_login(self):
        user = User.objects.create_user(
            username='09174000002',
            email='',
            password='secret',
            phone_number='09174000002',
            role='employer',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('employer_profile'),
            data={
                'company_name': 'West Corp',
                'city': 'Pasay',
                'contact_person': 'Chris',
                'contact_number': '0211111111',
                'account_phone': '09174000003',
                'email': '',
            },
            follow=False,
        )
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        user.refresh_from_db()
        self.assertEqual(user.phone_number, '09174000003')
        self.assertEqual(user.username, '09174000003')
        self.assertIsNone(authenticate(username='09174000002', password='secret'))
        self.assertIsNotNone(authenticate(username='09174000003', password='secret'))
