"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

LoopCaptureMiddleware records the server's event loop on the first scope so
`apps.core.tasks.InProcessBackend` can spawn `django.tasks` work on it
(specs/core-tasks.md, TASKBACKEND-7).

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from apps.core.eventloop import LoopCaptureMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = LoopCaptureMiddleware(get_asgi_application())
