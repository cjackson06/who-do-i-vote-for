# Phase 2 — Politician Data + Research Swarm (`apps/politicians`, `apps/research`)

Goal: build + cache cited politician profiles from pluggable sources. This is
the cost lever for freemium and the substrate the analysis pipeline consumes.

## Design

- Models: `Politician`, `PoliticianProfile` (per-scope summary), `Fact`
  (claim + link), `SourceRecord` (url, source_type, first_hand flag,
  retrieved_at, TTL)
- `SourceAdapter` protocol: `async fetch(politician, topic) -> list[RawFinding]`
- v1 adapters: Tavily (web/news), FEC (donations, federal)
- Swarm: asyncio fan-out per candidate × per source; results → `summarizer`
  role → cited `Fact`s stored
- First-hand rule: adapter-side filtering (drop aggregators/opinion pieces) +
  prompt rules (require citation, reject hearsay)
- Cache-hit path: fresh `SourceRecord`s within TTL ⇒ skip paid calls;
  stale ⇒ targeted refresh

## Tasks
- [ ] Models + migrations (incl. unique constraints for cache identity)
- [ ] `SourceAdapter` protocol + adapter registry
- [ ] TavilyAdapter (search + extract, error/rate-limit handling)
- [ ] FECAdapter (candidate lookup + committee donations)
- [ ] Swarm orchestrator (fan-out, per-task timeouts, partial-failure tolerance)
- [ ] Summarizer step: findings → per-source summaries → profile `Fact`s with citations
- [ ] Cache freshness/TTL logic + targeted refresh
- [ ] Management command: `python manage.py research_politician "Name"`
- [ ] Tests: adapter fixtures (recorded HTTP), swarm fault injection, TTL behavior
- [ ] Cost logging tie-in: Tavily credits per run recorded alongside `ModelCall` rows

## Exit criteria
- [ ] Researching the same politician twice costs ~zero Tavily calls the second time
- [ ] Every stored `Fact` links to a `SourceRecord` with a first-hand flag
- [ ] Adding an adapter = implement protocol + register (no orchestrator changes)
