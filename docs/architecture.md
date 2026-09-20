# Architecture

> Target architecture for the modernized app. Phase-by-phase implementation
> detail and trackers: see [`plans/modernization.md`](../plans/modernization.md)
> and `plans/phase-*.md`.

## Current state (transitional)

- Legacy backend: Google ADK YAML agents (`my_politician/`, `political_profiler/`)
  served by the stock `adk api_server` — no application code, in-memory
  sessions, CORS `*`.
- Legacy frontend: React/Vite (`client/`) speaking the raw ADK protocol.
- Both are deleted at the Phase 3 cutover.

## Target

A single **Django monolith on ASGI (uvicorn)** — HTMX templates for the UI,
plain Python async functions as "agents" calling LLMs directly. No agent
framework, no DRF.

```
┌──────────────────────── Django monolith (ASGI/uvicorn) ────────────────────────┐
│                                                                                 │
│  HTMX templates ──── views (HTML fragments) ──── SSE endpoints                  │
│        │                                     │                                  │
│  apps/accounts   anonymous sessions, claim flow, plan-tier stub                 │
│  apps/profiler   questionnaire/conversational onboarding                        │
│  apps/analysis   AnalysisJob ──► pipeline runner (background asyncio task)      │
│        │            steps persisted: research → match → recommend               │
│  apps/research   swarm orchestrator ──► SourceAdapter interface                 │
│        │                                 ├─ TavilyAdapter (web/news)            │
│        │                                 └─ FECAdapter (donations)              │
│  apps/politicians  Politician + cached profiles/facts/citations (TTL refresh)   │
│  apps/llm          OpenAI-compat client, ROLE→model config, structured output,  │
│        │            ModelCall log (tokens/cost/latency — feeds evals & billing) │
│  apps/evals        golden tasks, LLM judge, EvalRun/EvalResult, staff dashboard │
│  apps/core         SSE helpers, settings (base/hosted/self-host via env)        │
└─────────────────────────────────────────────────────────────────────────────────┘
   DB: Postgres (hosted) / SQLite (self-host default)   Search key: TAVILY_API_KEY
```

## Decision log

| Area | Decision |
|---|---|
| Backend | Python 3.13 + Django 6 (ASGI), uv-managed |
| Frontend | HTMX-first Django templates + Tailwind; small TS islands. React retired at Phase 3 |
| Models | Raw OpenAI-compatible client; per-role `{base_url, api_key, model}` server config. Hosted: env-only, never user-facing |
| Search | Tavily + FEC API in v1 behind a pluggable `SourceAdapter` interface |
| Research | Parallel swarm (fan-out per candidate × source) → cited summaries → DB-cached politician profiles (TTL) |
| Pipeline UX | SSE step progress; final structured result |
| Users | Anonymous by default; optional account (session-cookie auth, claim flow). No JWT |
| Billing | Deferred; entitlement hooks designed in now |
| Evals | Golden dataset + LLM-as-judge; CLI command + staff-only dashboard |
| Onboarding | Questionnaire in v1; Tinder-style swipe in v2 |
| Tooling | commitizen + GitHub Actions CI; ruff; pytest |
| Hosting | Host-agnostic; Docker Compose is the deployment contract |

## Key design points

- **Agents are deterministic pipeline steps**, not free-form tool-calling:
  research → ideology match → recommend, each a structured-output LLM call
  (Pydantic-validated, bounded retry). Robust across weak self-hosted models;
  comparable in evals.
- **AnalysisJob is the backbone**: steps persisted to DB; SSE streams from an
  in-process pub/sub (Redis-backed later without API change); entitlement
  limits attach at job creation.
- **Politician cache is the cost lever**: `SourceRecord` rows (URL, quote,
  first-hand flag, retrieved_at, TTL) let repeat analyses skip paid search.
- **First-hand sources only**: enforced in adapters (drop aggregators/opinion)
  and in prompts (citations required); every claim links to a `SourceRecord`.
- **Role config** (`apps/llm`): `profiler`, `researcher`, `summarizer`,
  `matcher`, `recommender`, `judge` — one env var pattern, documented for
  self-hosters, never surfaced in the hosted UI.

## Risks / constraints

- Raw OpenAI-compat client: Anthropic-native API needs a proxy (LiteLLM,
  OpenRouter, Ollama) — documented in `docs/self-hosting.md`.
- SSE requires ASGI (uvicorn); sync WSGI deployments must never sneak in.
- FEC covers federal elections only; state/local data comes with the elections
  phase.
