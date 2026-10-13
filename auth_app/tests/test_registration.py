from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class RegistrationTests(APITestCase):
    """Tests for user registration."""

    def test_registration_creates_inactive_user(self):
        """New users must activate their accounts."""
        payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response = self.client.post("/api/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(get_user_model().objects.count(), 1)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertFalse(user.is_active)