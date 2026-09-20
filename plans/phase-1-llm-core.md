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
- [ ] `specs/llm.md` contract written first (rule IDs: `LLM-CONFIG-*`,
      `LLM-CLIENT-*`, `LLM-STREAM-*`, `LLM-CALL-*`, `LLM-CHECK-*`,
      `LLM-PROMPT-*` — see `specs/README.md`)
- [ ] `apps/llm` app: role config schema + validation at startup (fail fast on
      missing role config)
- [ ] `LLMClient` wrapper: `complete(role, messages, schema=None, ...)` returning
      a parsed Pydantic object
- [ ] Retry/validation loop: malformed JSON → re-ask with error context
      (max N attempts), typed exceptions
- [ ] Prompt template conventions: versioned, testable modules (no f-string soup)
- [ ] `ModelCall` model + logging for success and failure
- [ ] Minimal streaming primitive (`stream(role, messages)`) for future SSE needs
- [ ] Tests: mocked transports (no live keys in CI), malformed-response retry,
      role-config validation
- [ ] Docs: `docs/self-hosting.md` model configuration section

## Exit criteria
- [ ] Any OpenAI-compatible endpoint can serve any role via env vars only
- [ ] Unit tests green with zero network access
- [ ] `ModelCall` rows written for every call
