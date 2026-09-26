"""Production settings: fail fast on bad config, harden everything."""

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import settings

if not settings.SECRET_KEY or settings.SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a real value in production "
        "(set SECRET_KEY in the environment or .env)."
    )
if not settings.ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be set in production (comma-separated domains)."
    )

DEBUG = False

ALLOWED_HOSTS = settings.ALLOWED_HOSTS

DATABASES = {
    "default": dj_database_url.parse(settings.DATABASE_URL, conn_max_age=600),
}

# SETTINGS-4: sole env-toggleable hardening flag (local compose / TLS proxy)
SECURE_SSL_REDIRECT = settings.SECURE_SSL_REDIRECT


SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in settings.ALLOWED_HOSTS]
X_FRAME_OPTIONS = "DENY"

# MAILERS: console backend inherited from base for now; real SMTP arrives
# with Phase 4 (accounts/email).
