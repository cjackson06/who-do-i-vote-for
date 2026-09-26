"""Tavily search adapter (specs/research.md, TAVILY-*)."""

import asyncio
import time
from datetime import date
from typing import Any
from urllib.parse import urlparse

import httpx2

from .. import settings as research_settings
from ..errors import AdapterError
from ..schemas import CallRecord, FetchOutcome, PoliticianRef, RawFinding
from .base import ensure_topic, is_retryable, redact_message, sanitize_url

MAX_RESULTS = 10
SEARCH_DEPTH = "basic"  # 1 credit per request (TAVILY-6)
CHUNKS_PER_SOURCE = 3
REQUEST_TIMEOUT = 15.0
RETRY_BACKOFF_SECONDS = 1.2
HTTP_OK = 400  # status < HTTP_OK is a success

# TAVILY-4: adapter-side filtering — aggregators/opinion-first hosts are
# excluded at request time; changes are spec + code + test changes together.
EXCLUDE_DOMAINS: tuple[str, ...] = (
    "reddit.com",
    "quora.com",
    "medium.com",
    "wikipedia.org",
    "ballotpedia.org",
    "procon.org",
    "ontheissues.org",
    "votesmart.org",
    "yelp.com",
    "change.org",
    "facebook.com",
    "x.com",
    "twitter.com",
)

# TAVILY-3: first-hand allowlist — government TLDs are official records;
# everything else starts False and relies on the summarizer prompt rules.
FIRST_HAND_TLDS: tuple[str, ...] = (".gov", ".mil")

# TAVILY-2/TAVILY-4: per-instance configuration; query templates per topic.
QUERY_TEMPLATES: dict[str, str] = {
    "positions": "{name} policy positions public statements",
    "voting_record": "{name} voting record legislation bills",
    "controversies": "{name} controversy statement response",
}


class TavilyAdapter:
    """Cited web/news search via POST /search (Bearer key)."""

    def __init__(
        self,
        http_client: httpx2.AsyncClient,
        *,
        name: str,
        topics: tuple[str, ...],
        tavily_topic: str,
        time_range: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        exclude_domains: tuple[str, ...] | None = None,
    ) -> None:
        self.http_client = http_client
        self.name = name
        self.topics = topics
        self.tavily_topic = tavily_topic
        self.time_range = time_range
        self.api_key = api_key or research_settings.tavily_api_key()
        self.base_url = (base_url or research_settings.tavily_base_url()).rstrip("/")
        self.exclude_domains = (
            exclude_domains if exclude_domains is not None else EXCLUDE_DOMAINS
        )
        if not self.api_key:
            raise AdapterError(self.name, "TAVILY_API_KEY is not configured")

    async def fetch(self, ref: PoliticianRef, topic: str) -> FetchOutcome:
        ensure_topic(self.name, topic, self.topics)
        template = QUERY_TEMPLATES.get(topic)
        if template is None:
            raise AdapterError(self.name, f"no query template for topic {topic!r}")

        body: dict[str, Any] = {
            "query": template.format(name=ref.name),
            "topic": self.tavily_topic,  # TAVILY-2
            "search_depth": SEARCH_DEPTH,
            "chunks_per_source": CHUNKS_PER_SOURCE,
            "max_results": MAX_RESULTS,
            "exclude_domains": list(self.exclude_domains),  # TAVILY-4
        }
        if self.time_range:
            body["time_range"] = self.time_range

        endpoint = f"{self.base_url}/search"
        started = time.perf_counter()
        response = await self._post(endpoint, body)
        latency_ms = int((time.perf_counter() - started) * 1000)

        try:
            payload = response.json()
        except ValueError as exc:
            raise AdapterError(self.name, f"invalid JSON response: {exc}") from exc

        findings = [self._finding(item) for item in payload.get("results", [])]
        call = CallRecord(
            endpoint=sanitize_url(endpoint),
            query=body["query"],
            credits=1,  # TAVILY-6: basic search = 1 credit
            latency_ms=latency_ms,
            status="ok",
        )
        return FetchOutcome(findings=findings, calls=[call])

    async def _post(self, endpoint: str, body: dict[str, Any]) -> httpx2.Response:
        """TAVILY-5: one retry on 429/5xx; other 4xx fail immediately."""
        headers = {"Authorization": f"Bearer {self.api_key}"}  # TAVILY-1
        for attempt in (1, 2):
            started = time.perf_counter()
            try:
                response = await self.http_client.post(
                    endpoint,
                    json=body,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except httpx2.RequestError as exc:
                if attempt == 1:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                raise AdapterError(
                    self.name,
                    redact_message(f"transport error: {exc}"),
                ) from exc
            latency = int((time.perf_counter() - started) * 1000)
            if response.status_code < HTTP_OK:
                return response
            if is_retryable(response.status_code) and attempt == 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue
            raise AdapterError(
                self.name,
                redact_message(
                    f"HTTP {response.status_code} after {attempt} attempt(s) "
                    f"({latency}ms): {response.text[:200]}"
                ),
            )
        raise AdapterError(self.name, "unreachable retry state")  # pragma: no cover

    def _finding(self, item: dict[str, Any]) -> RawFinding:
        """TAVILY-3: map a result entry; first-hand via official TLD allowlist."""
        url = str(item.get("url", ""))
        published: date | None = None
        raw_date = item.get("published_date")
        if raw_date:
            try:
                published = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                published = None
        host = urlparse(url).netloc.lower()
        first_hand = any(host.endswith(tld) for tld in FIRST_HAND_TLDS)
        return RawFinding(
            url=url,
            title=str(item.get("title", "")),
            content=str(item.get("content", "")),
            first_hand=first_hand,
            published_date=published,
            score=item.get("score"),
        )
