"""Tests for logging out with JWT cookies."""

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


TRUSTED_ORIGIN = "http://127.0.0.1:5500"


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html"
)
class LogoutTests(APITestCase):
    """Test logout and authentication-cookie removal."""

    def setUp(self):
        """Prepare authentication cookies for testing."""
        super().setUp()
        self.client.cookies["access_token"] = "expired-access"
        self.client.cookies["refresh_token"] = "expired-refresh"

    def test_logout_clears_both_cookies(self):
        """Delete both cookies even when the tokens are invalid."""
        response = self.client.post(
            "/api/logout/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for name in ("access_token", "refresh_token"):
            self.assertIn(name, response.cookies)
            self.assertEqual(response.cookies[name].value, "")
            self.assertEqual(response.cookies[name]["max-age"], 0)

    def test_logout_without_cookies_succeeds(self):
        """Allow logout when authentication cookies are absent."""
        self.client.cookies.clear()
        response = self.client.post(
            "/api/logout/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_rejects_untrusted_origin(self):
        """Reject logout requests from an untrusted website."""
        response = self.client.post(
            "/api/logout/", HTTP_ORIGIN="https://evil.example"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("access_token", response.cookies)

    def test_logout_rejects_missing_origin(self):
        """Reject logout requests without an origin."""
        response = self.client.post("/api/logout/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)