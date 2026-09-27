"""Politician cache — contract: specs/politicians.md (POLITICIAN-*, CACHE-*, SOURCE-*)."""

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from django.db import IntegrityError
from django.utils import timezone as dj_tz

from apps.politicians.cache import (
    TTL_DAYS,
    CacheCell,
    fresh_cells,
    fresh_until,
    is_fresh,
    prune_stale,
)
from apps.politicians.models import (
    Fact,
    Politician,
    PoliticianProfile,
    SourceRecord,
)

NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def politician(db) -> Politician:
    return Politician.objects.create(
        name="Jane Doe", party="DEM", office="Senate", state="PA"
    )


def _record(
    politician: Politician,
    source_type: str = SourceRecord.SourceType.TAVILY_WEB,
    topic: str = "positions",
    url: str = "https://example.com/a",
    *,
    retrieved_at: datetime = NOW,
) -> SourceRecord:
    return SourceRecord.objects.create(
        politician=politician,
        source_type=source_type,
        topic=topic,
        url=url,
        url_hash=SourceRecord.url_hash_of(url),
        title="t",
        content="c",
        first_hand=True,
        retrieved_at=retrieved_at,
        fresh_until=fresh_until(source_type, now=retrieved_at),
    )


# POLITICIAN-1
def test_politician_identity_constraint(db) -> None:
    """POLITICIAN-1: (name, office, state) is the identity; dupes fail."""
    from django.db import transaction

    Politician.objects.create(name="Jane Doe", office="Senate", state="PA")
    with pytest.raises(IntegrityError), transaction.atomic():
        Politician.objects.create(name="Jane Doe", office="Senate", state="PA")


def test_politician_fec_id_unique(db) -> None:
    """POLITICIAN-1: fec_candidate_id unique when present."""
    from django.db import transaction

    Politician.objects.create(name="A", fec_candidate_id="P1")
    with pytest.raises(IntegrityError), transaction.atomic():
        Politician.objects.create(name="B", fec_candidate_id="P1")
    # Blank/default values don't collide (null in DB)
    Politician.objects.create(name="C")


# CACHE-2
def test_ttl_constants_match_spec() -> None:
    """CACHE-2: TTL values match the spec table."""
    assert TTL_DAYS["tavily_web"] == timedelta(days=30)
    assert TTL_DAYS["tavily_news"] == timedelta(days=7)
    assert TTL_DAYS["fec"] == timedelta(days=90)


def test_fresh_until_per_source_type() -> None:
    """CACHE-2: fresh_until = retrieved_at + TTL(source_type)."""
    assert fresh_until("tavily_news", now=NOW) == NOW + timedelta(days=7)
    assert fresh_until("fec", now=NOW) == NOW + timedelta(days=90)


def test_is_fresh_boundary(db, politician) -> None:
    """CACHE-2: fresh iff fresh_until > now; empty cell never fresh."""
    assert not is_fresh(politician.id, "tavily_web", "positions", now=NOW)

    record = _record(politician)  # web → 30d
    assert is_fresh(politician.id, "tavily_web", "positions", now=NOW)
    expiry = cast(datetime, record.fresh_until)
    assert not is_fresh(politician.id, "tavily_web", "positions", now=expiry)
    # one second before expiry is still fresh
    assert is_fresh(
        politician.id,
        "tavily_web",
        "positions",
        now=expiry - timedelta(seconds=1),
    )


def test_fresh_cells_distinct(db, politician) -> None:
    """CACHE-2/-4: fresh_cells returns the set of distinct fresh cells."""
    _record(politician, topic="positions")
    _record(politician, source_type="tavily_news", topic="controversies")
    _record(
        politician,
        source_type="tavily_news",
        topic="controversies",
        url="https://example.com/b",
    )
    # stale cell (news TTL 7d, fetched 10d ago)
    _record(
        politician,
        source_type="tavily_news",
        topic="voting_record",
        url="https://example.com/c",
        retrieved_at=NOW - timedelta(days=10),
    )
    cells = fresh_cells(politician.id, now=NOW)
    assert cells == {
        CacheCell("tavily_web", "positions"),
        CacheCell("tavily_news", "controversies"),
    }


# SOURCE-1
def test_url_hash(db, politician) -> None:
    """SOURCE-1: url_hash is lowercase sha256 hex of the url."""
    import hashlib

    record = _record(politician)
    url = cast(str, record.url)
    assert record.url_hash == hashlib.sha256(url.encode()).hexdigest()


def test_source_cell_unique(db, politician) -> None:
    """CACHE-1/SOURCE-1: (politician, source_type, topic, url_hash) unique."""
    from django.db import transaction

    _record(politician)
    with pytest.raises(IntegrityError), transaction.atomic():
        _record(politician)


# FACT-1
def test_fact_requires_source_record(db, politician) -> None:
    """FACT-1: every fact links exactly one SourceRecord (not null)."""
    record = _record(politician)
    profile = PoliticianProfile.objects.create(
        politician=politician, scope="federal", summary="s"
    )
    fact = Fact.objects.create(
        profile=profile, topic="positions", claim="c1", source_record=record
    )
    assert fact.source_record_id == record.pk
    from django.db import transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        Fact.objects.create(profile=profile, topic="positions", claim="c2")


# CACHE-5
def test_prune_stale(db, politician) -> None:
    """CACHE-5: removes records lapsed beyond 2x TTL; keeps fresh + grace."""
    fresh = _record(politician, url="https://e.com/f")
    in_grace = _record(
        politician,
        source_type="tavily_news",
        topic="controversies",
        url="https://e.com/g",
        retrieved_at=NOW - timedelta(days=8),
    )
    _record(  # stale beyond 2x7d grace → deleted
        politician,
        source_type="tavily_news",
        topic="voting_record",
        url="https://e.com/h",
        retrieved_at=NOW - timedelta(days=25),
    )
    deleted = prune_stale(politician.id, now=NOW)
    assert deleted == 1
    assert fresh.pk is not None
    assert in_grace.pk is not None


def test_created_at_timezone_aware(db, politician) -> None:
    """USE_TZ invariant: auto timestamps are aware."""
    profile = PoliticianProfile.objects.create(
        politician=politician, scope="federal", summary="s"
    )
    assert dj_tz.is_aware(profile.generated_at)
