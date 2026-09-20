# Self-hosting

> Stub — filled in during Phase 1 (model configuration) and Phase 3 (full
> quickstart). See `plans/phase-1-llm-core.md` and `plans/phase-3-v1-cutover.md`.

## Planned shape

- **Deploy**: Docker Compose (`web` + `db`). Postgres for hosted; SQLite works
  for single-container self-hosting.
- **Models**: any OpenAI-compatible endpoint per role — Ollama, vLLM, LiteLLM
  proxy, Gemini's OpenAI-compat endpoint, OpenRouter, etc. Configured entirely
  via environment variables (`LLM_<ROLE>_BASE_URL`, `LLM_<ROLE>_API_KEY`,
  `LLM_<ROLE>_MODEL`).
- **Search**: a Tavily API key is required for live research
  (`TAVILY_API_KEY`); the FEC donations source is keyless.
- **Anthropic note**: the native Anthropic API is not OpenAI-compatible — route
  Claude models through a compatible proxy (LiteLLM, OpenRouter).
