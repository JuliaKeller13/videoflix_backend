from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class LoginTests(APITestCase):
    """Tests for user login."""

    def setUp(self):
        """Create a user and login data for each test."""
        super().setUp()
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
            is_active=True,
        )
        self.payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }

    def test_login_with_valid_credentials(self):
        """Allow activated users to log in."""
        response = self.client.post("/api/login/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_login_rejects_wrong_password(self):
        """Reject login with an incorrect password."""
        self.payload["password"] = "WrongPassword123!"
        response = self.client.post("/api/login/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_rejects_inactive_user(self):
        """Reject login when the account is not activated."""
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post("/api/login/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)