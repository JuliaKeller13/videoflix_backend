from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class RegistrationTests(APITestCase):
    """Tests for user registration."""

    def setUp(self):
        """Prepare valid registration data for each test."""
        super().setUp()
        self.payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }

    def test_registration_creates_inactive_user(self):
        """New users must activate their accounts."""
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email=self.payload["email"])
        self.assertFalse(user.is_active)

    def test_registration_rejects_mismatched_passwords(self):
        """Reject registration when passwords do not match."""
        self.payload["confirmed_password"] = "DifferentPassword123!"
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirmed_password", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_duplicate_email(self):
        """Reject duplicate emails without creating another user."""
        User.objects.create_user(
            username="existing_user",
            email=self.payload["email"],
            password="SecurePassword123!",
        )
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_hashes_password(self):
        """Ensure registered user passwords are hashed."""
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.payload["email"])
        self.assertNotEqual(user.password, self.payload["password"])
        self.assertTrue(user.check_password(self.payload["password"]))

    def test_registration_rejects_weak_password(self):
        """Reject registration with a weak password."""
        self.payload["password"] = "123"
        self.payload["confirmed_password"] = "123"
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_missing_email(self):
        """Reject registration without an email address."""
        self.payload.pop("email")
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_invalid_email(self):
        """Reject registration with an invalid email address."""
        self.payload["email"] = "invalid-email"
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_sends_activation_email(self):
        """Send an activation email after successful registration."""
        response = self.client.post("/api/register/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.payload["email"]])
        self.assertIn("uid=", mail.outbox[0].body)
        self.assertIn("token=", mail.outbox[0].body)

    def test_registration_handles_integrity_error(self):
        """Return a validation error when user creation fails."""
        payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }

        with patch(
            "auth_app.api.serializers.User.objects.create_user",
            side_effect=IntegrityError,
        ):
            response = self.client.post("/api/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"email": "Please check your registration details."},
        )