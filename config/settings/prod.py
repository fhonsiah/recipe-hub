import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa
from .base import _get_bool  # noqa

DEBUG = _get_bool("DEBUG", False)

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "example.com").split(",") if h.strip()]

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "recipehub"),
        "USER": os.environ.get("DB_USER", "recipehub"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# A local `.env` is loaded by base.py and fills in anything not already in the
# environment. That is convenient in development but dangerous here: shipping a
# development `.env` to a production host would silently enable DEBUG and point
# the app at SQLite. Fail loudly instead.
if DEBUG:
    raise ImproperlyConfigured(
        "DEBUG is enabled while running config.settings.prod. Set DEBUG=False in the environment."
    )
if SECRET_KEY.startswith("django-insecure-") or SECRET_KEY == "change-me-in-production":
    raise ImproperlyConfigured(
        "SECRET_KEY is still the placeholder value. Set a real SECRET_KEY environment variable."
    )
if ALLOWED_HOSTS == ["example.com"]:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is still the placeholder value. Set ALLOWED_HOSTS to your real hostnames."
    )
if DATABASES["default"]["NAME"].endswith(".sqlite3"):
    raise ImproperlyConfigured(
        "DB_NAME points at a SQLite file while running config.settings.prod. "
        "Set DB_NAME to your PostgreSQL database name."
    )

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = _get_bool("SECURE_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

WHITENOISE_MAX_AGE = 31536000
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
