"""Research runs + cost log (specs/research.md, RUN-*)."""

from django.db import models

from apps.politicians.models import Politician


class ResearchRun(models.Model):
    """One admin-triggered research execution over a politician."""

    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        COMPLETED = "completed"
        DEGRADED = "degraded"
        FAILED = "failed"

    politician = models.ForeignKey(
        Politician, on_delete=models.CASCADE, related_name="research_runs"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    topics = models.JSONField(default=list)
    force_refresh = models.BooleanField(default=False)
    task_result_id = models.CharField(max_length=64, blank=True, default="")
    credits = models.PositiveIntegerField(default=0)
    stats = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["politician", "-created_at"])]

    def __str__(self) -> str:
        return f"run#{self.pk} {self.politician} {self.status}"


class SourceCall(models.Model):
    """Cost/latency log for one outbound source HTTP call (RUN-3).

    Mirrors apps.llm.ModelCall for non-LLM sources; never stores keys.
    """

    class Status(models.TextChoices):
        OK = "ok"
        ERROR = "error"

    run = models.ForeignKey(
        ResearchRun,
        on_delete=models.CASCADE,
        related_name="source_calls",
        null=True,
        blank=True,
    )
    adapter = models.CharField(max_length=20)
    topic = models.CharField(max_length=30, blank=True, default="")
    endpoint = models.CharField(max_length=500)
    query = models.CharField(max_length=500, blank=True, default="")
    credits = models.PositiveSmallIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.adapter}/{self.topic} {self.status} ({self.credits}c)"
