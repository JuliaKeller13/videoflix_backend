from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers


User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate registration data and create inactive users."""

    email = serializers.EmailField(max_length=150, required=True)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    confirmed_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["email", "password", "confirmed_password"]

    def validate_email(self, value):
        """Reject duplicate accounts without exposing their existence."""
        email = value.strip().lower()
        if User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exists():
            raise serializers.ValidationError(
                "Please check your registration details."
            )
        return email

    def validate(self, attrs):
        """Check password confirmation and strength."""
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"confirmed_password": "Passwords do not match."}
            )
        self._validate_password_strength(attrs)
        return attrs

    def _validate_password_strength(self, attrs):
        """Apply Django's configured password validators."""
        user = User(username=attrs["email"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"password": exc.messages}
            ) from exc

    def create(self, validated_data):
        """Create an inactive user with a hashed password."""
        validated_data.pop("confirmed_password")
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    username=validated_data["email"],
                    is_active=False,
                    **validated_data,
                )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"email": "Please check your registration details."}
            ) from exc