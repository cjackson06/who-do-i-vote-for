"""Profile regeneration service (specs/politicians.md, POLITICIAN-3/-3b)."""

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .models import Fact, Politician, PoliticianProfile


@dataclass(frozen=True)
class NewFact:
    """A validated fact ready to store (link resolved by the caller)."""

    topic: str
    claim: str
    quote: str = ""
    source_record_id: int = 0


def replace_profile(
    politician_id: int,
    scope: str,
    summary: str,
    facts: list[NewFact],
    *,
    research_run_id: int | None = None,
    now: datetime | None = None,
) -> PoliticianProfile:
    """POLITICIAN-3/-3b: atomic replace of the profile and its facts.

    Only called with a complete, validated fact set; failures roll back and
    leave the previous profile intact.
    """
    now = now or timezone.now()

    with transaction.atomic():
        profile_manager = PoliticianProfile.objects  # type: ignore[unresolved-attribute]
        existing = (
            profile_manager.select_for_update()
            .filter(politician_id=politician_id, scope=scope)
            .first()
        )
        if existing is not None:
            existing.facts.all().delete()  # type: ignore[union-attr]
            existing.delete()

        profile = profile_manager.create(
            politician_id=politician_id,
            scope=scope,
            summary=summary,
            research_run_id=research_run_id,
        )
        fact_manager = Fact.objects  # type: ignore[unresolved-attribute]
        fact_manager.bulk_create(
            [
                Fact(
                    profile=profile,
                    topic=fact.topic,
                    claim=fact.claim,
                    quote=fact.quote,
                    source_record_id=fact.source_record_id,
                )
                for fact in facts
                if fact.source_record_id
            ]
        )
    return profile


def ensure_politician(
    name: str,
    *,
    party: str = "",
    office: str = "",
    state: str = "",
) -> Politician:
    """POLITICIAN-1/-2: get-or-create by identity (strip-normalized name)."""
    name = name.strip()
    politician, _ = Politician.objects.get_or_create(  # type: ignore[unresolved-attribute]
        name=name,
        office=office,
        state=state,
        defaults={"party": party},
    )
    return politician
