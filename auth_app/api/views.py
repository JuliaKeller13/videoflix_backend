from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.api.serializers import RegistrationSerializer
from auth_app.utils import send_activation_email


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
        """Authenticate credentials and issue JWT cookies."""
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