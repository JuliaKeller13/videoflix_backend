from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.api.serializers import RegistrationSerializer
from auth_app.utils import send_activation_email


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
