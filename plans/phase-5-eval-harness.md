# Phase 5 — Eval Harness (`apps/evals`) + Staff Dashboard

Goal: quantify model quality for summarization + information-finding. Runs via
CLI management command; results viewable in a staff-only dashboard.

## Design

- Golden dataset (YAML in-repo, versioned):
  - **Summarization tasks**: political texts + rubrics (faithfulness, coverage,
    first-hand-only, citation quality)
  - **Information-finding tasks**: verifiable questions (donations, positions,
    votes) with answer keys
- Judge: `judge` role LLM-as-judge with rubric prompts; judge ≠ candidate
  model; order randomization to limit position bias
- `EvalRun` / `EvalResult` models; runs concurrency-limited; markdown/JSON reports
- Staff dashboard: trigger runs, SSE progress, leaderboard, per-task drill-down
  with judge rationales

## Tasks
- [ ] Dataset schema + seed datasets (both task types)
- [ ] Runner management command:
      `python manage.py run_evals --role summarizer --models a,b,c`
- [ ] Judge implementation + bias mitigations; abstain/invalid handling
- [ ] Reports: JSON + markdown (leaderboard + per-task breakdown)
- [ ] Models: `EvalRun` / `EvalResult` with per-item token + latency capture
- [ ] Staff-only dashboard (`is_staff`): run trigger, HTMX SSE progress,
      leaderboard, drill-down
- [ ] Tests: offline judge fixtures, dataset validation, runner idempotency
- [ ] Docs: how to add tasks/datasets; interpreting reports

## Exit criteria
- [ ] One command produces a model leaderboard for summarizer + researcher roles
- [ ] Dashboard is staff-only and shows judge rationales
- [ ] New models/datasets evaluable without code changes
