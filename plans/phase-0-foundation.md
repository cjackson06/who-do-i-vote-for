# Phase 0 — Repo Foundation & Hygiene

Goal: clean slate + working Django skeleton served by Docker, with CI and
conventional commits in place. No product features yet.

## Tasks

### Cleanup
- [x] Remove dead frontend code: mock results in `client/src/api/candidates.ts`,
      `client/src/api/auth.ts` + unrouted Login/Register pages (React)
      — also removed `client/src/api/api.ts` (only used by auth.ts) and
      `client/src/pages/BlankPage.tsx` (unrouted)
- [x] Remove broken `shared: file:../shared` dependency from `client/package.json`
      (package-lock resynced via `npm install`)
- [x] Delete `my_politician/tmp/`
- [x] Remove empty `specs/` directory
- [x] Add MIT `LICENSE` file (README already claims MIT)

### Docs
- [x] `AGENTS.md` — repo conventions: uv-only Python workflow, ruff rules,
      pytest, cz/conventional commits, layout map
- [x] `docs/architecture.md` — target architecture (see master plan) + decision log
- [x] `docs/self-hosting.md` — stub (filled in during Phases 1 & 3)

### Tooling
- [x] commitizen: `[tool.commitizen]` in pyproject, `--dev` dep added,
      commit style documented in AGENTS.md + README (+ CONTRIBUTIONS.md updated
      from black/flake8 to ruff; flake8 dev dep removed)
- [x] GitHub Actions workflows (split by stack, path-scoped triggers):
      `.github/workflows/ci-python.yml` (ruff check + format check, `ty` type
      check, pytest) and `.github/workflows/ci-client.yml` (legacy React build,
      dropped when React is deleted in Phase 3)
- [x] `.gitignore` covers `*.sqlite3` (backend/db.sqlite3 was unignored)
- [x] `.env.example` populated with planned variables

### Django scaffold — **skipped in this pass** (owner is building `backend/` themselves)
- [ ] `uv add django uvicorn dj-database-url` (keep `google-adk` for now — removed
      at Phase 3 cutover so the old backend keeps running until replaced)
- [ ] Layout: `config/` (settings, urls, asgi) + `apps/core`
- [ ] Settings via env: `DATABASE_URL` (SQLite default, Postgres for hosted),
      `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`
- [ ] ASGI entrypoint; run under uvicorn (SSE depends on it later)
- [ ] Healthcheck endpoint `/healthz` (DB ping, version)
- [ ] Dockerfile (multi-stage, uv-based, non-root) + docker-compose: `web` + `db`
      (postgres 16) with healthchecks

## Exit criteria
- [ ] `docker compose up` serves `/healthz` from Django + Postgres *(blocked on
      Django scaffold)*
- [x] CI checks pass locally: `ruff check`, `ruff format --check`, `ty check`,
      `pytest`, client `vite build` *(GitHub Actions run pending first push)*
- [x] `cz` available; commit style documented
- [x] Dead code removed; `AGENTS.md` + `docs/architecture.md` exist
