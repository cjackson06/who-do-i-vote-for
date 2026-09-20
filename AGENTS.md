# AGENTS.md

Guidance for AI agents and humans working in this repository.

## Project

"Who Do I Vote For" — compares political candidates against a user's beliefs and
recommends whom to vote for. The repo is **mid-modernization**: the legacy
Google-ADK backend (`my_politician/`, `political_profiler/` YAML agents served by
`adk api_server`) and the React client (`client/`) are being replaced by a
Django + HTMX application. Read `plans/modernization.md` first; phase details
and trackers live in `plans/phase-*.md`.

## Hard rules

- **Python 3.13, managed exclusively with uv.** Never use bare `python`,
  `python3`, or `pip`.
  - Run anything: `uv run <cmd>` (e.g. `uv run pytest`, `uv run python script.py`)
  - Add dependencies: `uv add <pkg>` / `uv add --dev <pkg>`
- **Formatting/linting: ruff only** (see `[tool.ruff.lint]` in `pyproject.toml`).
  - `uv run ruff check .` and `uv run ruff format .` — CI enforces both
    (`ruff check`, `ruff format --check`).
- **Type check:** `uv run ty check .`
- **Tests:** `uv run pytest` — no suite yet; tests land with Phase 1
  (pytest exits with code 5 when zero tests are collected, so it's not in
  pre-flight/CI until then)
- **Commits: Conventional Commits** (commitizen is configured). Prefer
  `uv run cz commit`; otherwise format messages as `type(scope): subject` with
  types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.

## Pre-flight (run before finishing any task)

```bash
just preflight
# or, equivalently (raw commands stay canonical — CI runs these):
uv run ruff check . && uv run ruff format --check . && uv run ty check .
# add `&& uv run pytest` once the Phase 1 test suite exists
```

`justfile` wraps other common commands too (`just test`, `just manage <cmd>`,
`just server`, …) — `just --list` for the index.

## Layout

```
client/               Legacy React frontend (deleted at Phase 3 cutover)
my_politician/        Legacy ADK agent configs (deleted at Phase 3 cutover)
political_profiler/   Legacy ADK agent configs (deleted at Phase 3 cutover)
backend/              Django project (in progress)
docs/                 Human-facing narrative docs (architecture, self-hosting)
specs/                Declarative agent-facing contracts — see specs/README.md
plans/                Modernization master plan + per-phase trackers
tests/                Python tests
```

- **docs vs specs:** `docs/` explains the system for humans; `specs/`
  prescribes behavior for agents (interfaces + numbered MUST/SHOULD rules).
  New component behavior → write the spec first, then code, then tests that
  cite the spec's rule IDs.

## Environment

- `.env` holds secrets and is git-ignored; `.env.example` documents the
  expected variables. Never commit real keys.
