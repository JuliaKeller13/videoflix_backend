from rest_framework import serializers


class RegistrationSerializer(serializers.Serializer):
    """Validate incoming registration data."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirmed_password = serializers.CharField(write_only=True)