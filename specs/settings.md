# Settings / environment spec

> Source of truth for deployment configuration: how env vars reach Django
> settings, how settings modules are selected, and what fails fast. Code
> implements this spec; tests verify it.

## Purpose

One typed, validated configuration path for hosted and self-hosted runs.
Prevents drift between "what's documented", "what's read", and "what fails
loudly in prod".

## Interfaces

Settings modules (selected via `DJANGO_SETTINGS_MODULE`; every entrypoint
**defaults to `config.settings.local`** — production is selected explicitly
via env by deployers; the Phase 0–2 image runs local, and the Phase 3 hosted
deploy pins prod):

- `config.settings.base` — shared config + the typed `Settings` class below
- `config.settings.local` — `DEBUG=True`, localhost hosts, console email
- `config.settings.prod` — fail-fast validation + security hardening

`Settings` (pydantic-settings): field name == env var name. Resolution order:
**process env > repo-root `.env`** (loaded without overriding existing env
vars, so `apps/*` can also read the same values via `os.getenv`).

| Env var | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `django-insecure-dev-only-fallback` | real value required in prod (see SETTINGS-4) |
| `ALLOWED_HOSTS` | — | comma-separated CSV (never JSON); localhost defaults in local |
| `DATABASE_URL` | `sqlite://backend/db.sqlite3` | `postgres://…` for hosted/self-host compose |
| `SECURE_SSL_REDIRECT` | `true` | set `false` only for local compose / non-TLS deployments behind a trusted proxy |
| `TAVILY_API_KEY` | unset | research sources (Phase 2): when unset, the Tavily adapter is skipped with a `research.W001` check warning |
| `FEC_API_KEY` | unset | openFEC key; when unset the FEC adapter is skipped (`research.W002`). `DEMO_KEY` only via explicit `FEC_DEMO=1` |
| `TAVILY_BASE_URL` / `FEC_BASE_URL` | vendor defaults | endpoint overrides for self-hosted proxies/tests |
| `FEC_DEMO` | unset | set `1` to explicitly opt into the rate-limited `DEMO_KEY` mode |

`APP_VERSION` is read directly (not typed `Settings`) by `/healthz` — see
`specs/core-health.md`.

## Rules

- **SETTINGS-1 (MUST)** — every deployment value MUST flow through the typed
  `Settings` class (or `os.getenv` for the open-ended `LLM_*` family); no
  scattered `os.environ` reads for these vars elsewhere.
- **SETTINGS-6 (MUST)** — research-source keys (`TAVILY_API_KEY`,
  `FEC_API_KEY`) and their base-URL overrides flow through the typed
  `Settings` class as nullable fields; missing keys mean the corresponding
  adapter is disabled (see `specs/research.md`), never a crash.
- **SETTINGS-2 (MUST)** — `ALLOWED_HOSTS` MUST accept CSV
  (`example.com,www.example.com`), not JSON, since it is human-authored env.
- **SETTINGS-3 (MUST)** — `config.settings.prod` MUST raise
  `ImproperlyConfigured` at import when `SECRET_KEY` is empty or starts with
  `django-insecure-`, or when `ALLOWED_HOSTS` is empty. There is no
  "prod-lite" fallback.
- **SETTINGS-4 (MUST)** — prod security hardening MUST NOT be silently
  disableable except `SECURE_SSL_REDIRECT` (env-driven; e.g. behind a TLS
  proxy that already terminates HTTPS locally). HSTS, secure cookies,
  `X_FRAME_OPTIONS=DENY`, proxy SSL header stay on.
- **SETTINGS-5 (MUST)** — the entrypoints (`manage.py`, `asgi.py`) and the
  image MUST NOT default to `config.settings.prod`; prod selection happens
  only via explicit env (`DJANGO_SETTINGS_MODULE`), set by the deployer.

## Errors

| Case | Raised where | Behavior |
|---|---|---|
| prod + weak/missing `SECRET_KEY` | `settings/prod.py` import | `ImproperlyConfigured`, process exits |
| prod + empty `ALLOWED_HOSTS` | `settings/prod.py` import | `ImproperlyConfigured`, process exits |

## Non-goals

- Runtime reload of settings; multi-tenant config; secrets managers (env vars
  only for now).
