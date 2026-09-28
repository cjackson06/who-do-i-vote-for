"""apps.core task backend — contract: specs/core-tasks.md (TASKBACKEND-*).

Args crossing enqueue are JSON-normalized (framework contract), so task
bodies communicate via module-level stores, not mutable args.
"""

import asyncio
import threading

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.tasks import Task, task_backends
from django.tasks.base import TaskResultStatus
from django.tasks.exceptions import TaskResultDoesNotExist

from apps.core.eventloop import (
    capture_event_loop,
    reset_captured_loop,
)
from apps.core.tasks import InProcessBackend


def sync_task(x: int) -> int:
    return x * 2


async def async_task(x: int) -> int:
    await asyncio.sleep(0.001)
    return x * 2


async def failing_task() -> None:
    raise ValueError("boom")


async def thread_probe() -> None:
    PROBE["thread"] = threading.get_ident()
    PROBE["loop"] = asyncio.get_running_loop()


PROBE: dict[str, object] = {}


@pytest.fixture(autouse=True)
async def captured_loop(settings):
    """Capture the running loop + force the backend; reset both after."""
    settings.TASKS = {
        "default": {"BACKEND": "apps.core.tasks.InProcessBackend"},
    }
    reset_captured_loop()
    capture_event_loop(asyncio.get_running_loop())
    yield asyncio.get_running_loop()
    reset_captured_loop()


def _backend() -> InProcessBackend:
    backend = task_backends["default"]
    assert isinstance(backend, InProcessBackend)
    return backend


async def _wait_result(result, timeout: float = 2.0) -> TaskResultStatus:
    """Poll the result's status until it is terminal (event-loop friendly)."""
    backend = _backend()
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        refreshed = backend.get_result(result.id)
        if refreshed.is_finished:
            return refreshed.status
        await asyncio.sleep(0.005)
    raise TimeoutError(f"task did not finish within {timeout}s")


# TASKBACKEND-1
async def test_enqueue_returns_ready_then_runs_in_background() -> None:
    """TASKBACKEND-1: enqueue returns READY immediately; runs on the loop."""
    task = Task(func=async_task)
    result = task.enqueue(21)
    assert result.status == TaskResultStatus.READY
    final = await _wait_result(result)
    assert final == TaskResultStatus.SUCCESSFUL


async def test_task_executes_with_return_value() -> None:
    """TASKBACKEND-2: return value recorded via acall on the captured loop."""
    task = Task(func=async_task)
    result = task.enqueue(3)
    await _wait_result(result)
    stored = _backend().get_result(result.id)
    assert stored.status == TaskResultStatus.SUCCESSFUL
    assert stored.return_value == 6


async def test_error_captured_not_raised() -> None:
    """TASKBACKEND-2: exception stored on the result; loop keeps running."""
    task = Task(func=failing_task)
    result = task.enqueue()
    final = await _wait_result(result)
    assert final == TaskResultStatus.FAILED
    stored = _backend().get_result(result.id)
    assert stored.errors
    assert stored.errors[0].exception_class is ValueError
    assert "boom" in stored.errors[0].traceback


async def test_captured_loop_used(captured_loop) -> None:
    """TASKBACKEND-7: the task body runs on the captured (server) loop."""
    PROBE.clear()
    task = Task(func=thread_probe)
    result = task.enqueue()
    await _wait_result(result)
    assert PROBE["loop"] is captured_loop
    assert threading.get_ident() == PROBE["thread"]


async def test_sync_enqueue_from_other_thread(captured_loop) -> None:
    """TASKBACKEND-1/-7: enqueue from another thread (admin worker thread)
    still schedules on the captured loop via call_soon_threadsafe."""
    PROBE.clear()
    task = Task(func=thread_probe)
    results: dict[str, object] = {}

    def from_other_thread() -> None:
        results["r"] = task.enqueue()

    waiter = threading.Thread(target=from_other_thread)
    waiter.start()
    waiter.join()
    result = results["r"]
    await _wait_result(result)
    assert threading.get_ident() == PROBE["thread"]  # server loop thread
    assert PROBE["loop"] is captured_loop


async def test_enqueued_sync_task_executes(captured_loop) -> None:
    """TASKBACKEND-4: sync task funcs run too (via acall's sync_to_async)."""
    task = Task(func=sync_task)
    result = task.enqueue(4)
    status = await _wait_result(result)
    assert status == TaskResultStatus.SUCCESSFUL
    stored = _backend().get_result(result.id)
    assert stored.return_value == 8


async def test_no_captured_loop_raises() -> None:
    """TASKBACKEND-3: enqueue without a loop → ImproperlyConfigured."""
    reset_captured_loop()
    with pytest.raises(ImproperlyConfigured):
        Task(func=async_task).enqueue(1)


async def test_get_result_roundtrip_and_missing() -> None:
    """TASKBACKEND-5: get_result returns stored result; unknown raises."""
    task = Task(func=async_task)
    result = task.enqueue(1)
    await _wait_result(result)
    stored = _backend().get_result(result.id)
    assert stored.is_finished

    with pytest.raises(TaskResultDoesNotExist):
        _backend().get_result("missing-id")


def test_backend_capabilities() -> None:
    """TASKBACKEND-4: async supported; priority not."""
    backend = task_backends["default"]
    assert isinstance(backend, InProcessBackend)
    assert backend.supports_async_task
    assert backend.supports_get_result
    assert not backend.supports_priority
