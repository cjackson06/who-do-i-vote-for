"""Politician data + research corpus cache (specs/politicians.md)."""

import hashlib

from django.db import models


class Politician(models.Model):
    """A researched political figure (POLITICIAN-1 identity constraint)."""

    name = models.CharField(max_length=200)
    party = models.CharField(max_length=100, blank=True, default="")
    office = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    fec_candidate_id = models.CharField(
        max_length=20, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "office", "state"],
                name="politician_identity",
            ),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        loc = f" [{self.state}]" if self.state else ""
        return f"{self.name}{loc}"


class PoliticianProfile(models.Model):
    """Per-scope summarized profile; regenerated atomically on re-research."""

    class Scope(models.TextChoices):
        FEDERAL = "federal"

    politician = models.ForeignKey(
        Politician, on_delete=models.CASCADE, related_name="profiles"
    )
    scope = models.CharField(max_length=20, choices=Scope.choices)
    summary = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["politician", "scope"],
                name="profile_scope_unique",
            ),
        ]
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return f"{self.politician} · {self.scope}"


class SourceRecord(models.Model):
    """One cached first-hand-eligible source (SOURCE-1, CACHE-1)."""

    class SourceType(models.TextChoices):
        TAVILY_WEB = "tavily_web"
        TAVILY_NEWS = "tavily_news"
        FEC = "fec"

    @staticmethod
    def url_hash_of(url: str) -> str:
        """SOURCE-1: lowercase sha256 hex of the url string."""
        return hashlib.sha256(url.encode()).hexdigest()

    politician = models.ForeignKey(
        Politician, on_delete=models.CASCADE, related_name="source_records"
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    topic = models.CharField(max_length=30)
    url = models.CharField(max_length=500)
    url_hash = models.CharField(max_length=64)
    title = models.CharField(max_length=500, blank=True, default="")
    content = models.TextField(blank=True, default="")
    first_hand = models.BooleanField(default=False)
    published_date = models.DateField(null=True, blank=True)
    retrieved_at = models.DateTimeField()
    fresh_until = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["politician", "source_type", "topic", "url_hash"],
                name="source_cell_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["politician", "source_type", "topic", "fresh_until"],
                name="src_cell_fresh_idx",
            ),
        ]
        ordering = ["-retrieved_at"]

    def __str__(self) -> str:
        url = str(self.url)  # ty sees the descriptor type; runtime is a str
        return f"{self.source_type}/{self.topic}: {url[:60]}"


class Fact(models.Model):
    """A claim with its citation (FACT-1: SourceRecord required)."""

    class Topic(models.TextChoices):
        POSITIONS = "positions"
        VOTING_RECORD = "voting_record"
        CONTROVERSIES = "controversies"
        DONATIONS = "donations"

    profile = models.ForeignKey(
        PoliticianProfile, on_delete=models.CASCADE, related_name="facts"
    )
    topic = models.CharField(max_length=30, choices=Topic.choices)
    claim = models.TextField()
    quote = models.TextField(blank=True, default="")
    source_record = models.ForeignKey(
        SourceRecord, on_delete=models.PROTECT, related_name="facts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["profile", "topic", "pk"]

    def __str__(self) -> str:
        claim = str(self.claim)
        return f"[{self.topic}] {claim[:60]}"
