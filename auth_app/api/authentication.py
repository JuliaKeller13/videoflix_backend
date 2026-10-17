from urllib.parse import urlsplit

from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


def validate_origin(request):
    """Reject requests from untrusted origins."""
    frontend = urlsplit(settings.FRONTEND_ACTIVATION_URL)
    trusted_origin = f"{frontend.scheme}://{frontend.netloc}"
    if request.META.get("HTTP_ORIGIN") != trusted_origin:
        raise PermissionDenied("Untrusted request origin.")


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate requests using JWT cookies."""

    def authenticate(self, request):
        """Validate the access token and request origin."""
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            validate_origin(request)
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        return user, validated_token