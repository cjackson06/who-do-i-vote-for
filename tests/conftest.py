"""Shared fixtures. LLM tests run fully offline via httpx2.MockTransport."""

import json
from collections.abc import Callable
from types import SimpleNamespace

import httpx2
import pytest
from asgiref.sync import sync_to_async

from apps.llm.client import LLMClient
from apps.llm.config import ROLES
from apps.llm.models import ModelCall

ROLE_ENV_FIELDS = ("BASE_URL", "API_KEY", "MODEL", "TEMPERATURE")
GLOBAL_LLM_VARS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "LLM_TEMPERATURE")


@pytest.fixture
def llm_env(monkeypatch: pytest.MonkeyPatch) -> str:
    """Hermetic LLM env: clear everything, configure only `researcher`."""

    for role in ROLES:
        for field in ROLE_ENV_FIELDS:
            monkeypatch.delenv(f"LLM_{role.upper()}_{field}", raising=False)
    for var in GLOBAL_LLM_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LLM_RESEARCHER_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_RESEARCHER_MODEL", "test-model")
    monkeypatch.setenv("LLM_RESEARCHER_API_KEY", "test-key")
    return "researcher"


def _completion_body(content: str, usage: dict | None = None) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": usage
        or {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
    }


def _error_body(message: str) -> dict:
    return {
        "error": {"message": message, "type": "invalid_request_error", "code": None}
    }


def _sse_bytes(deltas: list[str], usage: dict | None = None) -> bytes:
    chunks: list[dict] = []
    for delta in deltas:
        chunks.append(
            {
                "id": "chatcmpl-test",
                "object": "chat.completion.chunk",
                "created": 1_700_000_000,
                "model": "test-model",
                "choices": [
                    {"index": 0, "delta": {"content": delta}, "finish_reason": None}
                ],
            }
        )
    final: dict = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": 1_700_000_000,
        "model": "test-model",
        "choices": [],
    }
    if usage is not None:
        final["usage"] = usage
    chunks.append(final)
    payload = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
    return (payload + "data: [DONE]\n\n").encode()


@pytest.fixture
def llm_testkit() -> SimpleNamespace:
    """Offline LLMClient factory + response-body builders (zero network)."""

    def make_client(handler: Callable) -> LLMClient:
        transport = httpx2.MockTransport(handler)
        return LLMClient(
            http_client=httpx2.AsyncClient(transport=transport), max_retries=0
        )

    return SimpleNamespace(
        make_client=make_client,
        completion=_completion_body,
        error=_error_body,
        sse=_sse_bytes,
    )


@pytest.fixture
def get_model_calls():
    """Async accessor for ModelCall rows (safe from event-loop context)."""

    async def _get() -> list[ModelCall]:
        return await sync_to_async(lambda: list(ModelCall.objects.all()))()  # type: ignore[unresolved-attribute]

    return _get
