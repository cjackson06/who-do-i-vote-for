"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

LoopCaptureMiddleware records the server's event loop on the first scope so
`apps.core.tasks.InProcessBackend` can spawn `django.tasks` work on it
(specs/core-tasks.md, TASKBACKEND-7).

Under DEBUG the application is wrapped in Django's ASGIStaticFilesHandler:
bare uvicorn (unlike `manage.py runserver`) does not serve static files, so
without this the admin renders unstyled in development. Production serves
static via collectstatic/CDN — Phase 3 wires that up.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from apps.core.eventloop import LoopCaptureMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_asgi_application()

# get_asgi_application() runs django.setup(); settings are safe to import now.
from django.conf import settings  # noqa: E402

if settings.DEBUG:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

    application = ASGIStaticFilesHandler(application)

application = LoopCaptureMiddleware(application)
