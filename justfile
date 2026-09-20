# Common dev commands — run `just --list` for the index.
# Quality recipes mirror AGENTS.md pre-flight and .github/workflows/ci-python.yml (CI stays raw).

# List available recipes
default:
    @just --list

# Install/sync Python dependencies
install:
    uv sync --all-groups

# Lint (ruff check)
lint:
    uv run ruff check .

# Lint with autofix
format:
    uv run ruff check --fix .

# Type check (ty)
types:
    uv run ty check .

# AGENTS.md pre-flight: ruff check + ruff format --check + ty + pytest
preflight: lint format types test

# Run tests; extra args pass through, e.g. `just test tests/test_foo.py -k bar`
test *ARGS:
    uv run pytest {{ARGS}}

# Any Django management command, e.g. `just manage showmigrations`
manage *ARGS:
    uv run backend/manage.py {{ARGS}}

# Django dev server (config.settings.local)
server:
    uv run backend/manage.py runserver

# Apply migrations
migrate:
    uv run backend/manage.py migrate

# Make migrations, e.g. `just makemigrations core`
makemigrations *ARGS:
    uv run backend/manage.py makemigrations {{ARGS}}
