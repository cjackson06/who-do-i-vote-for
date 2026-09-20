"""Operational endpoints. Behavior contract: specs/core-health.md."""

import os

from django.db import OperationalError, connection
from django.http import HttpRequest, JsonResponse


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness + DB ping probe (CORE-HEALTH-1..5)."""

    try:
        connection.ensure_connection()
    except OperationalError:
        # CORE-HEALTH-4: probe must fail with 503, never raise.
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    # CORE-HEALTH-2: 200 with version sourced from APP_VERSION (or "dev").
    return JsonResponse(
        {
            "status": "ok",
            "version": os.environ.get("APP_VERSION", "dev"),
            "database": "ok",
        }
    )
