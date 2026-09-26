"""Research schemas: JSON-safe boundaries (specs/research.md, Interfaces)."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class PoliticianRef(BaseModel):
    """JSON-safe politician identity passed across the task boundary."""

    id: int
    name: str
    party: str = ""
    office: str = ""
    state: str = ""
    fec_candidate_id: str | None = None


class RawFinding(BaseModel):
    """One first-hand-eligible finding returned by an adapter."""

    url: str
    title: str = ""
    content: str = ""
    first_hand: bool = False
    published_date: date | None = None
    score: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CallRecord(BaseModel):
    """One outbound HTTP call made by an adapter (feeds SourceCall)."""

    endpoint: str
    query: str = ""
    credits: int = 0
    latency_ms: int = 0
    status: str = "ok"  # "ok" | "error"
    error: str = ""


class FetchOutcome(BaseModel):
    """What a fetch returns: findings plus its call log entries."""

    findings: list[RawFinding] = Field(default_factory=list)
    calls: list[CallRecord] = Field(default_factory=list)


class FactDraft(BaseModel):
    """A summarizer-proposed fact with its floating citation."""

    claim: str
    quote: str = ""
    source_url: str


class TopicSummary(BaseModel):
    """LLM structured output for one topic (SUMMARIZER-1)."""

    summary: str
    facts: list[FactDraft] = Field(default_factory=list)
