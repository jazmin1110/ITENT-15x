import io
from datetime import date
from unittest.mock import patch

from django.contrib.auth import authenticate
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from PIL import Image
from django.urls import reverse

from accounts.form_utils import first_invalid_field_name
from accounts.forms import EmployerProfileForm, WorkerProfileForm
from accounts.models import User, WorkerProfile, WorkerPortfolioItem, EmployerProfile
from jobs.models import Application, ApplicationSkillRating, Job

# Valid biodata for worker profile POSTs / WorkerProfileForm (18+ DOB).
_WORKER_BIODATA_VALID = {'date_of_birth': '1990-05-15', 'gender': 'male'}


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
                **_WORKER_BIODATA_VALID,
                'city': 'Quezon City',
                'contact_number': '09179876543',
                'skills': ['Helper'],
                'email': 'w2@test.com',
                'national_id_number': '',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tingnan ang mga trabaho')
        profile = WorkerProfile.objects.get(user=user)
        self.assertEqual(str(profile.date_of_birth), '1990-05-15')
        self.assertEqual(profile.gender, 'male')

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
                **_WORKER_BIODATA_VALID,
                'city': 'Manila',
                'contact_number': '09171111111',
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
                **_WORKER_BIODATA_VALID,
                'city': 'Makati',
                'contact_number': '09172000002',
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
                **_WORKER_BIODATA_VALID,
                'city': 'Pasig',
                'contact_number': '09173000001',
                'skills': ['Driver'],
                'email': 'b@test.com',
                'national_id_number': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ginagamit na ang phone number')
        user_b.refresh_from_db()
        self.assertEqual(user_b.phone_number, '09173000002')

    def test_skills_saved_as_dicts_and_aggregate_years_is_max(self):
        user = User.objects.create_user(
            username='09177000001',
            email='',
            password='secret',
            phone_number='09177000001',
            role='worker',
        )
        form = WorkerProfileForm(
            data={
                'full_name': 'Skill Max',
                **_WORKER_BIODATA_VALID,
                'city': 'Manila',
                'contact_number': '09177000001',
                'skills': ['Helper', 'Masonry'],
                'years_Helper': 2,
                'years_Masonry': 7,
                'email': '',
                'national_id_number': '',
            },
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save(commit=False)
        profile.user = user
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.years_experience, 7)
        self.assertEqual(
            profile.skills,
            [
                {'skill': 'Helper', 'years_experience': 2},
                {'skill': 'Masonry', 'years_experience': 7},
            ],
        )

    def test_custom_skill_only_valid(self):
        user = User.objects.create_user(
            username='09177000002',
            email='',
            password='secret',
            phone_number='09177000002',
            role='worker',
        )
        form = WorkerProfileForm(
            data={
                'full_name': 'Custom Only',
                **_WORKER_BIODATA_VALID,
                'city': 'Taguig',
                'contact_number': '09177000002',
                'skills': [],
                'custom_skill_name': ['Welding'],
                'custom_skill_years': ['4'],
                'email': '',
                'national_id_number': '',
            },
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save(commit=False)
        profile.user = user
        profile.save()
        self.assertEqual(
            profile.skills,
            [{'skill': 'Welding', 'years_experience': 4}],
        )
        self.assertEqual(profile.years_experience, 4)

    def test_invalid_post_no_skills_shows_top_alert_and_skill_error(self):
        user = User.objects.create_user(
            username='09178000001',
            email='',
            password='secret',
            phone_number='09178000001',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'No Skills User',
                **_WORKER_BIODATA_VALID,
                'city': 'Manila',
                'contact_number': '09178000001',
                'email': '',
                'national_id_number': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hindi na-save ang profile')
        self.assertContains(response, 'Pumili ng kahit isang skill')

    def test_invalid_post_logs_warning_with_form_errors_json(self):
        user = User.objects.create_user(
            username='09178000002',
            email='',
            password='secret',
            phone_number='09178000002',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        with self.assertLogs('accounts.views', level='WARNING') as cm:
            response = client.post(
                reverse('worker_profile'),
                data={
                    'full_name': 'X',
                    **_WORKER_BIODATA_VALID,
                    'city': 'Manila',
                    'contact_number': '09178000002',
                    'email': '',
                    'national_id_number': '',
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any('worker_profile validation failed' in line for line in cm.output),
            cm.output,
        )
        self.assertTrue(
            any('skills' in line for line in cm.output),
            cm.output,
        )

    def test_post_saves_when_post_mirrors_browser_multivalue_skills_and_custom_rows(self):
        user = User.objects.create_user(
            username='09178000003',
            email='',
            password='secret',
            phone_number='09178000003',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'Multi POST',
                **_WORKER_BIODATA_VALID,
                'city': 'Makati',
                'contact_number': '09178000003',
                'skills': ['Masonry', 'Helper'],
                'years_Masonry': '3',
                'years_Helper': '1',
                'custom_skill_name': ['Pipefitting', ''],
                'custom_skill_years': ['5', ''],
                'email': '',
                'national_id_number': '',
            },
        )
        self.assertRedirects(response, reverse('worker_profile'))
        profile = WorkerProfile.objects.get(user=user)
        profile.refresh_from_db()
        self.assertEqual(len(profile.skills), 3)
        codes = {entry['skill']: entry.get('years_experience') for entry in profile.skills}
        self.assertEqual(codes.get('Masonry'), 3)
        self.assertEqual(codes.get('Helper'), 1)
        self.assertEqual(codes.get('Pipefitting'), 5)

    def test_invalid_per_skill_years_shows_alert_and_focuses_year_wrap(self):
        user = User.objects.create_user(
            username='09178000004',
            email='',
            password='secret',
            phone_number='09178000004',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'Bad Years',
                **_WORKER_BIODATA_VALID,
                'city': 'Pasig',
                'contact_number': '09178000004',
                'skills': ['Helper'],
                'years_Helper': '99',
                'email': '',
                'national_id_number': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hindi na-save ang profile')
        self.assertContains(response, 'id="profile-field-wrap-years_Helper"')
        self.assertContains(response, 'var name = "years_Helper"')

    def test_legacy_lowercase_predefined_skill_loads_canonical_checkbox_and_years(self):
        user = User.objects.create_user(
            username='09178000005',
            email='',
            password='secret',
            phone_number='09178000005',
            role='worker',
        )
        WorkerProfile.objects.create(
            user=user,
            full_name='Legacy Skills',
            city='X',
            contact_number='09178000005',
            skills=[{'skill': 'masonry', 'years_experience': 5}],
            years_experience=5,
        )
        form = WorkerProfileForm(instance=user.worker_profile, user=user)
        self.assertIn('Masonry', form.predefined_skills_selected_codes)
        self.assertEqual(form.fields['years_Masonry'].initial, 5)
        self.assertEqual(form.custom_skills_initial, [])

    def test_save_canonicalizes_predefined_skill_casing_in_db(self):
        user = User.objects.create_user(
            username='09178000006',
            email='',
            password='secret',
            phone_number='09178000006',
            role='worker',
        )
        WorkerProfile.objects.create(
            user=user,
            full_name='Norm Save',
            city='Quezon City',
            contact_number='09178000006',
            skills=[{'skill': 'HELPER', 'years_experience': 2}],
            years_experience=2,
        )
        form = WorkerProfileForm(
            data={
                'full_name': 'Norm Save',
                **_WORKER_BIODATA_VALID,
                'city': 'Quezon City',
                'contact_number': '09178000006',
                'skills': ['Helper'],
                'years_Helper': 3,
                'email': '',
                'national_id_number': '',
            },
            instance=user.worker_profile,
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save(commit=False)
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.skills, [{'skill': 'Helper', 'years_experience': 3}])

    def test_unbound_form_loads_custom_skills_from_instance(self):
        user = User.objects.create_user(
            username='09178000007',
            email='',
            password='secret',
            phone_number='09178000007',
            role='worker',
        )
        WorkerProfile.objects.create(
            user=user,
            full_name='Custom Rows',
            city='Z',
            contact_number='09178000007',
            skills=[{'skill': 'Welding', 'years_experience': 6}],
            years_experience=6,
        )
        form = WorkerProfileForm(instance=user.worker_profile, user=user)
        self.assertEqual(len(form.custom_skills_initial), 1)
        self.assertEqual(form.custom_skills_initial[0]['name'], 'Welding')
        self.assertEqual(form.custom_skills_initial[0]['years'], 6)

    def test_age_property_from_date_of_birth(self):
        user = User.objects.create_user(
            username='09178000008',
            email='',
            password='secret',
            phone_number='09178000008',
            role='worker',
        )
        profile = WorkerProfile.objects.create(
            user=user,
            full_name='Age Test',
            city='Manila',
            contact_number='09178000008',
            skills=[{'skill': 'Helper', 'years_experience': 1}],
            years_experience=1,
            date_of_birth=date(2000, 6, 10),
            gender='female',
        )

        class EveBirthday(date):
            @classmethod
            def today(cls):
                return cls(2026, 6, 9)

        with patch('accounts.models.date', EveBirthday):
            self.assertEqual(profile.age, 25)

        class OnBirthday(date):
            @classmethod
            def today(cls):
                return cls(2026, 6, 10)

        with patch('accounts.models.date', OnBirthday):
            self.assertEqual(profile.age, 26)

    def test_clean_date_of_birth_rejects_future_and_under_18(self):
        user = User.objects.create_user(
            username='09178000009',
            email='',
            password='secret',
            phone_number='09178000009',
            role='worker',
        )
        future = date.today().replace(year=date.today().year + 1)
        form = WorkerProfileForm(
            data={
                'full_name': 'Dob Test',
                'date_of_birth': future.isoformat(),
                'gender': 'male',
                'city': 'Manila',
                'contact_number': '09178000009',
                'skills': ['Helper'],
                'email': '',
                'national_id_number': '',
            },
            user=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)
        young = date(date.today().year - 10, 6, 15)
        form2 = WorkerProfileForm(
            data={
                'full_name': 'Dob Test',
                'date_of_birth': young.isoformat(),
                'gender': 'male',
                'city': 'Manila',
                'contact_number': '09178000009',
                'skills': ['Helper'],
                'email': '',
                'national_id_number': '',
            },
            user=user,
        )
        self.assertFalse(form2.is_valid())
        self.assertIn('date_of_birth', form2.errors)

    def test_optional_biodata_fields_round_trip(self):
        user = User.objects.create_user(
            username='09178000010',
            email='',
            password='secret',
            phone_number='09178000010',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        client.post(
            reverse('worker_profile'),
            data={
                'full_name': 'Extras',
                **_WORKER_BIODATA_VALID,
                'marital_status': 'single',
                'nationality': 'Filipino',
                'religion': 'None',
                'languages_known': 'Tagalog, English',
                'city': 'Manila',
                'contact_number': '09178000010',
                'skills': ['Helper'],
                'email': '',
                'national_id_number': '',
            },
        )
        profile = WorkerProfile.objects.get(user=user)
        self.assertEqual(profile.marital_status, 'single')
        self.assertEqual(profile.nationality, 'Filipino')
        self.assertEqual(profile.religion, 'None')
        self.assertEqual(profile.languages_known, 'Tagalog, English')


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
                'city': 'Manila',
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


class FirstInvalidFieldNameTests(TestCase):
    def test_returns_first_declared_field_with_error(self):
        User.objects.create_user(
            username='09175000003',
            email='',
            password='secret',
            phone_number='09175000003',
            role='worker',
        )
        user = User.objects.create_user(
            username='09175000001',
            email='',
            password='secret',
            phone_number='09175000001',
            role='worker',
        )
        form = WorkerProfileForm(
            data={
                'full_name': 'OK',
                **_WORKER_BIODATA_VALID,
                'city': 'Manila',
                'contact_number': '09175000003',
                'skills': ['Helper'],
                'email': '',
                'national_id_number': '',
            },
            user=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('contact_number', form.errors)
        self.assertEqual(first_invalid_field_name(form), 'contact_number')

    def test_none_when_valid(self):
        user = User.objects.create_user(
            username='09175000002',
            email='',
            password='secret',
            phone_number='09175000002',
            role='worker',
        )
        form = WorkerProfileForm(
            data={
                'full_name': 'OK',
                **_WORKER_BIODATA_VALID,
                'city': 'Manila',
                'contact_number': '09175000002',
                'skills': ['Helper'],
                'email': '',
                'national_id_number': '',
            },
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(first_invalid_field_name(form))


class ProfileFormFocusUXTests(TestCase):
    def test_worker_invalid_post_includes_focus_script_for_first_error(self):
        user = User.objects.create_user(
            username='09176000001',
            email='',
            password='secret',
            phone_number='09176000001',
            role='worker',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('worker_profile'),
            data={
                'full_name': '',
                **_WORKER_BIODATA_VALID,
                'city': 'Quezon City',
                'contact_number': '09176000001',
                'skills': ['Helper'],
                'email': '',
                'national_id_number': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        self.assertContains(response, 'var name = "full_name"')

    def test_employer_invalid_post_includes_focus_script_for_first_error(self):
        user = User.objects.create_user(
            username='09176000002',
            email='',
            password='secret',
            phone_number='09176000002',
            role='employer',
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('employer_profile'),
            data={
                'company_name': '',
                'city': 'Makati',
                'contact_person': 'Maria',
                'contact_number': '0288880000',
                'account_phone': '09176000002',
                'email': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        self.assertContains(response, 'var name = "company_name"')


class PortfolioAccessTests(TestCase):
    """Portfolio media and employer job-scoped page require applicant relationship."""

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
        self.other_employer = User.objects.create_user(
            username='09991234512',
            email='e12@test.com',
            password='pass',
            role='employer',
            phone_number='09991234512',
        )
        EmployerProfile.objects.create(
            user=self.employer,
            company_name='Test Co',
            city='Manila',
            contact_person='A',
            contact_number='09991234510',
        )
        EmployerProfile.objects.create(
            user=self.other_employer,
            company_name='Other Co',
            city='Manila',
            contact_person='B',
            contact_number='09991234512',
        )
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker,
            full_name='Worker One',
            city='Manila',
            contact_number='09991234511',
            years_experience=0,
            skills=[{'skill': 'Helper', 'years_experience': 1}],
        )
        buf = io.BytesIO()
        Image.new('RGB', (40, 40), color='red').save(buf, format='PNG')
        buf.seek(0)
        photo = SimpleUploadedFile('p.png', buf.read(), content_type='image/png')
        self.item = WorkerPortfolioItem.objects.create(
            worker_profile=self.worker_profile,
            title='Job',
            photo=photo,
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
        self.client = Client()

    def test_worker_can_fetch_own_portfolio_photo(self):
        self.client.force_login(self.worker)
        r = self.client.get(reverse('portfolio_item_photo', args=[self.item.pk]))
        self.assertEqual(r.status_code, 200)

    def test_employer_with_application_can_fetch_photo(self):
        Application.objects.create(job=self.job, worker=self.worker)
        self.client.force_login(self.employer)
        r = self.client.get(reverse('portfolio_item_photo', args=[self.item.pk]))
        self.assertEqual(r.status_code, 200)

    def test_employer_without_application_404(self):
        self.client.force_login(self.other_employer)
        r = self.client.get(reverse('portfolio_item_photo', args=[self.item.pk]))
        self.assertEqual(r.status_code, 404)

    def test_employer_portfolio_page_404_without_application(self):
        self.client.force_login(self.employer)
        r = self.client.get(
            reverse('employer_worker_portfolio', args=[self.job.id, self.worker.id]),
        )
        self.assertEqual(r.status_code, 404)

    def test_employer_portfolio_page_ok_with_application(self):
        Application.objects.create(job=self.job, worker=self.worker)
        self.client.force_login(self.employer)
        r = self.client.get(
            reverse('employer_worker_portfolio', args=[self.job.id, self.worker.id]),
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Portfolio')

    def test_employer_can_save_per_skill_ratings(self):
        Application.objects.create(job=self.job, worker=self.worker)
        self.worker_profile.skills = [{'skill': 'Helper', 'years_experience': 2}]
        self.worker_profile.save()
        self.client.force_login(self.employer)
        r = self.client.post(
            reverse('employer_worker_portfolio', args=[self.job.id, self.worker.id]),
            data={'employer_rating_0': '4'},
        )
        self.assertRedirects(
            r,
            reverse('employer_worker_portfolio', args=[self.job.id, self.worker.id]),
            fetch_redirect_response=False,
        )
        app = Application.objects.get(job=self.job, worker=self.worker)
        self.assertEqual(
            ApplicationSkillRating.objects.get(application=app, skill_name='Helper').score,
            4,
        )
