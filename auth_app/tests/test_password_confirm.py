from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class PasswordConfirmTests(APITestCase):
    """Test password reset confirmation and token validation."""

    def setUp(self):
        """Prepare a user, reset link, and valid passwords."""
        super().setUp()
        self.user = User.objects.create_user(
            username="test@example.com",
            password="OldSecurePassword123!",
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)
        self.url = f"/api/password_confirm/{self.uid}/{self.token}/"
        self.payload = {
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
        }

    def test_valid_token_resets_password(self):
        """Save the new password and return the documented response."""
        response = self.client.post(self.url, self.payload)
        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"detail": "Your Password has been successfully reset."},
        )
        self.assertTrue(self.user.check_password("NewSecurePassword123!"))
        self.assertFalse(self.user.check_password("OldSecurePassword123!"))

    def test_used_token_is_rejected(self):
        """Prevent reusing a token after a successful reset."""
        self.client.post(self.url, self.payload)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_token_is_rejected(self):
        """Reject an incorrect reset token."""
        url = f"/api/password_confirm/{self.uid}/invalid-token/"
        response = self.client.post(url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldSecurePassword123!"))

    def test_unknown_user_is_rejected(self):
        """Reject reset links for nonexistent users."""
        uid = urlsafe_base64_encode(force_bytes(999999))
        url = f"/api/password_confirm/{uid}/{self.token}/"
        response = self.client.post(url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uid_is_rejected(self):
        """Reject malformed Base64 user identifiers."""
        url = f"/api/password_confirm/not-base64/{self.token}/"
        response = self.client.post(url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mismatched_passwords_are_rejected(self):
        """Require the two password fields to match."""
        self.payload["confirm_password"] = "DifferentPassword123!"
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldSecurePassword123!"))

    def test_weak_password_is_rejected(self):
        """Apply Django's configured password validators."""
        self.payload["new_password"] = "123"
        self.payload["confirm_password"] = "123"
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)