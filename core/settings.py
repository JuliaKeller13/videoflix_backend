import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    default="django-insecure-@#x5h3zj!g+8g1v@2^b6^9$8&f1r7g$@t3v!p4#=g0r5qzj4m3",
)

DEBUG = True

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1"
).split(",")

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    default="http://127.0.0.1:5500",
).split(",")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_rq",
    "auth_app",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", default="videoflix_db"),
        "USER": os.environ.get("DB_USER", default="videoflix_user"),
        "PASSWORD": os.environ.get(
            "DB_PASSWORD", default="supersecretpassword"
        ),
        "HOST": os.environ.get("DB_HOST", default="db"),
        "PORT": os.environ.get("DB_PORT", default=5432),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get(
            "REDIS_LOCATION", default="redis://redis:6379/1"
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "videoflix",
    }
}

RQ_QUEUES = {
    "default": {
        "HOST": os.environ.get("REDIS_HOST", default="redis"),
        "PORT": os.environ.get("REDIS_PORT", default=6379),
        "DB": os.environ.get("REDIS_DB", default=0),
        "DEFAULT_TIMEOUT": 900,
        "REDIS_CLIENT_KWARGS": {},
    },
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


FRONTEND_ACTIVATION_URL = os.environ["FRONTEND_ACTIVATION_URL"]

frontend_url = urlsplit(FRONTEND_ACTIVATION_URL)

CORS_ALLOWED_ORIGINS = [
    f"{frontend_url.scheme}://{frontend_url.netloc}",
]

CORS_ALLOW_CREDENTIALS = True

CORS_URLS_REGEX = r"^/api/"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "auth_app.api.authentication.CookieJWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
}


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 2525))

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "no-reply@videoflix.test",
)