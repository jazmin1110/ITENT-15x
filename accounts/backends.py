from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class PhoneEmailBackend(ModelBackend):
    """Authenticate with phone number only."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        phone = (username or '').strip()
        # Support user input like +63XXXXXXXXX by normalizing to 0XXXXXXXXX.
        if phone.startswith('+63'):
            phone = '0' + phone[3:]

        try:
            user = User.objects.get(
                Q(username=phone)
                | Q(phone_number=phone)
            )
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
