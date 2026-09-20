# Phase 0 — Repo Foundation & Hygiene

Goal: clean slate + working Django skeleton served by Docker, with CI and
conventional commits in place. No product features yet.

## Tasks

### Cleanup
- [ ] Remove dead frontend code: mock results in `client/src/api/candidates.ts`,
      `client/src/api/auth.ts` + unrouted Login/Register pages (React)
- [ ] Remove broken `shared: file:../shared` dependency from `client/package.json`
- [ ] Delete `my_politician/tmp/`
- [ ] Remove or repurpose empty `specs/` directory
- [ ] Add MIT `LICENSE` file (README already claims MIT)

### Docs
- [ ] `AGENTS.md` — repo conventions: uv-only Python workflow, ruff rules,
      pytest, cz/conventional commits, layout map
- [ ] `docs/architecture.md` — target architecture (see master plan) + decision log
- [ ] `docs/self-hosting.md` — stub (filled in during Phases 1 & 3)

### Tooling
- [ ] commitizen: `[tool.commitizen]` in pyproject; commit style documented in
      AGENTS.md + README
- [ ] GitHub Actions workflow: ruff check + format check, `ty` type check,
      pytest, client build check (dropped when React is deleted in Phase 3)

### Django scaffold
- [ ] `uv add django uvicorn dj-database-url` (keep `google-adk` for now — removed
      at Phase 3 cutover so the old backend keeps running until replaced)
- [ ] Layout: `config/` (settings, urls, asgi) + `apps/core`
- [ ] Settings via env: `DATABASE_URL` (SQLite default, Postgres for hosted),
      `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`
- [ ] ASGI entrypoint; run under uvicorn (SSE depends on it later)
- [ ] Healthcheck endpoint `/healthz` (DB ping, version)
- [ ] Dockerfile (multi-stage, uv-based, non-root) + docker-compose: `web` + `db`
      (postgres 16) with healthchecks
- [ ] `.env.example` updated with all Phase 0 vars

## Exit criteria
- [ ] `docker compose up` serves `/healthz` from Django + Postgres
- [ ] CI green on PR (ruff, ty, pytest)
- [ ] `cz` available; commit style documented
- [ ] Dead code removed; `AGENTS.md` + `docs/architecture.md` exist
