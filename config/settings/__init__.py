"""
Default settings module points to the development settings.

For production, set the environment variable:
    DJANGO_SETTINGS_MODULE=config.settings.prod
"""
from .dev import *  # noqa
