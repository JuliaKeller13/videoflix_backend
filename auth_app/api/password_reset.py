from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers


class PasswordResetRequestSerializer(serializers.Serializer):
    """Validate an email address for a password reset request."""

    email = serializers.EmailField()


def send_password_reset_email(user):
    """Email a password reset link to the user."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_url = urljoin(
        settings.FRONTEND_ACTIVATION_URL, "confirm_password.html"
    )
    link = f"{frontend_url}?{urlencode({'uid': uid, 'token': token})}"
    send_mail(
        "Reset your Videoflix password",
        f"Reset your password using this link:\n{link}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )