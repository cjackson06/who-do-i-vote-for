# LLM core spec (`apps/llm`)

> Source of truth for the model-agnostic LLM layer: role-based config, the
> async OpenAI-compatible client, structured outputs, the `ModelCall` log,
> and prompt conventions. Code implements this spec; tests verify it.

## Purpose

One seam for **every** LLM call in the system (research swarm, profiler,
matcher, judge). Providers may be anything OpenAI-compatible (OpenAI, Ollama,
vLLM, LiteLLM proxy, Gemini OpenAI-compat, OpenRouter) — configured per role
via env only. Hosted deployments never expose this config to users.

## Interfaces

### Roles

`profiler`, `researcher`, `summarizer`, `matcher`, `recommender`, `judge`.
The set is closed; adding a role means changing this spec and the code.

### Role config

```python
class RoleConfig(BaseModel):
    base_url: str  # OpenAI-compatible endpoint (…/v1)
    api_key: str = "EMPTY"  # "EMPTY" placeholder for keyless endpoints (Ollama)
    model: str  # model name as the endpoint knows it
    temperature: float | None = None  # None → endpoint default
```

Env resolution (per role, `<ROLE>` uppercase: `profiler`, …):

| Env var | Falls back to | Missing → |
|---|---|---|
| `LLM_<ROLE>_BASE_URL` | `LLM_BASE_URL` | `RoleNotConfigured` |
| `LLM_<ROLE>_MODEL` | `LLM_MODEL` | `RoleNotConfigured` |
| `LLM_<ROLE>_API_KEY` | `LLM_API_KEY` | `"EMPTY"` |
| `LLM_<ROLE>_TEMPERATURE` | `LLM_TEMPERATURE` | `None` |

So self-hosters can point all roles at one server with 3 globals and override
any role individually. Values may come from process env or the repo-root
`.env` (see `specs/settings.md`). Resolution failures raise `RoleNotConfigured`
(lazy: at call time; startup check per `LLM-CHECK-1`).

### `LLMClient`

```python
class LLMClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None): ...
    async def complete(
        self,
        role: str,
        messages: list[dict],  # OpenAI-style {"role", "content"}
        *,
        schema: type[BaseModel] | None = None,
        temperature: float | None = None,  # wins over role config
        max_tokens: int | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
    ) -> str | BaseModel: ...
    async def stream(
        self,
        role: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]: ...
```

### `ModelCall` (DB log)

| Field | Type | Notes |
|---|---|---|
| `role` | CharField (choices = roles) | |
| `model` | CharField | model name from RoleConfig |
| `base_url` | CharField | endpoint; **never** the API key |
| `prompt_name` / `prompt_version` | CharField, blank | lineage for evals |
| `response_format` | CharField | `text` \| `json_mode` \| `json_schema` |
| `attempts` | PositiveSmallInt | 1 = clean first try |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | Int, null | usage if endpoint reports it |
| `latency_ms` | Int | wall time around SDK call |
| `status` | CharField | `ok` \| `error` |
| `error` | TextField, blank | truncated error context (no secrets) |
| `created_at` | DateTime | auto-now-add |

Index on `(role, created_at)`. **No FK** to `AnalysisJob`/`EvalRun` yet —
Phase 3/5 add nullable FKs by migration (decision: defer entirely, Phase 1).

## Rules

### Config

- **LLM-CONFIG-1 (MUST)** — the role set is exactly the six roles above; any
  other role name is a programming error (`ValueError` at call time).
- **LLM-CONFIG-2 (MUST)** — env resolution follows the table: role-specific
  wins over global; missing `base_url` or `model` → `RoleNotConfigured`;
  missing `api_key` defaults to `"EMPTY"`.
- **LLM-CONFIG-3 (MUST)** — `api_key` values MUST NOT be logged, stored, or
  included in any error message. `ModelCall.base_url` stores the endpoint
  only.
- **LLM-CONFIG-4 (SHOULD)** — one `AsyncOpenAI` client instance per role,
  cached in-process; a fresh `LLMClient` is cheap to build for tests.

### `complete()`

- **LLM-CLIENT-1 (MUST)** — without `schema`: returns the assistant text
  (`str`). With `schema`: returns a validated instance of that pydantic
  model — never raw JSON strings, never `dict`.
- **LLM-CLIENT-2 (MUST)** — structured output first attempts
  `response_format: json_schema` (schema JSON built from the pydantic model).
  Structured responses are always parsed **client-side** from the raw text
  (`json.loads` + `model_validate`) — NOT via the SDK's `.parse()` — so
  retries can echo the model's invalid output (LLM-CLIENT-5) and weak
  self-hosted endpoints behave uniformly.
- **LLM-CLIENT-3 (MUST)** — when the endpoint rejects `json_schema`
  (HTTP 400/404 `BadRequestError`), the client MUST transparently downgrade
  to **JSON mode** for that attempt (`response_format: {"type": "json_object"}`
  with the JSON schema injected into the system/user messages) and MUST
  record the downgrade in-process for that role so later calls skip the
  unsupported mode. The downgrade MUST NOT surface as an error.
- **LLM-CLIENT-4 (MUST)** — structured responses (both `json_schema` and
  JSON-mode) are `json.loads`-ed then `schema.model_validate`d. Malformed
  JSON, empty content, or validation failure = a malformed attempt.
- **LLM-CLIENT-5 (MUST)** — malformed attempts are retried by re-asking with
  the model's invalid output **and** the concrete parse/validation error
  appended as extra messages, max `attempts=3` (default, bounded); exhaustion
  raises `StructuredOutputError` carrying the last error and a truncated raw
  output snippet.
- **LLM-CLIENT-6 (MUST)** — transport/API errors from the SDK propagate as-is
  (openai exceptions) — after the `ModelCall` row for the call is written
  (`status=error`). The client adds no wrapping except for its own typed
  exceptions (`RoleNotConfigured`, `StructuredOutputError`).
- **LLM-CLIENT-7 (MUST)** — exactly one `ModelCall` row is written per
  `complete()`/`stream()` invocation, success **or** failure.
- **LLM-CLIENT-8 (SHOULD)** — `temperature` argument wins over role config;
  `None` means "role config, else endpoint default".
- **LLM-CLIENT-9 (MUST)** — `attempts` on `ModelCall` counts SDK
  request/response cycles actually made (1 = clean first try).

### `stream()`

- **LLM-STREAM-1 (MUST)** — yields assistant text deltas in arrival order
  (str only; no schema support in v1).
- **LLM-STREAM-2 (MUST)** — writes one `ModelCall` row when the stream ends
  (status `ok`/`error`); token usage is recorded when the endpoint supplies
  it (usage-bearing final chunk) and stays `null` otherwise — absence MUST
  NOT raise.
- **LLM-STREAM-3 (SHOULD)** — no structured-output support; callers needing
  schema + streaming arrive in Phase 3 and combine both primitives.

### `ModelCall` persistence

- **LLM-CALL-1 (MUST)** — rows are written for **every** call, success and
  failure, including `RoleNotConfigured`? — no: unconfigured roles fail
  before any SDK attempt and write **no** row (nothing was attempted).
- **LLM-CALL-2 (MUST)** — API keys never appear in any field (see
  LLM-CONFIG-3); error text is truncated (≤ 2000 chars).
- **LLM-CALL-3 (SHOULD)** — ORM writes happen via `sync_to_async` (client is
  async); tests use `django_db(transaction=True)` accordingly.

### Startup checks

- **LLM-CHECK-1 (MUST)** — a registered Django system check (id `llm.E001`)
  reports every role lacking resolvable config: severity **ERROR** when
  `DEBUG=False`, **WARNING** under `DEBUG`. Consequence: a prod entrypoint
  running `manage.py check` fails fast; dev servers still boot.
- **LLM-CHECK-2 (MUST)** — independent of the check, calling an unconfigured
  role raises `RoleNotConfigured` at call time.

### Prompt conventions

- **LLM-PROMPT-1 (MUST)** — prompt modules live in `apps/llm/prompts/`; each
  exports `NAME: str`, `VERSION: str`, and a **pure**
  `build_messages(**ctx) -> list[dict]`. No I/O, no globals mutated, no
  client calls inside.
- **LLM-PROMPT-2 (MUST)** — prompt text lives in module-level constants;
  `build_messages` only interpolates context into them (no inline f-string
  prose scattered through call sites).
- **LLM-PROMPT-3 (SHOULD)** — call sites pass the prompt module's
  `NAME`/`VERSION` as `prompt_name`/`prompt_version` so `ModelCall` rows
  carry prompt lineage for evals.

## Errors

| Exception | When raised |
|---|---|
| `LLMError` | base class; catch-all for app-level LLM errors |
| `RoleNotConfigured(LLMError)` | role has no resolvable `base_url`/`model` (config resolution or call time) |
| `StructuredOutputError(LLMError)` | malformed/invalid output persisted past the attempt budget |

Endpoint/transport errors are NOT wrapped: openai SDK exceptions propagate
(callers may catch `openai.APIStatusError` etc. directly).

## Non-goals

- No tool/function calling, no free-form agent loops (deterministic pipeline
  by design — see `docs/architecture.md`).
- No Anthropic-native API (route through an OpenAI-compatible proxy).
- No cost computation or rate tables (tokens recorded; billing later).
- No response caching (politician-profile cache lives in `apps/politicians`,
  Phase 2).
