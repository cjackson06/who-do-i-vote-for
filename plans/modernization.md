# Modernization Plan — Who Do I Vote For

> Status: approved 2026-09-20 · Per-phase trackers live in this directory ·
> Original brainstorm notes preserved verbatim in the Appendix.

## Why

The repo was originally built for a Google agentic AI challenge. The "backend" is
stock `adk api_server` serving YAML agent configs — there is no application code:
no custom endpoints, no auth, in-memory sessions, CORS `*`. The React frontend
speaks the raw ADK protocol (`POST /run`, hand-parsed event JSON) and papers over
its quirks (re-POST on `functionCall`, string-matching `"complete"`, hardcoded
mock results).

Goals of this modernization:

1. A real, extensible backend that calls models directly (no agent framework).
2. One codebase that runs **hosted** (we operate, freemium) and **self-hosted**
   (open source, anyone's models).
3. A model **evaluation harness** for summarization + information-finding so we
   can pick/configure models per role with evidence.

## Decision log (locked)

| Area | Decision |
|---|---|
| Backend | **Python 3.13 + Django 6 (ASGI)**, uv-managed — replaces ADK `api_server` entirely |
| Frontend | **HTMX-first Django templates + Tailwind**, small TypeScript islands (charts, later swipe). React app retired at Phase 3 cutover |
| Models | **Raw OpenAI-compatible client**, role-based server config (`base_url` + `api_key` + `model` per role). Hosted: env-only, never exposed to users. Self-hosted: point at Ollama/vLLM/LiteLLM proxy/Gemini OpenAI-compat/OpenRouter |
| Search | **Tavily** (web+news) + **FEC API** (donations) in v1, behind a pluggable source-adapter interface (YouTube, voting history, social later) |
| Research | **Parallel agent swarm**: fan-out per candidate × per source → summarize w/ citations → **politician profiles cached in DB** to cut search costs |
| Pipeline UX | **SSE step progress** (HTMX SSE extension), final structured result |
| Users | **Anonymous by default + optional account** to save profile/results (claim-anonymous-session flow). Session-cookie auth, no JWT |
| Billing | **Deferred** — entitlement hooks designed in now (plan tier field, limits interface) |
| Evals | **Golden dataset + LLM-as-judge**, CLI management command **plus staff-only dashboard** (trigger runs, SSE progress, leaderboard, judge rationales) |
| Onboarding | Conversational questionnaire first (v1), **Tinder-style swipe next** (v2) |
| Dev tooling | **commitizen (cz) + GitHub Actions CI**, ruff, pytest |
| Hosting | Host-agnostic; **Docker Compose is the deployment contract**; pick host later |

## Target architecture

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

## Key design points

- **No ADK, no DRF.** HTML fragments for HTMX; a handful of JSON/SSE endpoints.
  Agents = plain Python async functions calling the LLM client with
  structured-output schemas (Pydantic-validated, retry-on-malformed).
  Deterministic pipeline, not free-form tool-calling — more robust across weak
  self-hosted models and makes evals comparable.
- **AnalysisJob is the backbone**: created per analysis, steps written to DB, SSE
  streams from an in-process pub/sub (single container now; Redis-backed later
  without changing the API). Job records give free-tier limits somewhere to
  attach and make failures debuggable.
- **Politician cache**: `SourceRecord` rows store URL, quote, first-hand flag,
  retrieved-at. Research checks cache freshness (TTL) before spending Tavily
  credits — the main cost lever for freemium.
- **"First-hand sources only"** enforced at two levels: adapter-side filtering
  (exclude aggregators/opinion) + prompt rules requiring citations; every claim
  in a profile links to a `SourceRecord`.
- **Role config** (`apps/llm`): `profiler`, `researcher`, `summarizer`,
  `matcher`, `recommender`, `judge` — each `{base_url, api_key, model,
  temperature}`. One env var pattern, documented for self-hosters; hosted
  deployment never surfaces it.
- **Future-proofing**: `apps/elections` slot reserved for local-election lookup
  (Google Civic Information / Vote411 are the likely sources); swipe onboarding
  is a `profiler` addition, not a rewrite.
- **Specs-first docs split** (established at Phase 1 kickoff): `docs/` is
  human-readable narrative; `specs/` holds declarative agent-facing contracts
  (interfaces + numbered MUST/SHOULD rule IDs) — see `specs/README.md`. New
  component behavior lands as spec → code → tests citing rule IDs.

## Phases

| Phase | File | Scope | Status |
|---|---|---|---|
| 0 | [phase-0-foundation.md](phase-0-foundation.md) | Docs, tooling (cz, GHA), Django scaffold, Docker | done (GHA run pending first push) |
| 1 | [phase-1-llm-core.md](phase-1-llm-core.md) | Model-agnostic LLM layer, role config, ModelCall log | done |
| 2 | [phase-2-research-politicians.md](phase-2-research-politicians.md) | Source adapters, research swarm, politician cache | pending |
| 3 | [phase-3-v1-cutover.md](phase-3-v1-cutover.md) | Analysis pipeline, SSE, HTMX frontend, delete ADK+React | pending |
| 4 | [phase-4-accounts-saves.md](phase-4-accounts-saves.md) | Accounts, claim flow, history, entitlement hooks | pending |
| 5 | [phase-5-eval-harness.md](phase-5-eval-harness.md) | Golden datasets, LLM judge, CLI + staff dashboard | pending |
| 6 | [phase-6-growth.md](phase-6-growth.md) | Swipe onboarding, more adapters, local elections, Stripe | pending |

## Risks / notes

- **Raw OpenAI-compat client**: Anthropic-native API needs a proxy
  (LiteLLM/Ollama/OpenRouter) — fine for self-hosters, but document it clearly
  in `docs/self-hosting.md`.
- **SSE + Django requires ASGI** (uvicorn) — baked in at Phase 0; sync WSGI
  deployment must never sneak in.
- **Weak local models** may produce malformed JSON — structured-output retry +
  deterministic pipeline mitigates; the eval harness quantifies exactly this.
- **FEC covers federal only** — state/local donations come later with the
  elections phase.
- **Migration is a hard cutover** — no production users, no compat layer. Keep
  React app working until Phase 3 replaces it, then delete.

## Appendix — original brainstorm notes (verbatim, 2026-09-20)

```markdown
# Onboarding
- Tinder style swiping or current Questionnaire

# Enhancements
- Django backend
- HTMX frontedn with typescript where needed
- Agent swarm for research
- Politician information saved to database to reduce search costs
  - Profiles for politicians 

# Search
- New articles
- Youtube
- Social Media
- Voting History
- Accepted Donations
- Only first hand notes, specifically for news articles no he said/she said 

# UI/UX
- Logins to save profile 

# Development
- add cz
- add gha
```
