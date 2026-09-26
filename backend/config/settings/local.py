"""Development settings: DEBUG on, localhost hosts, console email (from base)."""

import dj_database_url

from .base import *
from .base import settings

DEBUG = True

ALLOWED_HOSTS = settings.ALLOWED_HOSTS or ["localhost", "127.0.0.1"]

DATABASES = {
    "default": dj_database_url.parse(settings.DATABASE_URL, conn_max_age=600),
}

# Server runs enqueue-and-return (specs/core-tasks.md, TASKBACKEND-1);
# scripts/shell against these settings must capture the loop first.
TASKS = {
    "default": {
        "BACKEND": "apps.core.tasks.InProcessBackend",
    },
}
