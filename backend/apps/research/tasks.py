"""Registered django.tasks jobs (specs/research.md, RUN-2; specs/core-tasks.md)."""

from django.db.models import Manager
from django.tasks import task

from .models import ResearchRun
from .swarm import load_ref, research_politician
from .topics import validate_topics


@task
async def run_research(politician_id: int, run_id: int) -> None:
    """RUN-2: queued → running → terminal; unexpected errors mark failed."""
    run = await _runs().filter(pk=run_id).afirst()
    if run is None or run.status != ResearchRun.Status.QUEUED:
        return  # stale/duplicate enqueue; nothing to do
    ref = await load_ref(politician_id)
    topics = validate_topics(run.topics)

    await (
        _runs()
        .filter(pk=run_id, status=ResearchRun.Status.QUEUED)
        .aupdate(status=ResearchRun.Status.RUNNING)
    )
    try:
        await research_politician(
            ref,
            list(topics),
            force_refresh=run.force_refresh,
            run_id=run_id,
        )
    except Exception as exc:
        await (
            _runs()
            .filter(pk=run_id)
            .aupdate(
                status=ResearchRun.Status.FAILED,
                error=f"{type(exc).__name__}: {exc}"[:2000],
            )
        )
        raise  # TASKBACKEND-2: framework captures traceback; RUN-2 re-raise


def _runs() -> Manager[ResearchRun]:
    return ResearchRun.objects  # type: ignore[unresolved-attribute]
