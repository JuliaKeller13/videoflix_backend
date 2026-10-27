import os
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from dotenv import dotenv_values
from rest_framework.test import APITestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSOLE_BACKEND = "django.core.mail.backends.console.EmailBackend"
SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class EmailSettingsTests(SimpleTestCase):
    """Test the email configuration used by new installations."""

    def _load_backend(self, backend):
        """Read Django settings with the requested email backend."""
        with patch.dict(os.environ, {"EMAIL_BACKEND": backend}):
            values = runpy.run_path(
                str(PROJECT_ROOT / "core" / "settings.py")
            )
        return values["EMAIL_BACKEND"]

    def test_console_backend_can_be_selected(self):
        """Support logging emails instead of sending them."""
        self.assertEqual(
            self._load_backend(CONSOLE_BACKEND), CONSOLE_BACKEND
        )

    def test_smtp_backend_remains_available(self):
        """Preserve support for SMTP and Mailtrap."""
        self.assertEqual(
            self._load_backend(SMTP_BACKEND), SMTP_BACKEND
        )

    def test_environment_template_uses_console(self):
        """Let fresh installations work without SMTP credentials."""
        values = dotenv_values(PROJECT_ROOT / ".env.template")
        self.assertEqual(values.get("EMAIL_BACKEND"), CONSOLE_BACKEND)


@override_settings(EMAIL_BACKEND=CONSOLE_BACKEND)
class ConsoleEmailIntegrationTests(APITestCase):
    """Test email delivery through Django's console backend."""

    def setUp(self):
        """Configure the trusted frontend origin."""
        self.client.defaults["HTTP_ORIGIN"] = "http://127.0.0.1:5500"

    def _post_and_capture(self, url, payload):
        """Capture the email printed during an API request."""
        output = StringIO()
        with redirect_stdout(output):
            response = self.client.post(url, payload, format="json")
        return response, output.getvalue()

    def test_registration_prints_activation_link(self):
        """Print a usable activation URL to the console."""
        payload = {
            "email": "console@example.com",
            "password": "SecurePassword123!",
            "confirmed_password": "SecurePassword123!",
        }
        response, output = self._post_and_capture(
            "/api/register/", payload
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("activate.html?uid=", output)
        self.assertIn("&token=", output)

    def test_password_reset_prints_reset_link(self):
        """Print a usable password-reset URL to the console."""
        user = get_user_model().objects.create_user(
            username="console@example.com",
            email="console@example.com",
            password="SecurePassword123!",
        )
        response, output = self._post_and_capture(
            "/api/password_reset/", {"email": user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("confirm_password.html?uid=", output)
        self.assertIn("&token=", output)
