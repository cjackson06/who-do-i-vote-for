"""Tavily adapter — contract: specs/research.md (TAVILY-*)."""

import json

import httpx2
import pytest

from apps.research.adapters.tavily import (
    EXCLUDE_DOMAINS,
    FIRST_HAND_TLDS,
    TavilyAdapter,
)
from apps.research.errors import AdapterError
from apps.research.schemas import PoliticianRef

REF = PoliticianRef(id=1, name="Jane Doe", party="DEM", office="Senate", state="PA")


def _search_payload(*results: dict) -> dict:
    return {
        "results": list(results),
        "response_time": 0.4,
        "request_id": "req-test",
    }


def _result(url: str, title: str = "t", content: str = "c", **extra) -> dict:
    return {"url": url, "title": title, "content": content, **extra}


@pytest.fixture
def client_factory():
    """Build (adapter, captured_requests) with a scripted handler."""

    def make(
        responses: list[httpx2.Response | Exception],
        *,
        name: str = "tavily_web",
        topics: tuple[str, ...] = ("positions", "voting_record"),
        tavily_topic: str = "general",
        time_range: str | None = None,
        api_key: str = "test-key",
        base_url: str = "https://api.tavily.test",
    ) -> tuple[TavilyAdapter, list[httpx2.Request]]:
        requests: list[httpx2.Request] = []
        queue = list(responses)

        def handler(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        transport = httpx2.MockTransport(handler)
        client = httpx2.AsyncClient(transport=transport)
        adapter = TavilyAdapter(
            client,
            name=name,
            topics=topics,
            tavily_topic=tavily_topic,
            time_range=time_range,
            api_key=api_key,
            base_url=base_url,
        )
        return adapter, requests

    return make


# TAVILY-1 / TAVILY-2
async def test_request_shape_and_headers(client_factory) -> None:
    """TAVILY-1/-2: POST /search, Bearer key, body params incl. excludes."""
    adapter, requests = client_factory([httpx2.Response(200, json=_search_payload())])
    outcome = await adapter.fetch(REF, "positions")

    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.tavily.test/search"
    assert request.headers["Authorization"] == "Bearer test-key"

    body = json.loads(request.content)
    assert body["query"] == "Jane Doe policy positions public statements"
    assert body["topic"] == "general"
    assert body["search_depth"] == "basic"
    assert body["chunks_per_source"] == 3
    assert body["max_results"] == 10
    assert body["exclude_domains"] == list(EXCLUDE_DOMAINS)
    assert "time_range" not in body  # web variant has none

    assert [f.url for f in outcome.findings] == []
    assert len(outcome.calls) == 1
    call = outcome.calls[0]
    assert call.credits == 1  # TAVILY-6
    assert call.status == "ok"
    assert "test-key" not in call.endpoint  # TAVILY-7


async def test_news_variant_uses_news_topic_and_time_range(client_factory) -> None:
    """TAVILY-2: tavily_news maps topic=news + time_range=year."""
    adapter, requests = client_factory(
        [httpx2.Response(200, json=_search_payload())],
        name="tavily_news",
        topics=("controversies",),
        tavily_topic="news",
        time_range="year",
    )
    await adapter.fetch(REF, "controversies")
    body = json.loads(requests[0].content)
    assert body["topic"] == "news"
    assert body["time_range"] == "year"
    assert body["query"] == "Jane Doe controversy statement response"


# TAVILY-3
async def test_first_hand_heuristic(client_factory) -> None:
    """TAVILY-3: .gov/.mil hosts → first_hand; others False."""
    adapter, _ = client_factory(
        [
            httpx2.Response(
                200,
                json=_search_payload(
                    _result("https://www.senate.gov/statement", content="official"),
                    _result("https://news.example.com/story"),
                ),
            )
        ]
    )
    outcome = await adapter.fetch(REF, "positions")
    hands = {f.url: f.first_hand for f in outcome.findings}
    assert hands["https://www.senate.gov/statement"] is True
    assert hands["https://news.example.com/story"] is False


async def test_published_date_parsing_and_meta_defaults(client_factory) -> None:
    """TAVILY-3: published_date parsed tolerantly; unknown fields default."""
    adapter, _ = client_factory(
        [
            httpx2.Response(
                200,
                json=_search_payload(
                    _result(
                        "https://a.example/1",
                        published_date="2026-09-01T08:00:00Z",
                        score=0.93,
                    ),
                    _result("https://a.example/2", published_date="not-a-date"),
                    _result("https://a.example/3"),
                ),
            )
        ]
    )
    from datetime import date

    outcome = await adapter.fetch(REF, "positions")
    first, second, third = outcome.findings
    assert first.published_date == date(2026, 9, 1)
    assert first.score == 0.93
    assert second.published_date is None
    assert third.title == "t"  # defaults intact


# TAVILY-4
async def test_exclude_domains_sent(client_factory) -> None:
    """TAVILY-4: denylist constant rides on every request."""
    adapter, requests = client_factory([httpx2.Response(200, json=_search_payload())])
    await adapter.fetch(REF, "voting_record")
    body = json.loads(requests[0].content)
    assert "reddit.com" in body["exclude_domains"]
    assert "wikipedia.org" in body["exclude_domains"]


# TAVILY-5
async def test_429_retried_once_then_success(client_factory, monkeypatch) -> None:
    """TAVILY-5: 429 → one retry → success; two HTTP calls recorded as one."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("apps.research.adapters.tavily.asyncio.sleep", fake_sleep)
    adapter, requests = client_factory(
        [
            httpx2.Response(429, json={"detail": "rate limited"}),
            httpx2.Response(200, json=_search_payload(_result("https://x.example/a"))),
        ]
    )
    outcome = await adapter.fetch(REF, "positions")
    assert len(requests) == 2
    assert sleeps == [1.2]
    assert len(outcome.calls) == 1  # one cell-level call record
    assert outcome.calls[0].status == "ok"


async def test_429_twice_raises_adapter_error(client_factory, monkeypatch) -> None:
    """TAVILY-5: second 429 → AdapterError; no key leakage in message."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("apps.research.adapters.tavily.asyncio.sleep", fake_sleep)
    adapter, requests = client_factory(
        [
            httpx2.Response(429, json={"detail": "rate limited"}),
            httpx2.Response(429, json={"detail": "still limited"}),
        ]
    )
    with pytest.raises(AdapterError, match="HTTP 429"):
        await adapter.fetch(REF, "positions")
    assert len(requests) == 2
    assert sleeps == [1.2]


async def test_401_no_retry(client_factory) -> None:
    """TAVILY-5: 401/403 → immediate AdapterError (bad key), no retry."""
    adapter, requests = client_factory(
        [httpx2.Response(401, json={"detail": "unauthorized"})]
    )
    with pytest.raises(AdapterError, match="HTTP 401"):
        await adapter.fetch(REF, "positions")
    assert len(requests) == 1


async def test_transport_error_retries_then_fails(client_factory, monkeypatch) -> None:
    """TAVILY-5: network error → one retry → AdapterError."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("apps.research.adapters.tavily.asyncio.sleep", fake_sleep)
    adapter, requests = client_factory(
        [
            httpx2.ConnectError("conn refused"),
            httpx2.ConnectError("conn refused"),
        ]
    )
    with pytest.raises(AdapterError, match="transport error"):
        await adapter.fetch(REF, "positions")
    assert len(requests) == 2


def test_first_hand_tlds_constant() -> None:
    """TAVILY-3: allowlist is the government TLDs only."""
    assert FIRST_HAND_TLDS == (".gov", ".mil")
