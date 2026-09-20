"""Tests for /healthz — contract: specs/core-health.md."""

from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import Client

pytestmark = pytest.mark.django_db


def test_healthz_ok_returns_200() -> None:
    """CORE-HEALTH-2/3: 200 with status/database/version on healthy DB."""

    response = Client().get("/healthz")

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert isinstance(data["version"], str)


def test_healthz_reports_app_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORE-HEALTH-2: version comes from APP_VERSION, defaulting to dev."""

    monkeypatch.setenv("APP_VERSION", "abc123")
    data = Client().get("/healthz").json()
    assert data["version"] == "abc123"

    monkeypatch.delenv("APP_VERSION", raising=False)
    data = Client().get("/healthz").json()
    assert data["version"] == "dev"


def test_healthz_db_failure_returns_503() -> None:
    """CORE-HEALTH-4: OperationalError -> 503 JSON, no exception raised."""

    with patch("apps.core.views.connection") as conn:
        conn.ensure_connection.side_effect = OperationalError("no db")
        response = Client().get("/healthz")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {
        "status": "error",
        "database": "unavailable",
    }
