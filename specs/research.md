# Research spec (`apps/research`)

> Source of truth for source adapters, the swarm orchestrator, the
> summarizer step, research runs and their cost log, and the admin-triggered
> background task. Code implements this spec; tests verify it.

## Purpose

Fetch **first-hand**, citable findings about a politician from pluggable
sources, in parallel, at bounded cost, and turn them into a cached cited
profile. Sources in v1: web/news search (Tavily) and federal campaign-finance
records (FEC); more adapters later via the same protocol.

## Interfaces

### Topics

`POSITIONS = "positions"`, `VOTING_RECORD = "voting_record"`,
`CONTROVERSIES = "controversies"`, `DONATIONS = "donations"`. **Closed set**
(like LLM roles): adding a topic means spec + code + tests. Default topic =
all four.

### `SourceAdapter` protocol

```python
class RawFinding(BaseModel):
    url: str
    title: str
    content: str  # excerpt / chunk text supporting the claim
    first_hand: bool
    published_date: date | None = None
    score: float | None = None
    meta: dict = {}  # adapter-specific (fec totals, etc.)


class SourceAdapter(Protocol):
    name: str  # "tavily_web" | "tavily_news" | "fec"
    topic: str  # the single topic it covers

    def __init__(self, http_client: httpx2.AsyncClient) -> None: ...
    async def fetch(self, ref: PoliticianRef, topic: str) -> list[RawFinding]: ...
```

`PoliticianRef` = JSON-safe pydantic `{"id", "name", "party", "office",
"state", "fec_candidate_id"}`. Adapters never touch ORM rows.

#### Cell plan (topic × source)

| Topic | Sources |
|---|---|
| `positions` | `tavily_web` |
| `voting_record` | `tavily_web` |
| `controversies` | `tavily_news` |
| `donations` | `fec` |

An adapter covers exactly one cell type; the registry expands to multiple
cells per adapter (e.g. a future multi-topic news adapter) — orchestrator
iterates the registry, it does not hard-code maps per adapter.

### Registry

```python
def available_adapters() -> list[SourceAdapter]   # reads Settings; skips unconfigured
```

- `TAVILY_API_KEY` set → `TavilyAdapter("tavily_web", topics=positions, voting_record)`
  and `TavilyAdapter("tavily_news", topics=controversies)` (same class, two
  instances).
- `FEC_API_KEY` set (or `FEC_DEMO=1` for explicit DEMO_KEY opt-in) → `FECAdapter`.
- Adding an adapter = new module implementing the protocol + one registry
  line. No orchestrator edits (exit criterion).

### Env

| Env var | Required | Notes |
|---|---|---|
| `TAVILY_API_KEY` | no (adapter skipped) | Tavily search key |
| `FEC_API_KEY` | no (adapter skipped) | openFEC key; `DEMO_KEY` allowed via `FEC_DEMO=1` opt-in only |
| `TAVILY_BASE_URL` | no | default `https://api.tavily.com` |
| `FEC_BASE_URL` | no | default `https://api.open.fec.gov/v1` |

## Rules

### Tavily adapter

- **TAVILY-1 (MUST)** — call `POST {TAVILY_BASE_URL}/search` with
  `Authorization: Bearer <TAVILY_API_KEY>`; body: `query`, `topic`,
  `search_depth: "basic"`, `chunks_per_source: 3`, `max_results: 10`,
  `exclude_domains: <denylist>`.
- **TAVILY-2 (MUST)** — `tavily_web` uses `topic: "general"`,
  `tavily_news` uses `topic: "news"` with `time_range: "year"`.
- **TAVILY-3 (MUST)** — response mapping: `results[]` → `RawFinding(url, title,
  content, published_date, score)`; `first_hand` heuristic: url host equals
  the politician's known official domains or endswith `.gov` → True; else
  False. Official-domain detection: `.gov/` TLDs and campaign/official
  host allowlist constants; everything else first_hand=False (the summary
  prompt still rejects hearsay — defense in depth with SUMMARIZER-2).
- **TAVILY-4 (MUST)** — adapter-side filtering: `exclude_domains` denylist
  constant includes known aggregators/opinion-first hosts
  (reddit.com, quora.com, medium.com, wikipedia.org, ballotpedia.org,
  procon.org, ontheissues.org …); list lives in the adapter module, changes
  are code+spec+test changes together.
- **TAVILY-5 (MUST)** — HTTP 429 or 5xx: exactly one retry after ≥1s backoff,
  then `AdapterError`. Other HTTP 4xx (401/403/400): `AdapterError`
  immediately (no retry; 401/403 indicate bad key).
- **TAVILY-6 (MUST)** — credit accounting: 1 credit per search request
  (`search_depth=basic`) — recorded on the run's `SourceCall` row with the
  actual HTTP latency and status.
- **TAVILY-7 (MUST)** — never log or store the API key; only the base URL.

### FEC adapter

- **FEC-1 (MUST)** — resolve the candidate first:
  `GET /candidates/search/?q=<name>&api_key=<key>`; pick best match (exact
  name normal order > party/state filter match). The adapter exposes this as
  a dedicated `async resolve_candidate(ref) -> str` (or raises
  `AdapterError` "candidate not found" — never a fabricated id); the
  **swarm** persists the id to `politician.fec_candidate_id` (adapters never
  touch ORM rows). Resolution happens once per run and is reused.
- **FEC-2 (MUST)** — donations findings come from authorized-committee
  totals: GET `/candidate/<id>/committees/history/?cycle=<CUR>` →
  committee ids → `GET /committee/<id>/totals/?cycle=<CUR>` → one RawFinding
  per committee: url = fec.gov contribution page permalink, `content` =
  human-readable totals line (receipts, individual contributions), meta =
  raw numbers. Dedupe by committee id.
- **FEC-3 (MUST)** — every call passes `api_key` as a query param; FEC is
  free → credits 0 on `SourceCall` rows; 429/5xx → one retry (FEC-3 backoff
  ≥2s), then `AdapterError`. DEMO_KEY has hard rate limits; production uses
  a real key.
- **FEC-4 (MUST)** — federal only in v1: candidates with no federal match →
  `AdapterError`; adapters never claim data outside their scope.
- **FEC-5 (MUST)** — `first_hand=True` always (official agency records).

### Swarm orchestrator (`swarm.py`)

```python
async def research_politician(
    ref: PoliticianRef, topics: list[str], *, force_refresh: bool = False,
    run_id: int,
) -> None
```

- **SWARM-1 (MUST)** — plan = for each topic, every available adapter cell;
  fresh cells (CACHE-4) skipped unless `force_refresh`. Plan + decision
  recorded in the run's stats.
- **SWARM-2 (MUST)** — cells run concurrently (`asyncio.gather` with
  `return_exceptions=True`) under a per-cell `asyncio.timeout(45s)`.
- **SWARM-3 (MUST)** — partial failure tolerance: one cell's `AdapterError`/
  timeout never fails the run; failures are recorded per cell in run stats.
  If ≥1 cell succeeded → run `degraded` (unless all succeeded → `completed`);
  all cells failed → run `failed`.
- **SWARM-4 (MUST)** — persist: one `SourceRecord` per finding (dedupe via
  unique constraint `update_or_create`), one `SourceCall` row per outbound
  HTTP call (success or failure), run stats updated with counts
  (`findings`, `cells_ok`, `cells_failed`, `cache_hits`).
- **SWARM-5 (MUST)** — after fetches, hand the per-topic persisted records to
  the summarizer (SUMMARIZER-1) and finalize the run:
  `queued → running → completed|degraded|failed` happens in the task
  (RUN-2), but the swarm itself is exception-safe: any unexpected error is
  recorded and re-raised for the task wrapper to mark `failed`.
- **SWARM-6 (SHOULD)** — politician ORM access via `sync_to_async`;
  findings→DB persistence batches transactionally per cell.

### Summarizer step (`summarize.py`, prompt `apps/llm/prompts/research_summarizer.py`)

- **SUMMARIZER-1 (MUST)** — one `summarizer`-role call per (non-cached) topic
  with schema `TopicSummary{summary: str, facts: list[FactDraft]}`,
  `FactDraft{claim, quote, source_url}`. Uses `LLMClient.complete(schema=...)`
  with `prompt_name/version` from the prompt module (LLM-PROMPT-3).
- **SUMMARIZER-2 (MUST)** — prompt builds in the findings (title + chunk
  content + url + first-hand flag) and instructs: every fact must cite only
  the provided sources; reject hearsay/collation ("he said, she said"),
  editorializing, and aggregator content; prefer first-hand domains; facts
  without a provable source are omitted, never invented.
- **SUMMARIZER-3 (MUST)** — citation validation before storage: each
  `fact.source_url` must (case/fragment-insensitively) match a persisted
  `SourceRecord.url` from this run; mismatches are dropped and counted in
  run stats (`facts_dropped`). Valid ones store `Fact(claim, quote,
  source_record)`.
- **SUMMARIZER-4 (MUST)** — `StructuredOutputError` or other `LLMError` from
  a topic call marks that topic failed (counted) but does not abort the run
  unless ALL topics failed (→ run `failed`, see POLITICIAN-3b: no partial
  profile).
- **SUMMARIZER-5 (MUST)** — profile text = topic summaries joined under
  topic headers (deterministic; no extra LLM call in Phase 2).

### Runs and cost log

```python
RunStatus: QUEUED | RUNNING | COMPLETED | DEGRADED | FAILED
```

- **RUN-1 (MUST)** — admin trigger creates `ResearchRun(status=queued,
  topics, force_refresh)` and enqueues the task after commit
  (`transaction.on_commit(partial(run_research.enqueue, politician_id,
  run_id))`). Run rows are staff-visible in the admin (read-only after
  creation; status/credits/error/stats fields update as work proceeds).
- **RUN-2 (MUST)** — the registered task
  `run_research(politician_id, run_id)` MUST: load rows (sync), set RUNNING,
  run the swarm (which re-verifies the run row state is `queued`), finalize
  the terminal status. Unexpected exceptions mark the run `failed` with the
  error text, then re-raise (framework captures the traceback, TASKBACKEND-2).
- **RUN-3 (MUST)** — every outbound source HTTP call gets a `SourceCall` row
  (`run` FK, adapter name, topic, query/endpoint, credits, latency_ms, status
  ok|error, truncated error). No API key values ever stored.
- **RUN-4 (MUST)** — `ResearchRun.credits` accumulates paid-source credits
  (Tavily 1/call; FEC 0) alongside `ModelCall` rows for the LLM calls of the
  same run.

## Errors

| Exception | When | Surfaced as |
|---|---|---|
| `AdapterError` | adapter exhausted retries / bad key / upstream failure | cell failed; run degraded/failed; `SourceCall` error row |
| `asyncio.TimeoutError` | cell exceeded SWARM-2 timeout | cell failed; run degraded |
| `StructuredOutputError` | summarizer schema failure after budget (LLM-CLIENT-5) | topic failed; per SUMMARIZER-4 |
| `RoleNotConfigured` | summarizer role unconfigured | run failed before any paid calls |

## Non-goals

- No extract/full-page scraping (search chunks suffice in v1).
- No voting-history/social/YouTube adapters (Phase 6).
- No free-form agent loops; deterministic fan-out only.
- No user-facing pages; admin trigger only (Phase 3 wires the web pipeline to
  the same service layer).
