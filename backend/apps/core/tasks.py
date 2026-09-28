"""In-process django.tasks backend (specs/core-tasks.md, TASKBACKEND-*).

Executes tasks on the ASGI server's captured event loop: enqueue returns
immediately (READY) and the job runs in the background of the same process.
Durable status lives in domain rows (e.g. ResearchRun); this backend's
result store is best-effort in-memory (TASKBACKEND-6).
"""

import asyncio
import logging
from traceback import format_exception

from django.core.exceptions import ImproperlyConfigured
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.base import (
    Task,
    TaskContext,
    TaskError,
    TaskResult,
    TaskResultStatus,
)
from django.tasks.exceptions import TaskResultDoesNotExist
from django.tasks.signals import task_enqueued, task_finished, task_started
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.json import normalize_json

from .eventloop import current_captured_loop

logger = logging.getLogger(__name__)

_result_stores: dict[str, dict[str, TaskResult]] = {}
_running_tasks: dict[str, dict[str, asyncio.Task[None]]] = {}
_WORKER_ID = get_random_string(32)


class InProcessBackend(BaseTaskBackend):
    """Spawn tasks onto the captured ASGI loop; results kept in memory.

    Shared state (result store, worker id) is module-level keyed by alias so
    it is visible across the per-thread backend instances Django's
    thread-local connection handler may create.
    """

    supports_async_task = True
    supports_get_result = True

    def __init__(self, alias: str, params: dict) -> None:
        super().__init__(alias, params)
        self.results = _stores_for(self.alias)
        self.tasks = _running_for(self.alias)

    def enqueue(self, task: Task, args: tuple, kwargs: dict) -> TaskResult:
        self.validate_task(task)

        result = self._new_result(task, args, kwargs)
        self.results[result.id] = result

        loop = current_captured_loop()
        # TASKBACKEND-3: explicit failure, no silent inline fallback
        if loop is None or loop.is_closed():
            raise ImproperlyConfigured(
                "apps.core.tasks.InProcessBackend requires a captured ASGI "
                "event loop: start the server with `just server` (uvicorn — "
                "ASGI). `manage.py runserver` is WSGI and cannot run "
                "background tasks. In tests, call "
                "apps.core.eventloop.capture_event_loop(loop) first. "
                f"(Task {task.module_path!r} was enqueued without a loop.)"
            )
        loop.call_soon_threadsafe(self._spawn, task, result)
        return result

    async def aenqueue(self, task: Task, args: tuple, kwargs: dict) -> TaskResult:
        self.validate_task(task)

        result = self._new_result(task, args, kwargs)
        self.results[result.id] = result
        self._spawn(task, result)
        return result

    def get_result(self, result_id: str) -> TaskResult:
        try:
            return self.results[result_id]
        except KeyError:
            raise TaskResultDoesNotExist(result_id) from None

    async def aget_result(self, result_id: str) -> TaskResult:
        try:
            return self.results[result_id]
        except KeyError:
            raise TaskResultDoesNotExist(result_id) from None

    # -- internals ---------------------------------------------------------

    def _new_result(self, task: Task, args: tuple, kwargs: dict) -> TaskResult:
        return TaskResult(
            task=task,
            id=get_random_string(32),
            status=TaskResultStatus.READY,
            enqueued_at=None,
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=list(args),
            kwargs=dict(kwargs),
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )

    def _spawn(self, task: Task, result: TaskResult) -> None:
        """Schedule execution on the loop thread (enqueue may come from any)."""
        loop = current_captured_loop()
        if loop is None:
            raise ImproperlyConfigured(
                "InProcessBackend lost its captured event loop before the "
                f"task {task.module_path!r} could spawn."
            )
        loop.call_soon_threadsafe(self._run, task, result)

    def _run(self, task: Task, result: TaskResult) -> None:
        """Loop-thread side: create the runner task (TASKBACKEND-1, -2)."""
        self.tasks[result.id] = asyncio.get_running_loop().create_task(
            self._execute(task, result)
        )

    async def _execute(self, task: Task, result: TaskResult) -> None:
        object.__setattr__(result, "enqueued_at", timezone.now())
        task_enqueued.send(type(self), task_result=result)
        started = timezone.now()
        object.__setattr__(result, "status", TaskResultStatus.RUNNING)
        object.__setattr__(result, "started_at", started)
        object.__setattr__(result, "last_attempted_at", started)
        result.worker_ids.append(_WORKER_ID)
        task_started.send(sender=type(self), task_result=result)

        try:
            if task.takes_context:
                raw = await task.acall(
                    TaskContext(task_result=result), *result.args, **result.kwargs
                )
            else:
                raw = await task.acall(*result.args, **result.kwargs)
            object.__setattr__(result, "_return_value", normalize_json(raw))
            object.__setattr__(result, "finished_at", timezone.now())
            object.__setattr__(result, "status", TaskResultStatus.SUCCESSFUL)
            task_finished.send(type(self), task_result=result)
        except KeyboardInterrupt:
            raise
        except BaseException as exc:
            object.__setattr__(result, "finished_at", timezone.now())
            exc_type = type(exc)
            result.errors.append(
                TaskError(
                    exception_class_path=f"{exc_type.__module__}.{exc_type.__qualname__}",
                    traceback="".join(format_exception(exc)),
                )
            )
            object.__setattr__(result, "status", TaskResultStatus.FAILED)
            task_finished.send(type(self), task_result=result)
            logger.exception("In-process task %s (id=%s) failed", task.name, result.id)


def _stores_for(alias: str) -> dict[str, TaskResult]:
    store = _result_stores.get(alias)
    if store is None:
        store = {}
        _result_stores[alias] = store
    return store


def _running_for(alias: str) -> dict[str, asyncio.Task[None]]:
    store = _running_tasks.get(alias)
    if store is None:
        store = {}
        _running_tasks[alias] = store
    return store
