"""Development settings: DEBUG on, localhost hosts, console email (from base)."""

import dj_database_url

from .base import *
from .base import settings

DEBUG = True

ALLOWED_HOSTS = settings.ALLOWED_HOSTS or ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        **dj_database_url.parse(settings.DATABASE_URL, conn_max_age=600),
        # Tests run ORM work from the event loop AND the asgiref executor
        # thread; pytest-django's default shared-cache in-memory sqlite
        # fails cross-connection writes instantly ("database table is
        # locked"). A file-backed test DB behaves like real self-hosted
        # sqlite (busy-timeout waits instead of instant lock errors).
        "TEST": {"NAME": str(BASE_DIR / "test-db.sqlite3")},
    },
}

# Server runs enqueue-and-return (specs/core-tasks.md, TASKBACKEND-1);
# scripts/shell against these settings must capture the loop first.
TASKS = {
    "default": {
        "BACKEND": "apps.core.tasks.InProcessBackend",
    },
}
