from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ActivationTests(APITestCase):
    def test_activation_with_valid_token(self):
        """Activate an inactive user with a valid token."""

        user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
            is_active=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(f"/api/activate/{uid}/{token}/")
        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Account successfully activated."}    )
        self.assertTrue(user.is_active)

    def test_activation_rejects_invalid_token(self):
        """Reject activation with an invalid token."""

        user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="SecurePassword123!",
            is_active=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(f"/api/activate/{uid}/invalid-token/")
        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(user.is_active)

    def test_activation_rejects_unknown_user(self):
        """Reject activation when the user does not exist."""
        
        uid = urlsafe_base64_encode(force_bytes(999999))
        response = self.client.get(f"/api/activate/{uid}/invalid-token/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activation_rejects_malformed_uid(self):
        """Reject malformed activation user IDs."""
        response = self.client.get("/api/activate/____/invalid-token/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)