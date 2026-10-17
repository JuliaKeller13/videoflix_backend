"""Integration tests for JWT cookie authentication."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import path
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class ProtectedTestView(APIView):
    """Provide a protected endpoint for integration tests."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the authenticated user's ID."""
        return Response({"user_id": request.user.pk})

    def post(self, request):
        """Handle an authenticated test request."""
        return Response({"user_id": request.user.pk})


urlpatterns = [
    path("protected-test/", ProtectedTestView.as_view()),
]


@override_settings(
    ROOT_URLCONF=__name__,
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html",
)
class AuthenticationIntegrationTests(APITestCase):
    """Test cookie authentication through protected DRF views."""

    def setUp(self):
        """Prepare an authenticated test client."""
        super().setUp()
        self.user = User.objects.create_user(username="test@example.com")
        token = RefreshToken.for_user(self.user).access_token
        self.client.cookies["access_token"] = str(token)

    def test_access_cookie_authenticates_protected_view(self):
        """Allow access with a valid JWT cookie."""
        response = self.client.get("/protected-test/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], self.user.pk)

    def test_post_accepts_trusted_origin(self):
        """Allow authenticated POST from the trusted frontend."""
        response = self.client.post(
            "/protected-test/", HTTP_ORIGIN="http://127.0.0.1:5500"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_rejects_untrusted_origin(self):
        """Reject authenticated POST from an untrusted origin."""
        response = self.client.post(
            "/protected-test/", HTTP_ORIGIN="https://evil.example"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_rejects_missing_origin(self):
        """Reject authenticated POST without an origin."""
        response = self.client.post("/protected-test/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)