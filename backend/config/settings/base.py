"""
Django settings shared by every environment.

Environment *differences* (DEBUG, ALLOWED_HOSTS, DATABASES, security
hardening) live in `local.py` / `prod.py`. Deployment-specific *values*
come from the environment or the repo-root `.env` via the typed Settings
class below (pydantic-settings).

Settings selection: every entrypoint defaults to `config.settings.local`
(safe default); production is pinned by the Docker image via
`ENV DJANGO_SETTINGS_MODULE=config.settings.prod` — never by a default.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# config/settings/base.py → parents[2] = backend/
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed, validated deployment configuration.

    Field names are the env var names (SECRET_KEY, ALLOWED_HOSTS,
    DATABASE_URL). Process env wins over the repo-root `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SECRET_KEY: str = Field(default="django-insecure-dev-only-fallback")
    # NoDecode: env values arrive as raw strings (CSV) — JSON decoding disabled
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = []
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept ALLOWED_HOSTS=a.com,b.com instead of JSON."""
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value


settings = Settings()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = settings.SECRET_KEY

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"

# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = "static/"

# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
