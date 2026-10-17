from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.api.authentication import CookieJWTAuthentication


User = get_user_model()


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html"
)
class CookieAuthenticationTests(APITestCase):
    """Test JWT cookies and request origin validation."""

    def setUp(self):
        """Prepare a user and a valid access token."""
        super().setUp()
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

    def test_valid_access_cookie_authenticates_user(self):
        """Authenticate a user using an access-token cookie."""
        request = APIRequestFactory().get("/")
        request.COOKIES["access_token"] = self.token
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], self.user)

    def test_missing_access_cookie(self):
        """Return None when no access-token cookie exists."""
        request = APIRequestFactory().get("/")
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNone(result)

    def test_invalid_access_cookie_is_rejected(self):
        """Reject authentication with an invalid access token."""
        request = APIRequestFactory().get("/")
        request.COOKIES["access_token"] = "invalid-token"
        with self.assertRaises(InvalidToken):
            CookieJWTAuthentication().authenticate(request)

    def test_rejects_untrusted_origin(self):
        """Reject cookie requests from an untrusted origin."""
        request = APIRequestFactory().post(
            "/", HTTP_ORIGIN="https://evil.example"
        )
        request.COOKIES["access_token"] = self.token
        with self.assertRaises(PermissionDenied):
            CookieJWTAuthentication().authenticate(request)

    def test_accepts_trusted_origin(self):
        """Accept cookie requests from the configured frontend."""
        request = APIRequestFactory().post(
            "/", HTTP_ORIGIN="http://127.0.0.1:5500"
        )
        request.COOKIES["access_token"] = self.token
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], self.user)

    def test_rejects_missing_origin_on_post(self):
        """Reject unsafe cookie requests without an origin."""
        request = APIRequestFactory().post("/")
        request.COOKIES["access_token"] = self.token
        with self.assertRaises(PermissionDenied):
            CookieJWTAuthentication().authenticate(request)