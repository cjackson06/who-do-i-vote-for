# Phase 2 — Politician Data + Research Swarm (`apps/politicians`, `apps/research`)

Goal: build + cache cited politician profiles from pluggable sources. This is
the cost lever for freemium and the substrate the analysis pipeline consumes.

> Triggers are staff-only via the **Django admin** using Django 6's native
> `django.tasks` framework — no data-management CLI commands (decision from
> plan review: "django cli is for managing django itself"). Execution uses a
> small in-process ASGI task backend (`apps/core`); swapping to a durable
> backend later is settings-only. See `specs/core-tasks.md`,
> `specs/politicians.md`, `specs/research.md`.

## Design

- Models: `Politician`, `PoliticianProfile` (per-scope summary), `Fact`
  (claim + link), `SourceRecord` (url, source_type, first_hand flag,
  retrieved_at, TTL); plus `ResearchRun` + `SourceCall` (cost log) in
  apps/research
- `SourceAdapter` protocol: `async fetch(ref, topic) -> list[RawFinding]`
- v1 adapters: Tavily (web/news), FEC (donations, federal)
- Cell plan: positions→tavily_web, voting_record→tavily_web,
  controversies→tavily_news, donations→fec
- Swarm: `asyncio.gather` fan-out per cell; per-cell timeout; results →
  `summarizer` role → cited `Fact`s stored
- First-hand rule: adapter-side filtering (drop aggregators/opinion) +
  prompt rules (require citation, reject hearsay)
- Cache-hit path: fresh `SourceRecord`s within TTL ⇒ skip paid calls;
  stale ⇒ targeted refresh (`force_refresh` bypasses)
- Background execution: `django.tasks` `@task run_research` +
  `apps.core.tasks.InProcessBackend` (Django admin action triggers, never
  blocks the request; `transaction.on_commit` enqueue)

## Tasks
- [ ] Specs first: `specs/core-tasks.md`, `specs/politicians.md`,
      `specs/research.md`, settings-env rows
- [ ] `InProcessBackend` + ASGI loop capture + `TASKS` settings + tests;
      `uv add httpx2` (direct dep)
- [ ] Models + migrations (unique constraints for cache identity) +
      cache TTL helpers
- [ ] `apps/politicians` admin registration (browse) + `apps/research`
      models (`ResearchRun`, `SourceCall`) + admin
- [ ] `SourceAdapter` protocol + `RawFinding` schema + registry
- [ ] TavilyAdapter (search, exclude-domains, first-hand heuristic,
      credit accounting, one-retry on 429/5xx)
- [ ] FECAdapter (candidate resolution → committees → totals)
- [ ] Swarm orchestrator (fan-out, per-cell timeouts, partial-failure
      tolerance)
- [ ] Summarizer step: findings → per-topic `TopicSummary` (+facts with
      citations) → profile `Fact`s; citation validation; prompts module in
      `apps/llm/prompts/`
- [ ] Cache freshness/TTL logic + targeted refresh (`force_refresh`)
- [ ] Admin trigger: Politician "Run research" action → `ResearchRun`(queued)
      → enqueue task on commit; runs/runs' cost `SourceCall` visible in admin
- [ ] Tests: adapter fixtures (recorded HTTP via MockTransport), swarm fault
      injection, TTL behavior, backend semantics — all offline
- [ ] Cost logging tie-in: Tavily credits per run recorded alongside
      `ModelCall` rows
- [ ] Live smoke (keys): admin-trigger a real research run; re-run shows
      cache hit (~0 Tavily calls)

## Exit criteria
- [ ] Researching the same politician twice costs ~zero Tavily calls the
      second time (verified by test + live smoke)
- [ ] Every stored `Fact` links to a `SourceRecord` with a first-hand flag
- [ ] Adding an adapter = implement protocol + register (no orchestrator
      changes)
- [ ] Trigger-to-result flow fully in admin (no data CLI)

