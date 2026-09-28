"""FEC campaign-finance adapter (specs/research.md, FEC-*)."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx2

from .. import settings as research_settings
from ..errors import AdapterError
from ..schemas import CallRecord, FetchOutcome, PoliticianRef, RawFinding
from .base import is_retryable, redact_message, sanitize_url

MAX_COMMITTEES = 3
PER_PAGE = 100
REQUEST_TIMEOUT = 30.0
RETRY_BACKOFF_SECONDS = 2.0
HTTP_OK = 400  # status < HTTP_OK is a success

TOPIC = "donations"
NAME = "fec"


def current_cycle(now: datetime | None = None) -> int:
    """FEC two-year transaction period for 'now' (even years)."""
    year = (now or datetime.now(tz=UTC)).year
    return year + (year % 2)


def normalize_name(name: str) -> str:
    """Uppercase, drop punctuation/commas; 'HARRIS, KAMALA' -> HARRIS KAMALA."""
    cleaned = name.upper()
    for char in (".", ",", "-", "'"):
        cleaned = cleaned.replace(char, " ")
    return " ".join(cleaned.split())


def candidate_match_score(ref: PoliticianRef, candidate: dict[str, Any]) -> float:
    """Deterministic best-match scoring (FEC-1): name tokens, then state/party."""
    candidate_name = normalize_name(str(candidate.get("name", "")))
    ref_tokens = normalize_name(ref.name).split()
    if not ref_tokens:
        return 0.0
    score = 0.0
    hits = sum(1 for token in ref_tokens if token in candidate_name)
    if hits == len(ref_tokens):
        score += 2.0
    elif ref_tokens[-1] in candidate_name:
        score += 1.0
    else:
        return 0.0
    candidate_state = str(candidate.get("state", "") or "").upper()
    if ref.state and candidate_state == ref.state.upper():
        score += 0.5
    party = str(candidate.get("party_full", "") or candidate.get("party", "") or "")
    if ref.party and party and ref.party.upper() in party.upper():
        score += 0.5
    return score


class FECAdapter:
    """Federal campaign-finance records; always first-hand (FEC-5)."""

    name = NAME
    topics = (TOPIC,)

    def __init__(
        self,
        http_client: httpx2.AsyncClient,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        cycle: int | None = None,
    ) -> None:
        self.http_client = http_client
        if api_key is not None:
            self.api_key = api_key
            self.base_url = (base_url or research_settings.fec_base_url()).rstrip("/")
        else:
            config = research_settings.fec_settings()
            self.api_key = config.api_key
            self.base_url = (base_url or config.base_url).rstrip("/")
        self.cycle = cycle or current_cycle()
        self._resolved: dict[str, str] = {}  # name -> candidate_id (per run)
        self._last_resolution_call = CallRecord(
            endpoint=sanitize_url(f"{self.base_url}/candidates/search/"),
            query="candidates/search (cached)",
            credits=0,
            latency_ms=0,
            status="ok",
        )

    async def resolve_candidate(self, ref: PoliticianRef) -> str:
        """FEC-1: best-match candidate id; AdapterError when not found."""
        if ref.fec_candidate_id:
            return ref.fec_candidate_id
        if ref.name in self._resolved:
            return self._resolved[ref.name]

        started = time.perf_counter()
        response = await self._get(
            "/candidates/search/",
            {"q": ref.name, "per_page": PER_PAGE},
            query_label=f"candidates/search q={ref.name!r}",
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = _json(response, self.name)
        results = payload.get("results", [])

        best: tuple[float, dict[str, Any]] | None = None
        for candidate in results:
            score = candidate_match_score(ref, candidate)
            if best is None or score > best[0]:
                best = (score, candidate)
        if best is None or best[0] < 1.0:
            raise AdapterError(
                self.name, f"no federal candidate match for {ref.name!r}"
            )

        candidate_id = str(best[1].get("id", ""))
        if not candidate_id:
            raise AdapterError(self.name, "candidate result missing id")
        self._resolved[ref.name] = candidate_id
        self._last_resolution_call = CallRecord(
            endpoint=sanitize_url(str(response.request.url)),
            query=f"candidates/search q={ref.name!r}",
            credits=0,  # FEC is free (FEC-3)
            latency_ms=latency_ms,
            status="ok",
        )
        return candidate_id

    async def fetch(self, ref: PoliticianRef, topic: str) -> FetchOutcome:
        if topic != TOPIC:
            raise AdapterError(self.name, f"topic {topic!r} not covered")

        candidate_id = await self.resolve_candidate(ref)
        findings: list[RawFinding] = []
        calls: list[CallRecord] = [self._last_resolution_call]

        committees = await self._committees(candidate_id)
        calls.extend(committees.calls)
        for committee in committees.findings[:MAX_COMMITTEES]:
            committee_id = str(committee.meta["committee_id"])
            totals = await self._totals(committee_id)
            calls.extend(totals.calls)
            if not totals.findings:
                continue
            totals_finding = totals.findings[0]
            findings.append(
                RawFinding(
                    url=committee_fec_url(committee_id),
                    title=f"{committee.title} (cycle {self.cycle})",
                    content=totals_finding.content,
                    first_hand=True,  # FEC-5: official agency records
                    meta={**totals_finding.meta, "committee_id": committee_id},
                )
            )
        return FetchOutcome(findings=findings, calls=calls)

    async def _committees(self, candidate_id: str) -> FetchOutcome:
        """Principal campaign committees for the candidate (FEC-2)."""
        started = time.perf_counter()
        response = await self._get(
            f"/candidate/{candidate_id}/committees/history/",
            {"cycle": self.cycle},
            query_label=f"committees candidate={candidate_id}",
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = _json(response, self.name)
        findings = [
            RawFinding(
                url="",
                title=str(item.get("name", "")),
                content="",
                first_hand=True,
                meta={
                    "committee_id": str(item.get("committee_id", "")),
                    "designation": str(item.get("designation", "")),
                },
            )
            for item in payload.get("results", [])
            if item.get("committee_id")
        ]
        return FetchOutcome(
            findings=findings,
            calls=[
                CallRecord(
                    endpoint=sanitize_url(str(response.request.url)),
                    query=f"committees candidate={candidate_id}",
                    credits=0,
                    latency_ms=latency_ms,
                    status="ok",
                )
            ],
        )

    async def _totals(self, committee_id: str) -> FetchOutcome:
        """Cycle financial totals for one committee (FEC-2)."""
        started = time.perf_counter()
        response = await self._get(
            f"/committee/{committee_id}/totals/",
            {"cycle": self.cycle},
            query_label=f"totals committee={committee_id}",
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = _json(response, self.name)
        results = payload.get("results", [])
        if not results:
            return FetchOutcome(calls=[_fec_call(response, latency_ms, committee_id)])
        totals = results[0]
        receipts = _money(totals.get("receipts"))
        individual = _money(totals.get("individual_itemized_contributions"))
        content = (
            f"Cycle {self.cycle} totals for committee "
            f"{totals.get('committee_name', committee_id)}: total receipts "
            f"${receipts:,.2f}, itemized individual contributions "
            f"${individual:,.2f} (source: FEC official records)."
        )
        return FetchOutcome(
            findings=[
                RawFinding(
                    url=committee_fec_url(committee_id),
                    title=str(totals.get("committee_name", committee_id)),
                    content=content,
                    first_hand=True,
                    meta={
                        "receipts": receipts,
                        "individual_contributions": individual,
                        "cycle": self.cycle,
                    },
                )
            ],
            calls=[_fec_call(response, latency_ms, committee_id)],
        )

    async def _get(
        self, path: str, params: dict[str, Any], *, query_label: str
    ) -> httpx2.Response:
        """FEC-3: api_key as query param; one retry on 429/5xx."""
        all_params = {**params, "api_key": self.api_key, "per_page": PER_PAGE}
        for attempt in (1, 2):
            try:
                response = await self.http_client.get(
                    f"{self.base_url}{path}",
                    params=all_params,
                    timeout=REQUEST_TIMEOUT,
                )
            except httpx2.RequestError as exc:
                if attempt == 1:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                raise AdapterError(
                    self.name, redact_message(f"transport error: {exc}")
                ) from exc
            if response.status_code < HTTP_OK:
                return response
            if is_retryable(response.status_code) and attempt == 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue
            raise AdapterError(
                self.name,
                redact_message(
                    f"HTTP {response.status_code} for {query_label} after "
                    f"{attempt} attempt(s): {response.text[:200]}"
                ),
            )
        raise AdapterError(self.name, "unreachable retry state")  # pragma: no cover


def _fec_call(
    response: httpx2.Response, latency_ms: int, committee_or_q: str
) -> CallRecord:
    return CallRecord(
        endpoint=sanitize_url(str(response.request.url)),
        query=f"FEC call {committee_or_q}",
        credits=0,
        latency_ms=latency_ms,
        status="ok",
    )


def _json(response: httpx2.Response, adapter: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AdapterError(adapter, f"invalid JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise AdapterError(adapter, "unexpected response shape")
    return payload


def _money(value: float | str | None) -> float:
    if value is None:
        return 0.0
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def committee_fec_url(committee_id: str) -> str:
    """Public permalink for a committee's filings (first-hand source)."""
    return f"https://www.fec.gov/data/committee/{committee_id}/"
