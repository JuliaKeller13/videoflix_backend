"""Django settings optimized for automated tests."""

from .settings import *  # noqa: F401, F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]