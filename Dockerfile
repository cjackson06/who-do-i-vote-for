# syntax=docker/dockerfile:1

# --- Builder: resolve locked dependencies with uv -------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# --- Runtime ---------------------------------------------------------------
FROM python:3.13-slim

# SETTINGS-5: the image never defaults to prod. During the build phases the
# stack runs config.settings.local (entrypoint defaults); hosted/prod deploys
# set DJANGO_SETTINGS_MODULE=config.settings.prod explicitly (Phase 3 pins it).
# manage.py is invoked from /app so backend/ lands on sys.path via
# script-dir + PYTHONPATH (belt and braces).
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY backend/ backend/

# /healthz reports this (specs/core-health.md); CI/compose inject the SHA
ARG GIT_SHA=dev
ENV APP_VERSION=${GIT_SHA}

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
# Entrypoint: apply schema, run system checks (fail-fast gate for app config),
# then serve ASGI — never a WSGI server (SSE later depends on this).
CMD ["sh", "-c", "python backend/manage.py migrate --noinput && python backend/manage.py check && exec python -m uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]
