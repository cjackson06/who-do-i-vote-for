"""Summarizer step: persisted records → topic summary + cited facts.

Contract: specs/research.md (SUMMARIZER-*); prompt module follows
specs/llm.md LLM-PROMPT-*.
"""

from dataclasses import dataclass, field

from apps.llm.client import LLMClient
from apps.llm.prompts import research_summarizer
from apps.llm.prompts.research_summarizer import NAME, VERSION
from apps.politicians.models import SourceRecord

from .errors import ResearchError
from .schemas import PoliticianRef, TopicSummary

EXCERPT_LIMIT = 1000


@dataclass
class TopicResult:
    """One topic's summarization outcome."""

    topic: str
    summary: str = ""
    facts: list[tuple[str, str, int]] = field(
        default_factory=list
    )  # claim, quote, src_id
    dropped: int = 0
    failed: bool = False


def _findings_payload(records: list[SourceRecord]) -> list[dict[str, object]]:
    return [
        {
            "url": str(record.url),
            "title": str(record.title),
            "content": str(record.content)[:EXCERPT_LIMIT],
            "first_hand": bool(record.first_hand),
            "published_date": (
                str(record.published_date) if record.published_date else None
            ),
        }
        for record in records
    ]


async def summarize_topic(
    llm: LLMClient,
    ref: PoliticianRef,
    topic: str,
    records: list[SourceRecord],
) -> TopicResult:
    """SUMMARIZER-1/2: one structured call; citations validated in-memory.

    LLM errors (StructuredOutputError, RoleNotConfigured, transport) propagate
    to the swarm, which marks the topic failed (SUMMARIZER-4).
    """
    messages = research_summarizer.build_messages(
        politician=ref.name,
        topic=topic,
        findings=_findings_payload(records),
    )
    summary = await llm.complete(
        "summarizer",
        messages,
        schema=TopicSummary,
        prompt_name=NAME,
        prompt_version=VERSION,
    )
    if not isinstance(summary, TopicSummary):  # pragma: no cover - typing guard
        raise ResearchError(f"summarizer returned unexpected type {type(summary)!r}")

    # SUMMARIZER-3: citations must match persisted records from this run
    by_url: dict[str, int] = {
        str(record.url): int(record.pk or 0) for record in records
    }
    result = TopicResult(topic=topic, summary=summary.summary)
    for draft in summary.facts:
        source_id = by_url.get(draft.source_url)
        if source_id is None:
            result.dropped += 1
            continue
        result.facts.append((draft.claim, draft.quote, source_id))
    return result


def profile_summary(topic_results: list[TopicResult]) -> str:
    """SUMMARIZER-5: deterministic join under topic headers."""
    sections = []
    for result in topic_results:
        sections.append(f"## {result.topic}\n{result.summary}")
    return "\n\n".join(sections)
