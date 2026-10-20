from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()

SUCCESS_RESPONSE = {
    "detail": "An email has been sent to reset your password."
}


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PasswordResetTests(APITestCase):
    """Test password reset requests and email delivery."""

    def setUp(self):
        """Create an active test user."""
        super().setUp()
        self.client.defaults["HTTP_ORIGIN"] = "http://127.0.0.1:5500"
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
        )

    def test_reset_sends_email_with_valid_link(self):
        """Send a valid reset link to an existing user."""
        response = self.client.post(
            "/api/password_reset/", {"email": "TEST@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, SUCCESS_RESPONSE)
        self.assertEqual(len(mail.outbox), 1)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        expected = f"confirm_password.html?uid={uid}&token={token}"
        self.assertIn(expected, mail.outbox[0].body)

    def test_unknown_email_returns_generic_response(self):
        """Do not reveal whether an account exists."""
        response = self.client.post(
            "/api/password_reset/", {"email": "unknown@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, SUCCESS_RESPONSE)
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_user_receives_no_email(self):
        """Do not send reset emails to inactive accounts."""
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/password_reset/", {"email": self.user.email}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, SUCCESS_RESPONSE)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_is_rejected(self):
        """Reject incorrectly formatted email addresses."""
        response = self.client.post(
            "/api/password_reset/", {"email": "invalid-email"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_email_is_rejected(self):
        """Require an email address."""
        response = self.client.post("/api/password_reset/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)