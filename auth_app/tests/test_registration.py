from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


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
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email=payload["email"])
        self.assertFalse(user.is_active)

    def test_registration_rejects_mismatched_passwords(self):
        """Reject registration when passwords do not match."""
        
        payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword12311!",
        }
        response = self.client.post("/api/register/", payload, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirmed_password", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_duplicate_email(self):
        """Reject duplicate emails without creating another user."""

        User.objects.create_user(
            username="existing_user",
            email="test@example.com",
            password="SecurePassword123!",
        )
        payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response = self.client.post("/api/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_hashes_password(self):
        """Ensure registered user passwords are hashed."""

        payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response = self.client.post("/api/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=payload["email"])
        self.assertNotEqual(user.password, payload["password"])
        self.assertTrue(user.check_password(payload["password"]))

    def test_registration_rejects_weak_password(self):
        """Reject registration with a weak password."""

        payload = {
            "email": "test@example.com",
            "password": "123",
            "confirmed_password": "123",
        }
        response = self.client.post("/api/register/", payload, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_missing_email(self):
        """Reject registration without an email address."""

        payload = {
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response = self.client.post("/api/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_invalid_email(self):
        """Reject registration with an invalid email address."""

        payload = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response = self.client.post("/api/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_sends_activation_email(self):
        """Send an activation email after successful registration."""

        payload = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response = self.client.post("/api/register/", payload, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [payload["email"]])
        self.assertIn("uid=", mail.outbox[0].body)
        self.assertIn("token=", mail.outbox[0].body)
