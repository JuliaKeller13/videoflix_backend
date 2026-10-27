from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_activation_url(user, token):
    """Build the frontend activation URL."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    query = urlencode({"uid": uid, "token": token})
    return f"{settings.FRONTEND_ACTIVATION_URL}?{query}"


def build_password_reset_url(user):
    """Build the frontend password reset URL."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    page_url = urljoin(
        settings.FRONTEND_ACTIVATION_URL, "confirm_password.html"
    )
    return f"{page_url}?{urlencode({'uid': uid, 'token': token})}"


def _send_email(user, subject, text, template_name, context):
    """Send plain-text and HTML versions of an email."""
    send_mail(
        subject=subject,
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=render_to_string(template_name, context),
        fail_silently=False,
    )


def send_activation_email(user, token):
    """Send an account activation email."""
    url = build_activation_url(user, token)
    _send_email(
        user=user,
        subject="Activate your Videoflix account",
        text=f"Activate your account: {url}",
        template_name="activation_email.html",
        context={"action_url": url},
    )


def send_password_reset_email(user):
    """Send a password reset email."""
    url = build_password_reset_url(user)
    _send_email(
        user=user,
        subject="Reset your Videoflix password",
        text=f"Reset your password using this link:\n{url}",
        template_name="password_reset_email.html",
        context={"action_url": url},
    )
