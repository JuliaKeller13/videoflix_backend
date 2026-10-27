from html import unescape

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from auth_app.utils import (
    build_activation_url,
    send_activation_email,
    send_password_reset_email,
)


@override_settings(
    FRONTEND_ACTIVATION_URL="http://127.0.0.1:5500/pages/auth/activate.html",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class EmailTemplateTests(TestCase):
    """Verify HTML emails and their plain-text alternatives."""

    def setUp(self):
        """Create a recipient for both email workflows."""
        self.user = get_user_model().objects.create_user(
            username="email@example.com",
            email="email@example.com",
        )

    def _html_content(self):
        """Extract the HTML alternative from a sent email."""
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(len(message.alternatives), 1)
        alternative = message.alternatives[0]
        self.assertEqual(alternative.mimetype, "text/html")
        return unescape(alternative.content)

    def test_activation_email_has_html_and_text(self):
        """Include a responsive button with the activation link."""
        token = "example-token"
        send_activation_email(self.user, token)
        html = self._html_content()
        url = build_activation_url(self.user, token)
        self.assertIn(url, mail.outbox[0].body)
        self.assertIn(f'href="{url}"', html)
        self.assertIn("Activate account", html)
        self.assertIn("@media", html)

    def test_password_reset_email_has_html_and_text(self):
        """Include a responsive button with the reset link."""
        send_password_reset_email(self.user)
        html = self._html_content()
        link = mail.outbox[0].body.strip().splitlines()[-1]
        self.assertIn("confirm_password.html?uid=", link)
        self.assertIn(f'href="{link}"', html)
        self.assertIn("Reset password", html)
        self.assertIn("@media", html)
