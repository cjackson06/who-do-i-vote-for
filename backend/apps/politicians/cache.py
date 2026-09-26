"""Cache freshness over (politician, source_type, topic) cells (CACHE-*)."""

from datetime import datetime, timedelta
from typing import NamedTuple

from django.utils import timezone

from .models import SourceRecord

# CACHE-2: TTL per source type; changes here are spec + code + test changes
TTL_DAYS: dict[str, timedelta] = {
    SourceRecord.SourceType.TAVILY_WEB: timedelta(days=30),
    SourceRecord.SourceType.TAVILY_NEWS: timedelta(days=7),
    SourceRecord.SourceType.FEC: timedelta(days=90),
}

# CACHE-5: prune grace multiple
PRUNE_GRACE_MULTIPLE = 2


class CacheCell(NamedTuple):
    """One cache identity cell (CACHE-1)."""

    source_type: str
    topic: str


def fresh_until(source_type: str, *, now: datetime) -> datetime:
    """TTL expiry for a source type's records fetched at `now` (CACHE-2)."""
    ttl = TTL_DAYS.get(source_type)
    if ttl is None:
        raise ValueError(f"Unknown source type: {source_type!r}")
    return now + ttl


def is_fresh(
    politician_id: int,
    source_type: str,
    topic: str,
    *,
    now: datetime | None = None,
) -> bool:
    """CACHE-2: cell is fresh if any record's fresh_until > now."""
    now = now or timezone.now()
    manager = SourceRecord.objects  # type: ignore[unresolved-attribute]
    return manager.filter(
        politician_id=politician_id,
        source_type=source_type,
        topic=topic,
        fresh_until__gt=now,
    ).exists()


def fresh_cells(politician_id: int, *, now: datetime | None = None) -> set[CacheCell]:
    """Distinct cells with at least one fresh record (CACHE-2, CACHE-4)."""
    now = now or timezone.now()
    manager = SourceRecord.objects  # type: ignore[unresolved-attribute]
    rows = (
        manager.filter(
            politician_id=politician_id,
            fresh_until__gt=now,
        )
        .values_list("source_type", "topic")
        .distinct()
    )
    return {CacheCell(source_type, topic) for source_type, topic in rows}


def prune_stale(politician_id: int, *, now: datetime | None = None) -> int:
    """CACHE-5: delete records whose freshness lapsed beyond 2x TTL."""
    now = now or timezone.now()
    manager = SourceRecord.objects  # type: ignore[unresolved-attribute]
    count = 0
    for source_type, ttl in TTL_DAYS.items():
        grace = ttl * PRUNE_GRACE_MULTIPLE
        count += manager.filter(
            politician_id=politician_id,
            source_type=source_type,
            fresh_until__lt=now - grace,
        ).delete()[0]
    return count
