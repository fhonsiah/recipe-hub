from .base import *  # noqa
from .base import _get_bool  # noqa

DEBUG = _get_bool("DEBUG", True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
