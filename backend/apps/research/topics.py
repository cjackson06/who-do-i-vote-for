"""Research topics — closed set (specs/research.md, Topics)."""

from typing import Final

POSITIONS: Final = "positions"
VOTING_RECORD: Final = "voting_record"
CONTROVERSIES: Final = "controversies"
DONATIONS: Final = "donations"

TOPICS: Final[tuple[str, ...]] = (
    POSITIONS,
    VOTING_RECORD,
    CONTROVERSIES,
    DONATIONS,
)


def validate_topics(topics: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """Unknown topic names are a programming error (closed set)."""
    if topics is None:
        return TOPICS
    unknown = [t for t in topics if t not in TOPICS]
    if unknown:
        raise ValueError(f"Unknown research topics: {unknown!r}")
    return tuple(topics)
