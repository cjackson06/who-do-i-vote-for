# Phase 2.5 — Staff Console (`apps/console`)

Goal: give research operations a purpose-built UI — Django admin is
model-centric CRUD, but the ops loop (seed politicians → trigger research →
monitor runs → review cited profiles → watch costs) spans six models and
needs workflow screens. Mid-cycle phase between 2 and 3; admin **coexists**
(admin keeps raw row editing + users/auth; both surfaces share services).

> Scope locked in plan review 2026-09-28: ops dashboard, trigger-with-options,
> run monitoring, profile/fact review with **full edit curation**, politician
> ingestion, cost explorer. No live updates yet — run-status fragments reserve
> stable DOM ids so Phase 3 SSE swaps into them without URL/API changes.
> Specs: `specs/console.md` (new) + amendments in `specs/research.md`,
> `specs/politicians.md`, `specs/llm.md`.

## Decisions (from plan review, 2026-09-28)

| Area | Decision |
|---|---|
| Relationship to admin | Coexist at `/staff/` — console for workflows, admin for raw CRUD; single shared trigger service |
| Curation | Full edit (rewrite claim/quote, hide/unhide, delete) with a `FactRevision` audit trail |
| Edits vs regeneration | **Pin edits**: staff-edited facts survive re-research verbatim; hidden re-applies by `(topic, source_record)`; unedited machine facts replaced |
| Live updates | None in 2.5 (manual refresh); fragments carry SSE-reserved ids (CONSOLE-6) — polling replaced by SSE at Phase 3 |
| CSS pipeline | django-tailwind (pulls Phase 3's "Tailwind setup" forward); htmx vendored as pinned static |
| ModelCall ↔ run link | Nullable `research_run` FK now (pulls forward the Phase-1 "nullable FKs by migration" decision for research runs; `analysis_job` FK still lands in Phase 3) |

## Design

- **Pages/routes** (all `staff_member_required`, login reuses admin login):
  - `/staff/` — dashboard: adapter/LLM-role config health, run counts by
    status (now / 7d), Tavily credits + model token spend (today/7d/30d),
    stale & never-researched counts, recent failures with retry links
  - `/staff/politicians/` roster: search, party/state/freshness/last-run
    filters, per-cell freshness chips (CACHE-6 bulk helper), bulk select →
    trigger
  - `/staff/politicians/new/` ingestion: single form + bulk paste
    (`Name,Party,Office,State` per line) with per-line report (CONSOLE-4)
  - `/staff/politicians/fec-search/` HTMX fragment (FEC-6): query → candidate
    list → create with `fec_candidate_id`; duplicates link to existing
  - `/staff/politicians/<pk>/` detail: identity, cells, spend, run history
  - `/staff/profiles/<pk>/` review + curation: summary per topic, fact cards
    (claim inline-edit, quote, citation + source excerpt, first-hand badge),
    hide/unhide, delete, revision history; hidden facts dimmed behind toggle
  - `/staff/runs/` list; `/staff/runs/<pk>/` detail (status, stats panels,
    `SourceCall` + `ModelCall` tables, Retry per RUN-5); `/staff/runs/trigger/`
    form (politicians, topic checkboxes default all, force toggle)
  - `/staff/costs/` explorer: Sources tab (credits/calls/errors by day /
    adapter / run / politician) · Models tab (tokens, latency, failures by
    day / role / model) — tables first, no chart islands
- Data model: `Fact` gains `status` (published|hidden), `edited_at`,
  `edited_by`; new `FactRevision` (snapshot per curation action; editor +
  timestamp, CONSOLE-5/POLITICIAN-6); `ModelCall.research_run` FK (SET_NULL)
- **Service moves/refactors**: `enqueue_research()` out of
  `apps/research/admin.py` → `apps/research/services.py` (admin action calls
  it too); curation-aware `replace_profile()` keeps POLITICIAN-3 atomicity
  while pinning edited facts and carrying hidden decisions (POLITICIAN-7);
  `fresh_cells_bulk(politician_ids)` in `apps/politicians/cache.py`;
  `FECAdapter.search_candidates(query)`; summarizer threads `run_id` into
  `complete()` (LLM-CALL-4)
- Console internals: `apps/console` app with views/forms/queries/urls; sync
  views only (no new async surface); aggregations via ORM annotate/aggregate
  (CONSOLE-7); HTMX requests return partials, full loads return pages
  (CONSOLE-2)
- Tooling: django-tailwind theme app + `just css`/`just css-watch` + Docker
  build stage (verify v4 packaging via docs at kickoff — see risks); pinned
  vendored `htmx.min.js`; `TEMPLATES["DIRS"]` adds project-level
  `backend/templates/` (staff base today, public base in Phase 3)

## Tasks

Spec-first, then data layer, then scaffold, then pages (workflow order):

- [ ] Specs: `specs/console.md` (CONSOLE-1..7) + amendments — research.md
      (RUN-1 reworded to shared staff trigger, new RUN-5 retry-clone,
      FEC-6 search_candidates, SUMMARIZER-1 run linkage, non-goals update),
      politicians.md (Fact/FactRevision fields, POLITICIAN-6/-7, CACHE-6),
      llm.md (research_run FK, complete()/stream() param, LLM-CALL-4)
- [ ] Models + migrations: Fact curation fields + FactRevision;
      ModelCall.research_run FK
- [ ] Services: `enqueue_research` move + admin action rewire; curation
      service (edit/hide/unhide/delete writing revisions); curation-aware
      `replace_profile`; `fresh_cells_bulk`; `search_candidates` +
      `CandidateMatch` schema; run_id threading through summarize
- [ ] Tooling: django-tailwind theme app + just recipes + Docker stage;
      vendored htmx; settings (INSTALLED_APPS, TEMPLATES DIRS, LOGIN_URL);
      base staff template + nav
- [ ] `apps/console` scaffold: urls/views/forms/queries, staff gate,
      pipeline/adapter health panel
- [ ] Dashboard page (counts, spend, stale counts, recent failures)
- [ ] Roster + politician detail (filters, freshness chips, spend)
- [ ] Ingestion: single + bulk paste with per-line report; FEC search
      fragment with duplicate linking
- [ ] Trigger flow: form + roster-bulk modal, topics/force options, redirect
      to run detail
- [ ] Runs list + detail (+ Retry cloning per RUN-5); SSE-reserved fragment
      ids on run-status/-stats/-calls partials (CONSOLE-6)
- [ ] Profile review + curation UI (inline claim edit via HTMX, hide/unhide,
      delete, revision history)
- [ ] Cost explorer (Sources / Models tabs)
- [ ] Docs: architecture.md console surface; self-hosting.md staff access
      (`createsuperuser` / `is_staff`, `/staff/`); README pointer
- [ ] Tests (offline, citing rule IDs): gate + fragment-vs-page (CONSOLE-1/2),
      trigger via shared service (RUN-1/CONSOLE-3), retry-clone (RUN-5),
      bulk ingestion report (CONSOLE-4), FEC search via MockTransport +
      unconfigured fallback (FEC-6), revision writes (CONSOLE-5/POLITICIAN-6),
      regeneration pinning/carry-over atomicity (POLITICIAN-3/-7), ModelCall
      run linkage (LLM-CALL-4), aggregation math (CONSOLE-7), roster chips
      (CACHE-6)
- [ ] Live smoke (keys): seed via FEC search → trigger 2 topics → run detail
      → edit + hide a fact → re-run → verify pinning + carry-over; document
      here

## Exit criteria

- [ ] Full ops loop live in console with zero admin visits: ingest
      (FEC search/bulk) → trigger with topic/force options → inspect run
      detail → review cited profile → edit/hide facts → re-research →
      edits pinned, hidden carried over
- [ ] Dashboard answers "what's stale, what failed, what did it cost" on one
      screen; cost explorer aggregates `SourceCall` credits and `ModelCall`
      tokens by run/day/role
- [ ] Admin coexists intact; both surfaces share `enqueue_research`
- [ ] Run screens render without background execution; SSE attaches to the
      reserved fragments without changing their URLs (CONSOLE-6)
- [ ] `just preflight` green; live smoke documented above

## Risks / notes

- **django-tailwind packaging** (v4 support, `[bin]` extra vs node) is the
  least-certain piece — verify with current docs first; fallback documented:
  pinned Tailwind standalone CLI recipes (no npm).
- **Pinning edge case**: `prune_stale` (CACHE-5, currently unused housekeeping)
  must not delete `SourceRecord`s referenced by pinned facts — FK policy
  checked when pinning lands (politician spec note, POLITICIAN-7).
- Roster freshness chips must not N+1: CACHE-6 bulk helper is the contract.
- No polling/SSE in 2.5 → no new concurrency surface; console views stay
  sync-ORM only (SWARM-6 sqlite constraints untouched).
