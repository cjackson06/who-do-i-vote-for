"""FEC adapter — contract: specs/research.md (FEC-*)."""

from datetime import UTC

import httpx2
import pytest

from apps.research.adapters.fec import (
    FECAdapter,
    candidate_match_score,
    committee_fec_url,
    current_cycle,
    normalize_name,
)
from apps.research.errors import AdapterError
from apps.research.schemas import PoliticianRef

REF = PoliticianRef(id=1, name="Jane Doe", party="DEM", office="Senate", state="PA")


def _search_response(hits: list[dict]) -> httpx2.Response:
    return httpx2.Response(200, json={"results": hits})


def _candidate(
    cid: str, name: str, state: str = "PA", party: str = "Democratic"
) -> dict:
    return {
        "id": cid,
        "name": name,
        "state": state,
        "party_full": party,
    }


@pytest.fixture
def client_factory():
    """Build (adapter, requests) with a route-mapped fake FEC."""

    def make(
        routes: dict[str, list[httpx2.Response | Exception]],
        *,
        cycle: int = 2026,
        api_key: str = "test-fec-key",
        base_url: str = "https://api.fec.test/v1",
    ) -> tuple[FECAdapter, list[httpx2.Request]]:
        requests: list[httpx2.Request] = []

        def handler(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            url = str(request.url)
            for path, responses in routes.items():
                if path in url:
                    item = responses.pop(0)
                    if isinstance(item, Exception):
                        raise item
                    return item
            return httpx2.Response(404, json={"detail": f"unrouted {url}"})

        transport = httpx2.MockTransport(handler)
        client = httpx2.AsyncClient(transport=transport)
        adapter = FECAdapter(client, api_key=api_key, base_url=base_url, cycle=cycle)
        return adapter, requests

    return make


# FEC-1: scoring
def test_normalize_name() -> None:
    """FEC-1: normalization strips case/punctuation; 'DOE, JANE A' aligned."""
    assert normalize_name("HARRIS, KAMALA D.") == "HARRIS KAMALA D"


def test_candidate_match_scoring() -> None:
    """FEC-1: token match + state/party bonuses; non-match scores 0."""
    hit = _candidate("S2PADOE00", "DOE, JANE")
    assert candidate_match_score(REF, hit) == 3.0  # name(2) + state(.5) + party(.5)
    assert candidate_match_score(REF, _candidate("S1NYXYZ00", "XYZ, ORB")) == 0.0
    partial = candidate_match_score(REF, _candidate("H8DOE00", "DOE, BOB"))
    assert 1.0 <= partial < 3.0  # surname-only: ranked below full-name match


def test_current_cycle_parity() -> None:
    """FEC-2: cycle rounds up to even years."""
    from datetime import datetime

    assert current_cycle(datetime(2026, 3, 1, tzinfo=UTC)) == 2026
    assert current_cycle(datetime(2027, 3, 1, tzinfo=UTC)) == 2028


# FEC-1: resolution flow
async def test_resolve_candidate_best_match(client_factory) -> None:
    """FEC-1: best match chosen; id returned; no ORM touched."""
    adapter, requests = client_factory(
        {
            "/candidates/search/": [
                _search_response(
                    [
                        _candidate("S1NYXYZ00", "XYZ, ORB", state="NY"),
                        _candidate("S2PADOE00", "DOE, JANE"),
                    ]
                )
            ]
        }
    )
    candidate_id = await adapter.resolve_candidate(REF)
    assert candidate_id == "S2PADOE00"
    request = requests[0]
    assert "q=Jane+Doe" in str(request.url) or "q=Jane%20Doe" in str(request.url)
    assert "api_key=test-fec-key" in str(request.url)
    # resolution call recorded, key sanitized out of the stored endpoint
    call = adapter._last_resolution_call
    assert call.credits == 0  # FEC-3
    assert "test-fec-key" not in call.endpoint  # RUN-3
    assert "api_key" not in call.endpoint


async def test_resolve_candidate_uses_prefilled_id(client_factory) -> None:
    """FEC-1: existing fec_candidate_id short-circuits the search."""
    adapter, requests = client_factory({})
    ref = REF.model_copy(update={"fec_candidate_id": "S2PADOE00"})
    assert await adapter.resolve_candidate(ref) == "S2PADOE00"
    assert requests == []


async def test_resolve_candidate_no_match_raises(client_factory) -> None:
    """FEC-1: no plausible match → AdapterError, never a fabricated id."""
    adapter, _ = client_factory({"/candidates/search/": [_search_response([])]})
    with pytest.raises(AdapterError, match="no federal candidate match"):
        await adapter.resolve_candidate(REF)


async def test_resolve_caches_per_name(client_factory) -> None:
    """FEC-1: resolution happens once per run (adapter-level memo)."""
    adapter, requests = client_factory(
        {
            "/candidates/search/": [
                _search_response([_candidate("S2PADOE00", "DOE, JANE")])
            ]
        }
    )
    first = await adapter.resolve_candidate(REF)
    second = await adapter.resolve_candidate(REF)
    assert first == second == "S2PADOE00"
    assert len(requests) == 1


# FEC-2: full donations fetch
async def test_fetch_donations_builds_findings(client_factory) -> None:
    """FEC-2: candidate → principal committees → totals; one finding per
    committee with deterministic totals line; FEC-5 first_hand True."""
    adapter, requests = client_factory(
        {
            "/candidates/search/": [
                _search_response([_candidate("S2PADOE00", "DOE, JANE")])
            ],
            "/committees/history/": [
                httpx2.Response(
                    200,
                    json={
                        "results": [
                            {
                                "committee_id": "C00700000",
                                "name": "Jane Doe for Senate",
                                "designation": "P",
                            }
                        ]
                    },
                )
            ],
            "/totals/": [
                httpx2.Response(
                    200,
                    json={
                        "results": [
                            {
                                "committee_id": "C00700000",
                                "committee_name": "Jane Doe for Senate",
                                "receipts": 1234567.89,
                                "individual_itemized_contributions": 987654.32,
                            }
                        ]
                    },
                )
            ],
        }
    )
    outcome = await adapter.fetch(REF, "donations")

    assert len(outcome.findings) == 1
    finding = outcome.findings[0]
    assert finding.url == committee_fec_url("C00700000")
    assert finding.first_hand is True  # FEC-5
    assert "$1,234,567.89" in finding.content
    assert finding.meta["receipts"] == 1234567.89
    assert finding.meta["committee_id"] == "C00700000"

    # three upstream HTTP calls: search, committees, totals
    assert len(requests) == 3
    assert "api_key=test-fec-key" in str(requests[2].url)
    # no stored call leaks the key (RUN-3)
    for call in outcome.calls:
        assert "test-fec-key" not in call.endpoint
    assert all(call.credits == 0 for call in outcome.calls)  # FEC-3


async def test_fetch_dedupes_and_caps_committees(client_factory) -> None:
    """FEC-2: MAX_COMMITTEES caps totals calls."""
    committees = [
        {"committee_id": f"C0000000{i}", "name": f"C{i}", "designation": "P"}
        for i in range(5)
    ]
    adapter, requests = client_factory(
        {
            "/candidates/search/": [
                _search_response([_candidate("S2PADOE00", "DOE, JANE")])
            ],
            "/committees/history/": [
                httpx2.Response(200, json={"results": committees})
            ],
            "/totals/": [
                httpx2.Response(
                    200,
                    json={
                        "results": [
                            {
                                "committee_id": "C00000000",
                                "committee_name": "C",
                                "receipts": 1.0,
                                "individual_itemized_contributions": 1.0,
                            }
                        ]
                    },
                )
            ]
            * 3,
        }
    )
    outcome = await adapter.fetch(REF, "donations")
    total_calls = len(requests)
    assert total_calls == 1 + 1 + 3  # search + committees + 3 totals caps
    assert len(outcome.findings) == 3


async def test_fetch_wrong_topic_raises(client_factory) -> None:
    """Adapters reject topics outside their cell plan."""
    adapter, _ = client_factory({})
    with pytest.raises(AdapterError, match="not covered"):
        await adapter.fetch(REF, "positions")


async def test_fec_429_retried_once(client_factory, monkeypatch) -> None:
    """FEC-3: 429 → one retry with >=2s backoff."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("apps.research.adapters.fec.asyncio.sleep", fake_sleep)
    adapter, requests = client_factory(
        {
            "/candidates/search/": [
                httpx2.Response(429, json={"detail": "slow down"}),
                _search_response([_candidate("S2PADOE00", "DOE, JANE")]),
            ]
        }
    )
    assert await adapter.resolve_candidate(REF) == "S2PADOE00"
    assert len(requests) == 2
    assert sleeps == [2.0]


async def test_fec_403_no_retry(client_factory) -> None:
    """FEC-3: 403 (bad key) → immediate AdapterError."""
    adapter, requests = client_factory(
        {"/candidates/search/": [httpx2.Response(403, json={"detail": "no"})]}
    )
    with pytest.raises(AdapterError, match="HTTP 403"):
        await adapter.resolve_candidate(REF)
    assert len(requests) == 1


def test_fec_settings_demo_key_opt_in(monkeypatch) -> None:
    """FEC-3: DEMO_KEY only with explicit FEC_DEMO=1."""
    from django.test import override_settings

    from apps.research import settings as research_settings

    with override_settings(FEC_API_KEY=None, FEC_DEMO=False):
        assert not research_settings.fec_configured()
        with pytest.raises(RuntimeError):
            research_settings.fec_settings()

    with override_settings(FEC_API_KEY=None, FEC_DEMO=True):
        assert research_settings.fec_configured()
        config = research_settings.fec_settings()
        assert config.api_key == "DEMO_KEY"

    with override_settings(FEC_API_KEY="real-key", FEC_DEMO=True):
        assert research_settings.fec_settings().api_key == "real-key"


async def test_request_body_not_json_dumped_on_error_text(client_factory) -> None:
    """Sanity: error text from FEC contains no api_key= real value."""
    adapter, _ = client_factory(
        {
            "/candidates/search/": [
                httpx2.Response(400, text="bad q?api_key=test-fec-key")
            ]
        }
    )
    with pytest.raises(AdapterError) as excinfo:
        await adapter.resolve_candidate(REF)
    assert "test-fec-key" not in str(excinfo.value)
    assert "api_key=***" in str(excinfo.value)
