from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


User = get_user_model()
TRUSTED_ORIGIN = "http://127.0.0.1:5500"


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html"
)
class TokenRefreshTests(APITestCase):
    """Test token refresh through HttpOnly cookies."""

    def setUp(self):
        """Prepare an active user and refresh-token cookie."""
        super().setUp()
        self.user = User.objects.create_user(
            username="test@example.com",
            password="SecurePassword123!",
        )
        self.client.cookies["refresh_token"] = str(
            RefreshToken.for_user(self.user)
        )

    def test_refresh_sets_access_cookie(self):
        """Issue a new HttpOnly access-token cookie."""
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        access = AccessToken(response.cookies["access_token"].value)
        self.assertEqual(str(access["user_id"]), str(self.user.pk))

    def test_refresh_rejects_missing_cookie(self):
        """Reject requests without a refresh token."""
        del self.client.cookies["refresh_token"]
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_invalid_cookie(self):
        """Reject an invalid refresh token."""
        self.client.cookies["refresh_token"] = "invalid-token"
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_access_token(self):
        """Reject an access token used as a refresh token."""
        access = RefreshToken.for_user(self.user).access_token
        self.client.cookies["refresh_token"] = str(access)
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_inactive_user(self):
        """Reject token refresh for an inactive account."""
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN=TRUSTED_ORIGIN
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_untrusted_origin(self):
        """Reject refresh requests from another website."""
        response = self.client.post(
            "/api/token/refresh/", HTTP_ORIGIN="https://evil.example"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_rejects_missing_origin(self):
        """Reject refresh requests without an origin."""
        response = self.client.post("/api/token/refresh/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)