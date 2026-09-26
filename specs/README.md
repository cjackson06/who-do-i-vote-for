# Specs

Declarative contracts for how this repo's code should behave. Written for
**AI agents and assistant workflows** first; humans can read them too.

This is distinct from [`docs/`](../docs/) — narrative, human-facing
documentation (architecture, self-hosting guides). `docs/` explains the
system; `specs/` **prescribes** it.

## What belongs in a spec

- Exact interfaces: function signatures, pydantic/JSON schemas, env var
  tables, URL routes, model fields.
- Behavioral rules: inputs → outputs, invariants, ordering, retry/fallback
  semantics, failure modes.
- Error taxonomy and non-goals.

Not in a spec: tutorials, rationale essays, benchmarks, roadmap.

## File convention

- One file per app or cohesive component: `specs/<area>.md` (e.g.
  `specs/llm.md`, `specs/core-health.md`).
- Split into `specs/<area>-<component>.md` when a file outgrows ~200 lines.

## Anatomy

```markdown
# <Area> spec

> Source of truth for <component>. Code implements this spec; tests verify it.

## Purpose
Two or three sentences.

## Interfaces
Python-style signatures, pydantic models, env tables, routes.

## Rules
- **<AREA>-N (MUST|SHOULD|MUST NOT)** ...one behavior per rule...
- Rules are numbered and stable: never renumber; replace superseded rules.

## Errors
Table of exception/route-level errors and when they occur.

## Non-goals
Explicitly out of scope.
```

Rule IDs (`<AREA>-N`) are greppable anchors: tests cite them (docstrings,
e.g. `# Verify LLM-CLIENT-03`) and commits/PRs reference them. MUST rules are
enforced by tests or fail-fast code; SHOULD rules are advisory.

## Workflow rules

1. **Spec-first.** Write or update the spec before implementing a behavior.
2. **Same-PR.** Behavior changes land with the spec change in the same PR/commit
   series; a spec that drifts from code is a bug.
3. **Tests cite IDs.** Every MUST rule is covered by at least one test whose
   docstring references its rule ID.
