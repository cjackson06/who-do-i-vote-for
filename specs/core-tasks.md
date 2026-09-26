# Task framework spec (`apps.core.tasks`)

> Source of truth for background execution: the Django 6 `django.tasks`
> framework, the in-process ASGI backend, loop capture, and the `TASKS`
> settings map. Code implements this spec; tests verify it.

## Purpose

Run long jobs (research swarm, later the analysis pipeline) triggered from the
Django admin **without blocking the HTTP request**, using Django's native task
API. No custom CLI, no extra processes: tasks execute in the ASGI server
process itself (the repo's "single container" decision), and swapping to a
durable backend later is settings-only.

## Interfaces

### Settings

```python
TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    }
}
```

| Settings module | Default alias BACKEND | Why |
|---|---|---|
| `base.py` | `django.tasks.backends.immediate.ImmediateBackend` | Safe for scripts/shell/manage.py stock commands (inline execution, still correct) |
| `local.py`, `prod.py` | `apps.core.tasks.InProcessBackend` | Server runs: enqueue-and-return, execute on the ASGI event loop |
| tests (fixture override) | `django.tasks.backends.dummy.DummyBackend` or `ImmediateBackend` | Hermetic, explicit control |

### Event-loop capture

`apps/core/asgi.py` exports `application` = the Django ASGI application wrapped
by `LoopCaptureMiddleware`. On **any** first scope it records
`asyncio.get_running_loop()` via `capture_event_loop(loop)`. `config/asgi.py`
imports from it.

```python
def capture_event_loop(loop: asyncio.AbstractEventLoop) -> None: ...
def current_captured_loop() -> asyncio.AbstractEventLoop | None: ...
def reset_captured_loop() -> None:  # test/worker hygiene
```

### `InProcessBackend`

```python
class InProcessBackend(BaseTaskBackend):
    supports_async_task = True
    supports_get_result = True
    # enqueue(task, args, kwargs) -> TaskResult       # READY, runs in background
    # aenqueue(task, args, kwargs) -> TaskResult      # uses the running loop
    # get_result(result_id) -> TaskResult            # from in-memory store
```

### Registered task (jobs built on this seam)

```python
# apps/research/tasks.py
@task
async def run_research(politician_id: int, run_id: int) -> None: ...
```

Task functions are module-level and take JSON-serializable args (ints/strings).
DB access inside task bodies uses `sync_to_async` (or async ORM where suitable).

## Rules

- **TASKBACKEND-1 (MUST)** — `enqueue()` MUST return a `TaskResult` with status
  `READY` immediately; execution MUST be scheduled on the captured loop, never
  awaited inside `enqueue()`. The caller (e.g. an admin action) never blocks on
  the job.
- **TASKBACKEND-2 (MUST)** — execution MUST mirror Django semantics exactly:
  status transitions `READY → RUNNING → SUCCESSFUL|FAILED`, timestamps
  (`enqueued_at`, `started_at`, `finished_at`), `tasks_*` signals sent
  (`enqueued`, `started`, `finished`), return value and errors recorded on the
  result. A task exception MUST be captured into
  `result.errors[0]` (classname + traceback) and MUST NOT propagate to the
  event loop or crash the process.
- **TASKBACKEND-3 (MUST)** — `enqueue()` from a sync context (no captured
  loop — e.g. a script against a `local.py`/`prod.py` settings module outside
  the ASGI server) MUST raise `ImproperlyConfigured` explaining that
  `InProcessBackend` requires the ASGI server (or the `capture_event_loop`
  hook). No silent inline fallback.
- **TASKBACKEND-4 (MUST)** — `supports_async_task = True`; the backend awaits
  coroutine task functions via `task.acall(...)`. Priority ordering is NOT
  supported (`supports_priority = False`); execution order follows spawn order.
- **TASKBACKEND-5 (MUST)** — `get_result(result_id)` returns the stored
  `TaskResult` or raises `TaskResultDoesNotExist`; results ARE retrievable
  from the same process while it lives. In-memory results MUST NOT be relied
  on across restarts; durable status MUST live in domain rows (e.g.
  `ResearchRun`), never only in the backend.
- **TASKBACKEND-6 (SHOULD)** — the backend keeps no queue file/network state;
  it is best-effort in-process execution. Fire-and-forget semantics for staff
  triggers are acceptable; domain rows carry the authority.
- **TASKBACKEND-7 (MUST)** — loop capture happens at ASGI startup (lifespan or
  first scope) by `LoopCaptureMiddleware`; `capture_event_loop` MUST be safe to
  call repeatedly (idempotent overwrite), and the captured loop MUST be from
  the same thread as the server loop.

## Errors

| Exception | When |
|---|---|
| `ImproperlyConfigured` | `enqueue()`/`aenqueue()` without a captured loop and not in an async context (TASKBACKEND-3) |
| `TaskResultDoesNotExist` | `get_result` with an unknown id |
| `InvalidTask` | task validation failure (framework standard) |

## Non-goals

- Cross-process queueing, retries, deferral (`run_after`), durable
  results — those arrive when a durable backend (DB/Redis) is adopted;
  call sites MUST NOT change.
- A custom worker process or any CLI surface for running jobs.
- Progress streaming (Phase 3 SSE builds on the same event loop).
