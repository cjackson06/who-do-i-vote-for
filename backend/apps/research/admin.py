"""Admin for research runs + the staff trigger (specs/research.md, RUN-1).

Owns the single `Politician` registration so the "Run research" action sits
next to the model it acts on; profile/fact/source admins stay in
apps.politicians.admin.
"""

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Manager, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.politicians.models import Politician

from .models import ResearchRun, SourceCall
from .tasks import run_research
from .topics import validate_topics


def _runs() -> Manager[ResearchRun]:
    return ResearchRun.objects  # type: ignore[unresolved-attribute]


@admin.register(ResearchRun)
class ResearchRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "politician",
        "status_badge",
        "topics",
        "credits",
        "created_at",
        "finished_at",
    )
    list_filter = ("status", "force_refresh")
    search_fields = ("politician__name",)
    readonly_fields = (
        "politician",
        "status",
        "topics",
        "force_refresh",
        "task_result_id",
        "credits",
        "stats",
        "error",
        "created_at",
        "started_at",
        "finished_at",
    )

    @admin.display(description="status")
    def status_badge(self, run: ResearchRun) -> str:
        colors = {
            ResearchRun.Status.COMPLETED: "green",
            ResearchRun.Status.DEGRADED: "orange",
            ResearchRun.Status.FAILED: "red",
            ResearchRun.Status.RUNNING: "blue",
            ResearchRun.Status.QUEUED: "gray",
        }
        return format_html(
            "<b style='color: {}'>{}</b>",
            colors.get(run.status, "black"),
            run.status,
        )


@admin.register(SourceCall)
class SourceCallAdmin(admin.ModelAdmin):
    list_display = (
        "run",
        "adapter",
        "topic",
        "endpoint",
        "credits",
        "latency_ms",
        "status",
    )
    list_filter = ("adapter", "status")
    search_fields = ("endpoint", "query")
    readonly_fields = [field.name for field in SourceCall._meta.fields]  # ty: ignore[unresolved-attribute]


def enqueue_research(
    politician: Politician,
    *,
    topics: list[str] | None = None,
    force_refresh: bool = False,
) -> ResearchRun:
    """RUN-1: create the queued run and enqueue the task after commit."""
    run = _runs().create(
        politician=politician,
        status=ResearchRun.Status.QUEUED,
        topics=list(validate_topics(topics)),
        force_refresh=force_refresh,
    )
    transaction.on_commit(lambda: run_research.enqueue(politician.pk, run.pk))
    return run


@admin.action(description="Run research (selected politicians)")
def run_research_action(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Politician],
) -> None:
    """RUN-1 admin trigger: one queued run per selected politician."""
    runs = [enqueue_research(politician) for politician in queryset]
    if runs:
        modeladmin.message_user(
            request,
            f"Research enqueued for {len(runs)} politician(s); refresh this "
            "page (or open Research runs) to see the status.",
            messages.SUCCESS,
        )


@admin.register(Politician)
class PoliticianAdmin(admin.ModelAdmin):
    list_display = ("name", "party", "office", "state", "fec_candidate_id")
    list_filter = ("party", "state")
    search_fields = ("name", "fec_candidate_id")
    readonly_fields = ("created_at", "updated_at")
    actions = [run_research_action]
