"""Swarm orchestrator — contract: specs/research.md (SWARM-*, SUMMARIZER-*, RUN-*)."""

import asyncio
import json
from datetime import timedelta
from typing import Any

import httpx2
import pytest
from asgiref.sync import sync_to_async
from django.utils import timezone

# LLM-CALL-3/SWARM-6: sync_to_async ORM writes inside async code need
from apps.llm.client import LLMClient
from apps.politicians.cache import TTL_DAYS
from apps.politicians.models import (
    Fact,
    Politician,
    PoliticianProfile,
    SourceRecord,
)
from apps.research.errors import AdapterError
from apps.research.models import ResearchRun, SourceCall
from apps.research.schemas import CallRecord, FetchOutcome, PoliticianRef, RawFinding
from apps.research.swarm import research_politician
from apps.research.topics import TOPICS


@pytest.fixture(autouse=True)
def _clean_corpus(db) -> None:
    """Transactional tests commit — clear the corpus before each test."""
    from apps.llm.models import ModelCall

    ModelCall.objects.all().delete()  # type: ignore[unresolved-attribute]
    Politician.objects.all().delete()  # type: ignore[unresolved-attribute]
    ResearchRun.objects.all().delete()  # type: ignore[unresolved-attribute]


NOW = timezone.now()

ROLE_ENV_FIELDS = ("BASE_URL", "API_KEY", "MODEL", "TEMPERATURE")


@pytest.fixture(autouse=True)
def summarizer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hermetic env: configure only the `summarizer` role."""
    from apps.llm.config import ROLES

    for role in ROLES:
        for field in ROLE_ENV_FIELDS:
            monkeypatch.delenv(f"LLM_{role.upper()}_{field}", raising=False)
    monkeypatch.setenv("LLM_SUMMARIZER_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_SUMMARIZER_MODEL", "test-model")


async def acount(model, **filters) -> int:
    """Async-safe count helper (tests run on the event loop)."""

    def _count() -> int:
        return model.objects.filter(**filters).count()

    return await sync_to_async(_count)()


async def aget(model, **filters):
    return await sync_to_async(lambda: model.objects.get(**filters))()


async def arefresh(obj) -> None:
    await sync_to_async(obj.refresh_from_db)()


def _finding(
    url: str, content: str = "claim text", *, first_hand: bool = True
) -> RawFinding:
    return RawFinding(url=url, title="t", content=content, first_hand=first_hand)


def _outcome(findings: list[RawFinding], credits: int = 1) -> FetchOutcome:
    call = CallRecord(
        endpoint="https://api.test/search", query="q", credits=credits, latency_ms=5
    )
    return FetchOutcome(findings=findings, calls=[call])


class FakeAdapter:
    """Scriptable adapter for swarm tests."""

    def __init__(
        self,
        name: str,
        topics: tuple[str, ...],
        script: dict[str, Any],
    ) -> None:
        self.name = name
        self.topics = topics
        self.script = script  # topic -> FetchOutcome | Exception | "timeout"
        self.calls: list[str] = []

    async def fetch(self, ref: PoliticianRef, topic: str) -> FetchOutcome:
        self.calls.append(topic)
        behavior = self.script[topic]
        if behavior == "timeout":
            await asyncio.sleep(3600)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


@pytest.fixture
def politician(db) -> Politician:
    return Politician.objects.create(name="Jane Doe", party="DEM", state="PA")


@pytest.fixture
def run(db, politician) -> ResearchRun:
    return ResearchRun.objects.create(politician=politician, topics=list(TOPICS))


@pytest.fixture
def summarizer_llm(llm_testkit) -> LLMClient:
    """LLMClient whose summarizer role replies with canned TopicSummary JSON.

    The handler cites a source only if that source appears in the prompt
    (mimicking a well-behaved model) plus one ghost citation to exercise
    SUMMARIZER-3 dropping.
    Env comes from the module's autouse `summarizer_env` (conftest's
    `llm_env` would wipe it — it clears every role).
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        prompt_text = str(request.content)
        cite = (
            "https://www.fec.gov/data/committee/C1/"
            if "fec.gov" in prompt_text
            else "https://src.example/1"
        )
        content = json.dumps(
            {
                "summary": "Jane Doe supports X.",
                "facts": [
                    {
                        "claim": "Supports policy X",
                        "quote": "claim text",
                        "source_url": cite,
                    },
                    {
                        "claim": "Invented claim",
                        "quote": "",
                        "source_url": "https://not-in-run.example/ghost",
                    },
                ],
            }
        )
        return httpx2.Response(200, json=llm_testkit.completion(content))

    return llm_testkit.make_client(handler)


# SWARM-1..4: happy path
async def test_full_run_persists_everything(
    db, politician, run, summarizer_llm
) -> None:
    """SWARM-1..4: cells fetched, records + calls persisted, facts stored,
    profile regenerated, run completed with stats and credits."""
    adapters = [
        FakeAdapter(
            "tavily_web",
            ("positions",),
            {"positions": _outcome([_finding("https://src.example/1")])},
        ),
        FakeAdapter(
            "fec",
            ("donations",),
            {
                "donations": _outcome(
                    [
                        _finding(
                            "https://www.fec.gov/data/committee/C1/", first_hand=True
                        )
                    ],
                    credits=0,
                )
            },
        ),
    ]
    report = await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions", "donations"],
        run_id=run.pk,
        llm=summarizer_llm,
        adapters=adapters,
    )

    await arefresh(run)
    assert run.status == ResearchRun.Status.COMPLETED
    assert run.credits == 1  # fec is free
    assert run.stats["facts_stored"] == 2
    assert (
        run.stats["facts_dropped"] == 2
    )  # one ghost citation per topic (SUMMARIZER-3)

    assert await acount(SourceRecord) == 2
    assert await acount(SourceCall) == 2

    profile = await aget(PoliticianProfile, politician=politician)
    facts = await sync_to_async(
        lambda: list(profile.facts.select_related("source_record").all())
    )()
    assert len(facts) == 2
    assert {fact.topic for fact in facts} == {"positions", "donations"}
    by_topic = {fact.topic: fact for fact in facts}
    assert by_topic["positions"].source_record.url == "https://src.example/1"  # FACT-1
    assert by_topic["donations"].source_record.first_hand is True
    assert "## positions" in profile.summary  # SUMMARIZER-5 headers
    assert profile.summary.startswith("## positions\nJane Doe supports X.")

    assert report.cells_ok == 2
    assert report.cells_total == 2


# SWARM-3: partial failure
async def test_partial_failure_degrades(db, politician, run, summarizer_llm) -> None:
    """SWARM-3: one failing cell → run degraded, other cells still processed."""
    adapters = [
        FakeAdapter(
            "tavily_web",
            ("positions",),
            {"positions": _outcome([_finding("https://src.example/1")])},
        ),
        FakeAdapter(
            "tavily_news",
            ("controversies",),
            {
                "controversies": AdapterError(
                    "tavily_news", "HTTP 429 after 2 attempt(s)"
                )
            },
        ),
    ]
    report = await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions", "controversies"],
        run_id=run.pk,
        llm=summarizer_llm,
        adapters=adapters,
    )
    await arefresh(run)
    assert run.status == ResearchRun.Status.DEGRADED
    assert report.cells_ok == 1
    assert report.cells_failed == 1
    assert "tavily_news" in run.error
    # error-path SourceCall row exists for the failed cell (RUN-3)
    failed_calls = await acount(SourceCall, status="error")
    assert failed_calls == 1
    first_failed = await aget(SourceCall, status="error")
    assert first_failed.adapter == "tavily_news"
    # successful topic still summarized + stored
    assert run.stats["facts_stored"] == 1


async def test_all_cells_failed_fails_run(db, politician, run, summarizer_llm) -> None:
    """SWARM-3: every cell failing → failed run; no profile written."""
    adapters = [
        FakeAdapter(
            "tavily_web",
            ("positions",),
            {"positions": AdapterError("tavily_web", "down")},
        )
    ]
    await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions"],
        run_id=run.pk,
        llm=summarizer_llm,
        adapters=adapters,
    )
    await arefresh(run)
    assert run.status == ResearchRun.Status.FAILED
    assert await acount(PoliticianProfile) == 0


# SWARM-2: timeouts
async def test_cell_timeout_is_isolated(db, politician, run, summarizer_llm) -> None:
    """SWARM-2: a hung cell times out at 45s (shortened here) and is isolated.

    We patch the timeout constant to keep the test fast; semantics unchanged.
    """
    import apps.research.swarm as swarm

    adapters = [
        FakeAdapter("tavily_web", ("positions",), {"positions": _outcome([])}),
        FakeAdapter("tavily_news", ("controversies",), {"controversies": "timeout"}),
    ]
    monkey_timeout = pytest.MonkeyPatch()
    monkey_timeout.setattr(swarm, "CELL_TIMEOUT_SECONDS", 0.05)
    try:
        report = await research_politician(
            PoliticianRef(id=politician.pk, name=politician.name),
            ["positions", "controversies"],
            run_id=run.pk,
            llm=summarizer_llm,
            adapters=adapters,
        )
    finally:
        monkey_timeout.undo()
    await arefresh(run)
    assert report.cells_failed == 1
    assert any("timed out" in err for err in report.cell_errors)
    assert run.status == ResearchRun.Status.DEGRADED


# CACHE-4: the exit criterion
async def test_fresh_cache_skips_adapter_calls(
    db, politician, run, summarizer_llm
) -> None:
    """CACHE-4: researching a fresh politician costs ~zero adapter calls.

    Second run: same topics, records still within TTL → zero fetch calls,
    zero new credits, and the profile is still regenerated from cache.
    """
    adapters_first = [
        FakeAdapter(
            "tavily_web",
            ("positions",),
            {"positions": _outcome([_finding("https://src.example/1")])},
        )
    ]
    await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions"],
        run_id=run.pk,
        llm=summarizer_llm,
        adapters=adapters_first,
    )
    assert await acount(SourceCall) == 1

    run2 = await sync_to_async(ResearchRun.objects.create)(
        politician=politician, topics=["positions"]
    )
    adapters_second = FakeAdapter(
        "tavily_web", ("positions",), {"positions": _outcome([])}
    )
    report = await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions"],
        run_id=run2.pk,
        llm=summarizer_llm,
        adapters=[adapters_second],
    )
    assert adapters_second.calls == []  # zero paid calls — the exit criterion
    assert report.cache_hits == 1
    assert report.cells_total == 1
    await arefresh(run2)
    assert run2.credits == 0
    assert run2.status == ResearchRun.Status.COMPLETED
    # no additional SourceCall rows from the second run
    assert await acount(SourceCall) == 1


async def test_force_refresh_bypasses_cache(
    db, politician, run, summarizer_llm
) -> None:
    """CACHE-4: force_refresh re-fetches even fresh cells."""
    await sync_to_async(SourceRecord.objects.create)(
        politician=politician,
        source_type="tavily_web",
        topic="positions",
        url="https://src.example/old",
        url_hash=SourceRecord.url_hash_of("https://src.example/old"),
        retrieved_at=NOW,
        fresh_until=NOW + TTL_DAYS["tavily_web"],
    )
    adapters = FakeAdapter(
        "tavily_web",
        ("positions",),
        {"positions": _outcome([_finding("https://src.example/new")])},
    )
    report = await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions"],
        force_refresh=True,
        run_id=run.pk,
        llm=summarizer_llm,
        adapters=[adapters],
    )
    assert adapters.calls == ["positions"]
    assert report.cache_hits == 0


# SUMMARIZER-4: LLM failure isolation
async def test_summarizer_error_marks_topic_failed(db, politician, run) -> None:
    """SUMMARIZER-4: StructuredOutputError kills the topic, not the run;
    previous profile stays intact (POLITICIAN-3b)."""
    record = await sync_to_async(_seed_record)(politician)
    profile = await sync_to_async(PoliticianProfile.objects.create)(
        politician=politician, scope="federal", summary="old summary"
    )
    await sync_to_async(Fact.objects.create)(
        profile=profile, topic="positions", claim="old claim", source_record=record
    )
    adapters = [
        FakeAdapter(
            "tavily_web",
            ("positions",),
            {"positions": _outcome([_finding("https://src.example/1")])},
        )
    ]

    # LLM that always returns malformed JSON → StructuredOutputError
    def handler(request: httpx2.Request) -> httpx2.Response:
        return {"status": 200, "body": "{not json"}.get("status") or httpx2.Response(
            200, json=_completion("definitely not json")
        )

    llm = _llm_with(handler)
    report = await research_politician(
        PoliticianRef(id=politician.pk, name=politician.name),
        ["positions"],
        run_id=run.pk,
        llm=llm,
        adapters=adapters,
    )
    await arefresh(run)
    assert report.topics_failed == 1
    assert run.status == ResearchRun.Status.FAILED
    await arefresh(profile)
    assert profile.summary == "old summary"  # POLITICIAN-3b
    assert await acount(Fact, profile=profile) == 1


def _seed_record(politician: Politician) -> SourceRecord:
    return SourceRecord.objects.create(  # type: ignore[unresolved-attribute]
        politician=politician,
        source_type="tavily_web",
        topic="positions",
        url="https://old.example/1",
        url_hash=SourceRecord.url_hash_of("https://old.example/1"),
        retrieved_at=NOW - timedelta(days=1),
        fresh_until=NOW + timedelta(days=1),
    )


def _completion(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
    }


def _llm_with(handler) -> LLMClient:
    return LLMClient(
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        max_retries=0,
    )
