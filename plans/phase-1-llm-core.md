# Phase 1 — LLM Core (`apps/llm`)

Goal: a model-agnostic LLM layer with role-based config and structured outputs.
Everything later (research swarm, analysis pipeline, evals) calls through this.

## Design

- Raw OpenAI-compatible async client (`openai` SDK, `AsyncOpenAI`)
- Roles: `profiler`, `researcher`, `summarizer`, `matcher`, `recommender`, `judge`
- Each role config: `{base_url, api_key, model, temperature}` from env/settings —
  e.g. `LLM_RESEARCHER_BASE_URL`, `LLM_RESEARCHER_API_KEY`, `LLM_RESEARCHER_MODEL`
- Hosted: env-only, never exposed to users. Self-hosted: point at Ollama /
  vLLM / LiteLLM proxy / Gemini OpenAI-compat endpoint / OpenRouter
- Structured outputs: Pydantic schemas; use `response_format: json_schema` when
  the endpoint supports it, else JSON-mode fallback + validate + bounded retry
- `ModelCall` log: role, model, prompt/completion tokens, latency, cost-if-known,
  FK to job/run — feeds evals + future billing analytics

## Tasks
- [x] `specs/llm.md` contract written first (rule IDs: `LLM-CONFIG-*`,
      `LLM-CLIENT-*`, `LLM-STREAM-*`, `LLM-CALL-*`, `LLM-CHECK-*`,
      `LLM-PROMPT-*` — see `specs/README.md`)
- [x] `apps/llm` app: role config schema + validation at startup (fail fast on
      missing role config) — env resolution `LLM_<ROLE>_*` → global `LLM_*` →
      `RoleNotConfigured`; system check `llm.E001` (ERROR when DEBUG=False,
      WARNING under DEBUG)
- [x] `LLMClient` wrapper: `complete(role, messages, schema=None, ...)` returning
      a parsed Pydantic object
- [x] Retry/validation loop: malformed JSON → re-ask with error context
      (max N attempts), typed exceptions (`StructuredOutputError`,
      `RoleNotConfigured`; SDK errors propagate after logging)
- [x] Prompt template conventions: versioned, testable modules (no f-string soup)
      — `apps/llm/prompts/` (`NAME`/`VERSION`/pure `build_messages`)
- [x] `ModelCall` model + logging for success and failure — one row per
      invocation; job/run FK deferred to Phase 3 (decision logged)
- [x] Minimal streaming primitive (`stream(role, messages)`) for future SSE needs
- [x] Tests: mocked transports (no live keys in CI), malformed-response retry,
      role-config validation — 22 tests via `httpx2.MockTransport`, zero network
- [x] Docs: `docs/self-hosting.md` model configuration section

## Exit criteria
- [x] Any OpenAI-compatible endpoint can serve any role via env vars only
- [x] Unit tests green with zero network access
- [x] `ModelCall` rows written for every call
