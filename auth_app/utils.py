from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_activation_url(user, token):
    """Build the frontend activation URL."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    query = urlencode({"uid": uid, "token": token})
    return f"{settings.FRONTEND_ACTIVATION_URL}?{query}"


def send_activation_email(user, token):
    """Send the account activation email."""
    activation_url = build_activation_url(user, token)
    send_mail(
        subject="Activate your Videoflix account",
        message=f"Activate your account: {activation_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )