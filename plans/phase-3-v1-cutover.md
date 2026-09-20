# Phase 3 — v1 Cutover: Pipeline, SSE, HTMX Frontend

Goal: replace the ADK backend and React frontend with the Django + HTMX app
end-to-end. The big phase.

## Design

- `apps/profiler`: questionnaire session (conversational profiling via the
  `profiler` role) → structured `UserProfile`
- `apps/analysis`: `AnalysisJob` + `AnalysisStep` (research → match →
  recommend); pipeline runner as a background asyncio task; steps persisted for
  observability/debugging
- SSE: `StreamingHttpResponse` on the ASGI view; events from an in-process
  pub/sub (single container now; Redis later without changing the API)
- HTMX + Tailwind templates; TS islands only where needed (result charts)
- Hard cutover, no compat layer (no production users)

## Tasks

### Backend
- [ ] `apps/profiler`: session model, HTMX questionnaire flow, `UserProfile`
      extraction (structured output)
- [ ] `apps/analysis`: job/step models, pipeline runner wiring research swarm →
      matcher → recommender
- [ ] Final structured result schema: candidate, party, reason, compatibility,
      expanded_reason, citations
- [ ] SSE endpoint + event schema (`step_started` / `step_completed` /
      `step_failed` / `final`), reconnect-safe
- [ ] Anonymous session identity (session key / signed cookie) so results
      survive navigation

### Frontend
- [ ] Base template + Tailwind setup (replaces shadcn/react)
- [ ] Pages: welcome, questionnaire, candidate selection, live progress (HTMX
      SSE extension), results (compatibility cards, cited reasons)
- [ ] TS island only if needed (result charts)

### Cutover
- [ ] Delete: `google-adk` dep, `my_politician/`, `political_profiler/`,
      `client/` (React), old Dockerfiles
- [ ] docker-compose updated (web + db only); README rewrite: hosted vs
      self-host quickstart
- [ ] CI drops the frontend build job
- [ ] E2E smoke-test path documented

## Exit criteria
- [ ] Full journey in Docker Compose with zero React: welcome → questionnaire →
      candidates → live progress → cited results
- [ ] ADK fully removed; no raw-ADK protocol anywhere
- [ ] Pipeline steps visible in DB + streamed via SSE
