from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


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
