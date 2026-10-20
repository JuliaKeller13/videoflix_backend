from rest_framework import status
from rest_framework.test import APITestCase


class CorsTests(APITestCase):
    """Verify CORS for the Videoflix frontend."""

    def test_frontend_origin_is_allowed(self):
        """Allow credentialed requests from the frontend."""
        response = self.client.options(
            "/api/login/",
            HTTP_ORIGIN="http://127.0.0.1:5500",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "http://127.0.0.1:5500",
        )
        self.assertEqual(
            response["Access-Control-Allow-Credentials"], "true"
        )

    def test_untrusted_origin_is_not_allowed(self):
        """Do not authorize an unrelated website."""
        response = self.client.options(
            "/api/login/",
            HTTP_ORIGIN="https://evil.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", response)