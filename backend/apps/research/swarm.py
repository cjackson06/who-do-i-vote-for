"""Swarm orchestrator: fan-out fetch → persist → summarize → profile.

Contract: specs/research.md (SWARM-*) + specs/politicians.md (CACHE-4,
POLITICIAN-3).
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx2
from asgiref.sync import sync_to_async
from django.db.models import Manager

from apps.llm.client import LLMClient
from apps.politicians.cache import CacheCell, fresh_cells, fresh_until
from apps.politicians.models import Politician, SourceRecord
from apps.politicians.services import NewFact, replace_profile

from .adapters.base import SourceAdapter
from .errors import AdapterError
from .models import ResearchRun, SourceCall
from .registry import available_adapters
from .schemas import CallRecord, FetchOutcome, PoliticianRef
from .summarize import TopicResult, profile_summary, summarize_topic
from .topics import TOPICS

CELL_TIMEOUT_SECONDS = 45.0


class CellResult:
    """Outcome of one (adapter, topic) cell execution."""

    def __init__(
        self,
        adapter_name: str,
        topic: str,
        outcome: FetchOutcome | None = None,
        error: str = "",
        *,
        timed_out: bool = False,
    ) -> None:
        self.adapter_name = adapter_name
        self.topic = topic
        self.outcome = outcome
        self.error = error
        self.timed_out = timed_out

    @property
    def ok(self) -> bool:
        return self.outcome is not None and not self.error


@dataclass
class SwarmReport:
    """Aggregated outcome for the run row."""

    cells_total: int = 0
    cells_ok: int = 0
    cells_failed: int = 0
    cache_hits: int = 0
    findings: int = 0
    topics_failed: int = 0
    facts_stored: int = 0
    facts_dropped: int = 0
    topic_results: list[TopicResult] = field(default_factory=list)
    cell_errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.cells_total and self.cells_failed == self.cells_total:
            return ResearchRun.Status.FAILED
        if self.topic_results and self.topics_failed == len(self.topic_results):
            return ResearchRun.Status.FAILED
        if self.cells_failed or self.topics_failed:
            return ResearchRun.Status.DEGRADED
        return ResearchRun.Status.COMPLETED

    def as_stats(self) -> dict[str, Any]:
        return {
            "cells_total": self.cells_total,
            "cells_ok": self.cells_ok,
            "cells_failed": self.cells_failed,
            "cache_hits": self.cache_hits,
            "findings": self.findings,
            "topics_failed": self.topics_failed,
            "facts_stored": self.facts_stored,
            "facts_dropped": self.facts_dropped,
            "cell_errors": self.cell_errors,
        }


async def research_politician(
    ref: PoliticianRef,
    topics: list[str],
    *,
    force_refresh: bool = False,
    run_id: int,
    llm: LLMClient | None = None,
    http_client: httpx2.AsyncClient | None = None,
    adapters: list[SourceAdapter] | None = None,
) -> SwarmReport:
    """Execute the research plan for one politician (SWARM-1..6)."""
    llm = llm or LLMClient()
    politician_id = ref.id
    topics = [t for t in TOPICS if t in topics] or list(TOPICS)

    if adapters is None:
        adapters = available_adapters(http_client)

    # SWARM-1: plan cells; skip fresh ones (CACHE-4)
    fresh = await sync_to_async(fresh_cells)(politician_id)
    cells: list[tuple[SourceAdapter, str]] = []
    cache_hits = 0
    for adapter in adapters:
        for topic in topics:
            if topic not in adapter.topics:
                continue
            if not force_refresh and CacheCell(adapter.name, topic) in fresh:
                cache_hits += 1
            else:
                cells.append((adapter, topic))

    report = SwarmReport(cache_hits=cache_hits, cells_total=len(cells) + cache_hits)
    if not report.cells_total:
        report.cell_errors.append("no source adapters configured; nothing to run")
        await sync_to_async(_finalize_run)(run_id, report)
        return report

    # SWARM-2/3: concurrent cells, per-cell timeout, partial failure tolerated
    async def run_cell(adapter: SourceAdapter, topic: str) -> CellResult:
        try:
            async with asyncio.timeout(CELL_TIMEOUT_SECONDS):
                outcome = await adapter.fetch(ref, topic)
        except TimeoutError:
            return CellResult(
                adapter.name, topic, error="cell timed out", timed_out=True
            )
        except AdapterError as exc:
            return CellResult(adapter.name, topic, error=str(exc))
        except Exception as exc:
            return CellResult(adapter.name, topic, error=f"{type(exc).__name__}: {exc}")
        return CellResult(adapter.name, topic, outcome=outcome)

    results = list(
        await asyncio.gather(*(run_cell(adapter, topic) for adapter, topic in cells))
    )

    # SWARM-4: persist records + call rows per cell
    now = await sync_to_async(_utcnow)()
    for result in results:
        if result.outcome is not None:
            await sync_to_async(_persist_cell)(politician_id, result, now)
        await sync_to_async(_persist_calls)(run_id, result)
        if result.ok:
            report.cells_ok += 1
        else:
            report.cells_failed += 1
            report.cell_errors.append(
                f"{result.adapter_name}/{result.topic}: {result.error}"
            )
    report.findings = sum(
        len(result.outcome.findings) for result in results if result.outcome
    )

    # Summarize every topic in the run over the cell's current records
    for topic in topics:
        records = await sync_to_async(_topic_records)(politician_id, topic)
        if not records:
            report.cell_errors.append(f"no records to summarize: {topic}")
            continue
        try:
            topic_result = await summarize_topic(llm, ref, topic, records)
        except Exception as exc:
            report.topic_results.append(TopicResult(topic=topic, failed=True))
            report.topics_failed += 1
            report.cell_errors.append(f"summarizer/{topic}: {exc}")
            continue
        report.topic_results.append(topic_result)
        report.facts_dropped += topic_result.dropped

    # POLITICIAN-3: atomic profile regeneration with validated facts (3b:
    # only when the summarizer produced content)
    if any(not result.failed for result in report.topic_results):
        new_facts: list[NewFact] = []
        for topic_result in report.topic_results:
            if topic_result.failed:
                continue
            new_facts.extend(
                NewFact(
                    topic=topic_result.topic,
                    claim=claim,
                    quote=quote,
                    source_record_id=source_id,
                )
                for claim, quote, source_id in topic_result.facts
            )
        report.facts_stored = len(new_facts)
        succeeded = [r for r in report.topic_results if not r.failed]
        await sync_to_async(replace_profile)(
            politician_id,
            "federal",
            profile_summary(succeeded),
            new_facts,
            research_run_id=run_id,
        )

    await sync_to_async(_finalize_run)(run_id, report)
    return report


def _utcnow() -> datetime:
    from django.utils import timezone

    return timezone.now()


def _persist_cell(
    politician_id: int, result: CellResult, now: datetime
) -> list[SourceRecord]:
    """SWARM-4: one SourceRecord per finding, deduped by cell identity."""
    if result.outcome is None:  # callers only persist cells with outcomes
        return []
    manager = SourceRecord.objects  # type: ignore[unresolved-attribute]
    records: list[SourceRecord] = []
    for finding in result.outcome.findings:
        if not finding.url:
            continue
        record, _ = manager.update_or_create(
            politician_id=politician_id,
            source_type=result.adapter_name,
            topic=result.topic,
            url_hash=SourceRecord.url_hash_of(finding.url),
            defaults={
                "url": finding.url,
                "title": finding.title,
                "content": finding.content,
                "first_hand": finding.first_hand,
                "published_date": finding.published_date,
                "retrieved_at": now,
                "fresh_until": fresh_until(result.adapter_name, now=now),
            },
        )
        records.append(record)
    return records


def _persist_calls(run_id: int, result: CellResult) -> None:
    """RUN-3/SWARM-4: one SourceCall row per outbound HTTP call (ok or error)."""
    calls: list[CallRecord] = []
    if result.outcome is not None:
        calls.extend(result.outcome.calls)
    if not result.ok and not calls:
        # Adapter-level failure without call records (e.g. candidate not
        # found): still record the failed cell attempt for observability.
        calls.append(
            CallRecord(
                endpoint=f"adapter://{result.adapter_name}",
                query=result.topic,
                credits=0,
                latency_ms=0,
                status="error",
                error=result.error,
            )
        )
    _calls().bulk_create(
        [
            SourceCall(
                run_id=run_id,
                adapter=result.adapter_name,
                topic=result.topic,
                endpoint=call.endpoint[:500],
                query=call.query[:500],
                credits=call.credits,
                latency_ms=call.latency_ms,
                status=call.status,
                error=call.error,
            )
            for call in calls
        ]
    )


def _topic_records(politician_id: int, topic: str) -> list[SourceRecord]:
    manager = SourceRecord.objects  # type: ignore[unresolved-attribute]
    return list(
        manager.filter(politician_id=politician_id, topic=topic).order_by(
            "-first_hand", "-retrieved_at"
        )
    )


def _finalize_run(run_id: int, report: SwarmReport) -> None:
    """RUN-2/RUN-4: terminal status, stats, credits."""
    run = _runs().filter(pk=run_id).first()
    if run is None:
        return
    run.status = report.status
    run.stats = report.as_stats()
    run.credits = sum(call.credits for call in run.source_calls.all())
    run.finished_at = _utcnow()
    if report.cell_errors:
        run.error = "\n".join(report.cell_errors)[:2000]
    run.save(update_fields=["status", "stats", "credits", "finished_at", "error"])


def load_ref(politician_id: int) -> PoliticianRef:
    """JSON-safe ref for the task boundary (adapters never touch ORM)."""
    politician = Politician.objects.get(  # type: ignore[unresolved-attribute]
        pk=politician_id
    )
    return PoliticianRef(
        id=politician.pk,
        name=politician.name,
        party=politician.party,
        office=politician.office,
        state=politician.state,
        fec_candidate_id=politician.fec_candidate_id or None,
    )


def _runs() -> Manager[ResearchRun]:
    return ResearchRun.objects  # type: ignore[unresolved-attribute]


def _calls() -> Manager[SourceCall]:
    return SourceCall.objects  # type: ignore[unresolved-attribute]
