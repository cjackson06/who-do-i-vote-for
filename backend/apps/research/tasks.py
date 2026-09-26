"""Registered django.tasks jobs (specs/research.md, RUN-2; specs/core-tasks.md)."""

from asgiref.sync import sync_to_async
from django.db.models import Manager
from django.tasks import task

from .models import ResearchRun
from .swarm import load_ref, research_politician
from .topics import validate_topics


@task
async def run_research(politician_id: int, run_id: int) -> None:
    """RUN-2: queued → running → terminal; unexpected errors mark failed."""
    run = await sync_to_async(_load_run)(run_id)
    if run is None or run.status != ResearchRun.Status.QUEUED:
        return  # stale/duplicate enqueue; nothing to do
    ref = await sync_to_async(load_ref)(politician_id)
    topics = validate_topics(run.topics)

    await sync_to_async(_mark_running)(run_id)
    try:
        await research_politician(
            ref,
            list(topics),
            force_refresh=run.force_refresh,
            run_id=run_id,
        )
    except Exception as exc:
        await sync_to_async(_mark_failed)(run_id, f"{type(exc).__name__}: {exc}")
        raise  # TASKBACKEND-2: framework captures traceback; RUN-2 re-raise


def _load_run(run_id: int) -> ResearchRun | None:
    return _runs().filter(pk=run_id).first()


def _mark_running(run_id: int) -> None:
    _runs().filter(pk=run_id, status=ResearchRun.Status.QUEUED).update(
        status=ResearchRun.Status.RUNNING
    )


def _mark_failed(run_id: int, error: str) -> None:
    from django.utils import timezone

    _runs().filter(pk=run_id).update(
        status=ResearchRun.Status.FAILED,
        error=error[:2000],
        finished_at=timezone.now(),
    )


def _runs() -> Manager[ResearchRun]:
    return ResearchRun.objects  # type: ignore[unresolved-attribute]
