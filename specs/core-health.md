# Core health spec (`/healthz`)

> Source of truth for the operational healthcheck endpoint served by
> `backend/apps/core`. Code implements this spec; tests verify it.

## Purpose

Single liveness/readiness probe for the Django monolith. Used by Docker
Compose healthchecks, monitoring, and humans wondering "is it up".

## Interfaces

- Route: `GET /healthz` (any other method → Django's default 405).
- View: `apps.core.views.healthz` — synchronous on purpose; under ASGI Django
  runs sync views in a threadpool, which is fine for a probe.
- Version source: `APP_VERSION` env var (set by the Docker build from
  `GIT_SHA`); falls back to `"dev"` when unset.

## Rules

- **CORE-HEALTH-1 (MUST)** — the endpoint MUST NOT require authentication,
  CSRF, or any DB writes; it is read-only and safe to expose.
- **CORE-HEALTH-2 (MUST)** — a successful response MUST be
  `200 OK` with JSON `{"status": "ok", "version": <str>, "database": "ok"}`.
- **CORE-HEALTH-3 (MUST)** — the view MUST ping the database
  (`django.db.connection.ensure_connection()`) on every request; a successful
  ping MUST be reported as `"database": "ok"`.
- **CORE-HEALTH-4 (MUST)** — on `OperationalError` from the DB ping, the view
  MUST return `503 Service Unavailable` with JSON
  `{"status": "error", "database": "unavailable"}` — never raise.
- **CORE-HEALTH-5 (SHOULD)** — the view MUST NOT depend on any other app; it
  stays usable in minimal deployments.

## Errors

| Case | Status | Body |
|---|---|---|
| DB reachable | 200 | `{"status": "ok", "version": ..., "database": "ok"}` |
| `OperationalError` on ping | 503 | `{"status": "error", "database": "unavailable"}` |

## Non-goals

- Dependency checks for LLM/search providers (added later with those apps).
- Deep readiness (migration state, cache warm-up) — this is liveness + DB only.
