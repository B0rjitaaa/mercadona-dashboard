"""Production settings: the stack served by gunicorn behind nginx on the LAN."""

import os

from .base import *  # noqa: F403
from .base import MIDDLEWARE

DEBUG = False

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# nginx serves the SPA and /media; Django only answers /api, /admin and /static.
MIDDLEWARE = [
    MIDDLEWARE[0],
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[2:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Same-origin through nginx; trusted origins let the admin login work over plain HTTP.
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")  # noqa: F405
USE_X_FORWARDED_HOST = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
