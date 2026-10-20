from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html"
)
class LoginTests(APITestCase):
    """Test login credentials, JWT cookies, and request origins."""

    def setUp(self):
        """Prepare an active user and trusted frontend origin."""
        super().setUp()
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
        )
        self.payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }
        self.client.defaults["HTTP_ORIGIN"] = "http://127.0.0.1:5500"

    def test_login_success(self):
        """Return JWT cookies for valid credentials."""
        response = self.client.post("/api/login/", self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_login_wrong_password(self):
        """Reject incorrect credentials."""
        self.payload["password"] = "WrongPassword123!"
        response = self.client.post("/api/login/", self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        """Reject login for inactive users."""
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post("/api/login/", self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_rejects_untrusted_origin(self):
        """Reject login requests from an untrusted website."""
        response = self.client.post(
            "/api/login/", self.payload,
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("access_token", response.cookies)

    def test_login_rejects_missing_origin(self):
        """Reject login requests without an origin."""
        self.client.defaults.pop("HTTP_ORIGIN")
        response = self.client.post("/api/login/", self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)