"""ModelCall: per-invocation LLM call log (specs/llm.md, LLM-CALL-*)."""

from django.db import models


class ModelCall(models.Model):
    """One row per LLMClient.complete()/stream() invocation, ok or error.

    No FK to AnalysisJob/EvalRun yet — Phase 3/5 add nullable FKs by
    migration (decision logged in plans/phase-1-llm-core.md).
    """

    class Role(models.TextChoices):
        PROFILER = "profiler"
        RESEARCHER = "researcher"
        SUMMARIZER = "summarizer"
        MATCHER = "matcher"
        RECOMMENDER = "recommender"
        JUDGE = "judge"

    class ResponseFormat(models.TextChoices):
        TEXT = "text"
        JSON_MODE = "json_mode"
        JSON_SCHEMA = "json_schema"

    class Status(models.TextChoices):
        OK = "ok"
        ERROR = "error"

    role = models.CharField(max_length=20, choices=Role.choices)
    model = models.CharField(max_length=200)
    base_url = models.CharField(max_length=500)
    prompt_name = models.CharField(max_length=100, blank=True, default="")
    prompt_version = models.CharField(max_length=32, blank=True, default="")
    response_format = models.CharField(
        max_length=20, choices=ResponseFormat.choices, default=ResponseFormat.TEXT
    )
    attempts = models.PositiveSmallIntegerField(default=1)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["role", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.role}/{self.model} {self.status} ({self.created_at:%Y-%m-%d %H:%M:%S})"
