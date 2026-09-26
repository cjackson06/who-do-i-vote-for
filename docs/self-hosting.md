# Self-hosting

> Run "Who Do I Vote For" on your own machine with your own models.
> The deployment contract is Docker Compose (`web` + `db`). The frontend
> quickstart arrives with Phase 3 (see `plans/phase-3-v1-cutover.md`); this
> page covers the backend stack and model configuration today.

## Quickstart (backend stack)

```bash
cp .env.example .env   # add at least a SECRET_KEY
docker compose up --build
curl http://localhost:8000/healthz
```

- `db`: PostgreSQL 16 with a healthcheck and a named volume (`pgdata`).
- `web`: Django on ASGI (uvicorn); migrations are applied on boot; the image
  runs `manage.py check` before serving.
- Defaults (`wdvf`/`wdvf` database credentials, `ALLOWED_HOSTS=localhost`) are
  for a local trial only — set real values for anything exposed.
- Database: `DATABASE_URL` selects Postgres (compose) or
  `sqlite:///backend/db.sqlite3` (single-container dev).

> **`.env` and `$`:** Compose interpolates `$` inside `.env` values. If a
> secret contains a dollar sign, escape it as `$$` or keep it out of `.env`.

## Model configuration (`apps/llm`, Phase 1)

Every LLM call in the system goes through one of six **roles**:

`profiler` · `researcher` · `summarizer` · `matcher` · `recommender` · `judge`

Any OpenAI-compatible endpoint can serve any role, configured entirely via
environment variables (never exposed to end users):

| Variable | Purpose |
|---|---|
| `LLM_<ROLE>_BASE_URL` | OpenAI-compatible base URL (usually ends in `/v1`) |
| `LLM_<ROLE>_API_KEY` | API key; unset means the placeholder `EMPTY` (keyless servers) |
| `LLM_<ROLE>_MODEL` | model name as the endpoint knows it |
| `LLM_<ROLE>_TEMPERATURE` | optional; unset uses the endpoint default |

`<ROLE>` is uppercase (e.g. `LLM_RESEARCHER_MODEL`). **Global fallbacks**
`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_TEMPERATURE` fill any gap
— point everything at one server with three variables, then override roles
individually when needed (e.g. a bigger model for `researcher`).

Behavior (contract: [`specs/llm.md`](../specs/llm.md)):

- With no config for a role, production fails fast at startup
  (`manage.py check` reports error `llm.E001`); development warns, and calls
  to unconfigured roles raise `RoleNotConfigured`.
- Structured outputs are requested as JSON (native `json_schema` when the
  endpoint supports it, JSON-mode fallback otherwise) and validated against
  Pydantic schemas; malformed answers are re-asked with the error, max 3
  attempts.
- Every call is logged to the `ModelCall` table (role, model, endpoint,
  tokens, latency, status) — API keys are never stored or logged.

### Provider examples

| Provider | `BASE_URL` | Notes |
|---|---|---|
| Ollama | `http://localhost:11434/v1` (from compose: `http://host.docker.internal:11434/v1`) | no API key needed |
| vLLM | `http://your-vllm-host:8000/v1` | `--served-model-name` is your `MODEL` |
| LiteLLM proxy | `http://your-litellm:4000/v1` | set `LLM_API_KEY` to the proxy key |
| OpenRouter | `https://openrouter.ai/api/v1` | e.g. `MODEL=anthropic/claude-sonnet-4` |
| Gemini (OpenAI-compat) | `https://generativelanguage.googleapis.com/v1beta/openai/` | Google API key as `LLM_API_KEY` |

**Anthropic note:** the native Anthropic API is not OpenAI-compatible. Route
Claude models through a compatible proxy (LiteLLM, OpenRouter, or Ollama).

## Search (Phase 2)

A Tavily API key (`TAVILY_API_KEY`) is required for live research;
the FEC donations source is keyless.
