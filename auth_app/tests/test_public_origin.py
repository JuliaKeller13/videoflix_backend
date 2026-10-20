from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html"
)
class PublicAuthOriginTests(APITestCase):
    """Test origin protection on public authentication endpoints."""

    def setUp(self):
        """Prepare valid requests for public authentication endpoints."""
        self.user = get_user_model().objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
        )
        self.registration = {
            "email": "new@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.confirm_url = f"/api/password_confirm/{uid}/{token}/"
        self.passwords = {
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
        }

    def test_registration_rejects_untrusted_origin(self):
        """Reject registration requests from other websites."""
        response = self.client.post(
            "/api/register/", self.registration,
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_registration_rejects_missing_origin(self):
        """Reject registration requests without an origin."""
        response = self.client.post("/api/register/", self.registration)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_reset_rejects_untrusted_origin(self):
        """Reject reset requests from other websites."""
        response = self.client.post(
            "/api/password_reset/", {"email": self.user.email},
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_reset_rejects_missing_origin(self):
        """Reject reset requests without an origin."""
        response = self.client.post(
            "/api/password_reset/", {"email": self.user.email}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_confirm_rejects_untrusted_origin(self):
        """Reject password changes from other websites."""
        response = self.client.post(
            self.confirm_url, self.passwords,
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_confirm_rejects_missing_origin(self):
        """Reject password changes without an origin."""
        response = self.client.post(self.confirm_url, self.passwords)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)