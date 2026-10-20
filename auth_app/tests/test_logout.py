from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
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

    def test_logout_revokes_refresh_token(self):
        """Prevent refreshing tokens after logout."""
        user = get_user_model().objects.create_user(
            username="test@example.com"
        )
        token = str(RefreshToken.for_user(user))
        self.client.cookies["refresh_token"] = token
        response = self.client.post(
            "/api/logout/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.cookies["refresh_token"] = token
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)