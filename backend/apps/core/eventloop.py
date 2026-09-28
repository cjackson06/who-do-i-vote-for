"""Event-loop capture for the in-process task backend (specs/core-tasks.md).

`LoopCaptureMiddleware` wraps the ASGI application and records the running
loop on the first scope the server handles — uvicorn runs lifespan before
requests on the same loop, so the capture happens before any enqueue.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

ASGIApp = Callable[..., Awaitable[Any]]

_captured_loop: asyncio.AbstractEventLoop | None = None


def capture_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """TASKBACKEND-7: idempotent record of the server loop."""
    global _captured_loop
    _captured_loop = loop


def current_captured_loop() -> asyncio.AbstractEventLoop | None:
    return _captured_loop


def reset_captured_loop() -> None:
    """Test/worker hygiene: forget the captured loop."""
    global _captured_loop
    _captured_loop = None


class LoopCaptureMiddleware:
    """ASGI wrapper; captures the event loop on the first scope."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[Any]],
        send: Callable[[Any], Awaitable[Any]],
    ) -> None:
        with contextlib.suppress(RuntimeError):
            capture_event_loop(asyncio.get_running_loop())
        await self.app(scope, receive, send)
