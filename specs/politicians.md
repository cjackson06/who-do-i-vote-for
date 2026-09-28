# Politician cache spec (`apps/politicians`)

> Source of truth for the politician data models, the first-hand source
> policy, the TTL cache that shields paid sources from repeated research,
> and profile regeneration. Code implements this spec; tests verify it.

## Purpose

Every claim the product makes about a politician comes from a cached,
cited research corpus in this app. Caching research **per (politician,
source-type, topic) cell** is the main cost lever for freemium: repeat
research of a fresh politician costs ~zero paid calls.

## Interfaces

### Models

| Model | Fields (beyond FK/timestamps) |
|---|---|
| `Politician` | `name` (200) · `party` (blank) · `office` (blank) · `state` (2-char, blank) · `fec_candidate_id` (unique, null) |
| `PoliticianProfile` | FK `politician` · `scope` (choices `federal`) · `summary` (text) · `generated_at` · FK `ResearchRun` null |
| `Fact` | FK `profile` · `topic` · `claim` (text) · `quote` (text blank) · FK `SourceRecord` (not null) |
| `SourceRecord` | FK `politician` · `source_type` · `topic` · `url` (500) · `url_hash` (64 hex) · `title` · `content` · `first_hand` (bool) · `published_date` null · `retrieved_at` · `fresh_until` |

### Choices

```python
SourceRecord.SourceType: TAVILY_WEB = "tavily_web" | TAVILY_NEWS = "tavily_news" | FEC = "fec"
PoliticianProfile.Scope: FEDERAL = "federal"
Fact.Topic: POSITIONS | VOTING_RECORD | CONTROVERSIES | DONATIONS  # mirrors apps.research.topics
```

### Cache helpers (`apps/politicians/cache.py`)

```python
TTL_DAYS: dict[str, timedelta]           # per SourceType, see CACHE-2
def fresh_until(source_type: str, now) -> datetime
def fresh_cells(politician_id, now=None) -> set[CacheCell]   # CacheCell = (source_type, topic)
def is_fresh(politician_id, source_type: str, topic: str, now=None) -> bool
def prune_stale(politician_id) -> int
```

### unique constraints

| Model | Constraint |
|---|---|
| `Politician` | `(name, office, state)`; `fec_candidate_id` unique |
| `PoliticianProfile` | `(politician, scope)` |
| `SourceRecord` | `(politician, source_type, topic, url_hash)` (long URLs hash for constraint compactness) |

## Rules

- **POLITICIAN-1 (MUST)** — a politician identity is `(name, office, state)`;
  concurrent duplicate inserts fail on the unique constraint. `fec_candidate_id`
  is optional and unique when present.
- **POLITICIAN-2 (SHOULD)** — `name` is user-facing display text as entered by
  staff in the admin; no normalization beyond strip() before save.
- **POLITICIAN-3 (MUST)** — profile regeneration (new research run commits
  facts for the same scope) MUST be atomic: delete the old profile's facts +
  single profile row, then insert the new ones in one transaction. Readers
  never see a half-regenerated profile.
- **POLITICIAN-3b (MUST)** — regeneration MUST only replace the profile when
  the summarizer produced content for it; a failed/partial summarize MUST leave
  the previous profile intact.
- **CACHE-1 (MUST)** — cache identity is the cell `(politician, source_type,
  topic)`. Every `SourceRecord` row belongs to exactly one cell.
- **CACHE-2 (MUST)** — freshness of a cell = at least one of its
  `SourceRecord`s has `fresh_until > now`, where `fresh_until = retrieved_at +
  TTL(source_type)`: `tavily_news` → 7 days, `tavily_web` → 30 days, `fec` →
  90 days. A cell with zero records is never fresh (refetched; accepted v1
  tradeoff for zero-result searches).
- **CACHE-3 (MUST)** — TTL values are module constants in
  `apps/politicians/cache.py`, stated in this spec; changes are spec + code +
  test changes together. Callers MUST pass `now` explicitly when the decision
  must be testable.
- **CACHE-4 (MUST)** — a run that finds every intended cell fresh MUST NOT
  issue any adapter call for those cells (exit criterion: re-research costs
  ~0 Tavily credits). `force_refresh` bypasses freshness for the run's topics.
- **CACHE-5 (SHOULD)** — `prune_stale` deletes records whose cells are stale
  beyond a grace multiple (2× TTL); optional, used by future housekeeping.
- **SOURCE-1 (MUST)** — every `SourceRecord` row stores `url`, `title`,
  `content` excerpt, `retrieved_at`, `first_hand`, and its cell identity;
  `url_hash` is lowercase SHA-256 of the `url` string.
- **SOURCE-2 (MUST)** — `first_hand` is decided adapter-side at fetch time
  (see `specs/research.md`), stored, and never recomputed from cached rows.
- **FACT-1 (MUST)** — every `Fact` links to exactly one `SourceRecord`
  (`source_record` not null) citing where the claim came from.
- **FACT-2 (MUST)** — facts are stored only with resolvable citations: the
  summarizer's floating `source_url` string is validated against the run's
  persisted `SourceRecord` URLs before the fact is saved (see SUMMARIZER-3);
  unresolvable citations are dropped, not stored.

## Errors

| Case | Behavior |
|---|---|
| duplicate `(name, office, state)` insert | `IntegrityError` (framework) |
| summarizer cites unknown URL | fact dropped; counted in run stats (see `specs/research.md`) |
| profile regeneration mid-run | validation/summary failure aborts regeneration; previous profile stays (POLITICIAN-3b) |

## Non-goals

- Fixtures/dedupe beyond the unique constraints; no politician merging UI yet.
- No per-user profiles; profiles are system-wide cached facts.
- State/local election coverage (`apps/elections`, Phase 6).
