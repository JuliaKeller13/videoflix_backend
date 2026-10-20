from binascii import Error as Base64Error

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.api.authentication import validate_origin
from auth_app.api.serializers import (
    PasswordConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
)
from auth_app.utils import (
    send_activation_email,
    send_password_reset_email,
)


User = get_user_model()


class RegisterView(APIView):
    """Handle user registration."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        """Register a user and initiate account activation."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = default_token_generator.make_token(user)
        send_activation_email(user, token)
        return Response(
            {"user": {"id": user.pk, "email": user.email}},
            status=status.HTTP_201_CREATED,
        )


class ActivateView(APIView):
    """Handle account activation."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, uid, token):
        """Activate a user with a valid token."""
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            return Response({"message": "Invalid activation link."}, status=400)
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])
            return Response({"message": "Account activated."}, status=200)
        else:
            return Response({"message": "Invalid activation link."}, status=400)


class LoginView(APIView):
    """Handle user login."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Authenticate credentials from the trusted frontend."""
        validate_origin(request)
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"message": "Invalid credentials."}, status=401)
        refresh = RefreshToken.for_user(user)
        response = Response({"message": "Login successful."}, status=200)
        options = {"httponly": True, "secure": not settings.DEBUG, "samesite": "Lax"}
        response.set_cookie("access_token", str(refresh.access_token), **options)
        response.set_cookie("refresh_token", str(refresh), **options)
        return response


class TokenRefreshView(APIView):
    """Refresh access tokens using a refresh-token cookie."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Issue a new access token from a refresh cookie."""
        validate_origin(request)
        try:
            refresh = RefreshToken(request.COOKIES["refresh_token"])
            access = refresh.access_token
            JWTAuthentication().get_user(access)
        except (KeyError, TokenError, AuthenticationFailed):
            return Response({"message": "Invalid refresh token."}, status=401)
        response = Response({"message": "Token refreshed."}, status=200)
        response.set_cookie(
            "access_token", str(access), httponly=True,
            secure=not settings.DEBUG, samesite="Lax"
        )
        return response


class LogoutView(APIView):
    """Handle logout by removing and revoking JWT cookies."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Revoke the refresh token and remove cookies."""
        validate_origin(request)
        raw_token = request.COOKIES.get("refresh_token")
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass
        response = Response({"message": "Logout successful."}, status=200)
        options = {"path": "/", "samesite": "Lax"}
        response.delete_cookie("access_token", **options)
        response.delete_cookie("refresh_token", **options)
        return response


class PasswordResetView(APIView):
    """Handle password reset email requests."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Send a reset link without revealing account existence."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            send_password_reset_email(user)
        return Response(
            {"detail": "An email has been sent to reset your password."},
            status=status.HTTP_200_OK,
        )


class PasswordConfirmView(APIView):
    """Confirm password changes using an emailed reset token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def _get_valid_user(self, uidb64, token):
        """Find the user and validate the reset link."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError,
                Base64Error, User.DoesNotExist) as exc:
            raise ValidationError(
                {"detail": "Invalid or expired reset link."}
            ) from exc
        if not user.is_active or not default_token_generator.check_token(
            user, token
        ):
            raise ValidationError({"detail": "Invalid or expired reset link."})
        return user

    def post(self, request, uidb64, token):
        """Validate and save the new password."""
        user = self._get_valid_user(uidb64, token)
        serializer = PasswordConfirmSerializer(
            data=request.data, context={"user": user}
        )
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response(
            {"detail": "Your Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )