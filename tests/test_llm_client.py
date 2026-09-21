"""LLMClient.complete — contract: specs/llm.md (LLM-CLIENT-*, LLM-CALL-*).

All tests run offline via httpx2.MockTransport; DB writes happen through
sync_to_async, hence django_db(transaction=True).
"""

import json
from typing import Any

import httpx2
import openai
import pytest
from pydantic import BaseModel

from apps.llm.exceptions import RoleNotConfigured, StructuredOutputError

pytestmark = pytest.mark.django_db(transaction=True)


class Out(BaseModel):
    answer: str
    score: int


VALID = json.dumps({"answer": "ok", "score": 1})


async def test_complete_text_returns_str_and_logs(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-CLIENT-1/7: text path returns str; one ok ModelCall row."""

    bodies: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.read()))
        return httpx2.Response(
            200, json=llm_testkit.completion("hello world"), request=request
        )

    client = llm_testkit.make_client(handler)
    text = await client.complete(
        "researcher",
        [{"role": "user", "content": "hi"}],
        prompt_name="p",
        prompt_version="1",
    )

    assert text == "hello world"
    [row] = await get_model_calls()
    assert row.status == "ok"
    assert row.response_format == "text"
    assert row.attempts == 1
    assert row.model == "test-model"
    assert row.base_url == "http://llm.test/v1"
    assert row.prompt_name == "p"
    assert row.prompt_version == "1"
    assert row.total_tokens == 12
    assert "test-key" not in row.base_url  # LLM-CONFIG-3


async def test_structured_json_schema_success(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-CLIENT-1/2: schema given -> validated instance, json_schema mode."""

    bodies: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.read()))
        return httpx2.Response(200, json=llm_testkit.completion(VALID), request=request)

    client = llm_testkit.make_client(handler)
    result = await client.complete(
        "researcher", [{"role": "user", "content": "hi"}], schema=Out
    )

    assert isinstance(result, Out)
    assert result.answer == "ok"
    assert result.score == 1
    assert bodies[0]["response_format"]["type"] == "json_schema"
    [row] = await get_model_calls()
    assert row.response_format == "json_schema"
    assert row.status == "ok"
    assert row.attempts == 1


async def test_json_schema_downgrade_is_transparent(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-CLIENT-3: 400 on json_schema -> JSON mode, no error surfaced."""

    bodies: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        body: dict[str, Any] = json.loads(request.read())
        bodies.append(body)
        mode = body.get("response_format", {}).get("type")
        if mode == "json_schema":
            return httpx2.Response(
                400,
                json=llm_testkit.error("response_format json_schema unsupported"),
                request=request,
            )
        return httpx2.Response(200, json=llm_testkit.completion(VALID), request=request)

    client = llm_testkit.make_client(handler)
    result = await client.complete(
        "researcher", [{"role": "user", "content": "hi"}], schema=Out
    )

    assert result.answer == "ok"
    assert [b["response_format"]["type"] for b in bodies] == [
        "json_schema",
        "json_object",
    ]
    assert bodies[1]["messages"][-1]["role"] == "user"
    assert "JSON Schema" in bodies[1]["messages"][-1]["content"]
    [row] = await get_model_calls()
    assert row.response_format == "json_mode"
    assert row.attempts == 2
    assert row.status == "ok"

    # downgrade persists for the client instance: next call skips json_schema
    await client.complete(
        "researcher", [{"role": "user", "content": "hi again"}], schema=Out
    )
    assert bodies[-1]["response_format"]["type"] == "json_object"


async def test_malformed_output_retried_with_error_context(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-CLIENT-4/5: malformed attempts re-ask with output + error."""

    bodies: list[dict[str, Any]] = []
    payloads = iter(["not json", "{bad", VALID])

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.read()))
        return httpx2.Response(
            200, json=llm_testkit.completion(next(payloads)), request=request
        )

    client = llm_testkit.make_client(handler)
    result = await client.complete(
        "researcher", [{"role": "user", "content": "hi"}], schema=Out
    )

    assert result.score == 1
    assert len(bodies) == 3
    msgs = bodies[2]["messages"]
    assert msgs[-2]["role"] == "assistant"
    assert msgs[-2]["content"] == "{bad"
    assert "could not be parsed" in msgs[-1]["content"]
    assert "JSONDecodeError" in msgs[-1]["content"]
    [row] = await get_model_calls()
    assert row.attempts == 3
    assert row.status == "ok"


async def test_malformed_exhaustion_raises_structured_error(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-CLIENT-5: past the attempt budget -> StructuredOutputError."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, json=llm_testkit.completion("nope"), request=request
        )

    client = llm_testkit.make_client(handler)
    with pytest.raises(StructuredOutputError) as excinfo:
        await client.complete(
            "researcher", [{"role": "user", "content": "hi"}], schema=Out, attempts=2
        )

    assert "2 attempts" in str(excinfo.value)
    assert excinfo.value.raw_output == "nope"
    [row] = await get_model_calls()
    assert row.status == "error"
    assert row.attempts == 2


async def test_transport_error_propagates_after_logging(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-CLIENT-6/7: SDK errors propagate as-is; error row written once."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            500, json={"error": {"message": "backend boom"}}, request=request
        )

    client = llm_testkit.make_client(handler)
    with pytest.raises(openai.InternalServerError):
        await client.complete("researcher", [{"role": "user", "content": "hi"}])

    [row] = await get_model_calls()
    assert row.status == "error"
    assert row.attempts == 1
    assert "InternalServerError" in row.error
    assert "test-key" not in row.error  # LLM-CONFIG-3


async def test_role_not_configured_makes_no_request(
    llm_env, monkeypatch, llm_testkit, get_model_calls
) -> None:
    """LLM-CALL-1/LLM-CHECK-2: unconfigured role fails before any attempt."""

    monkeypatch.delenv("LLM_RESEARCHER_BASE_URL")
    monkeypatch.delenv("LLM_RESEARCHER_MODEL")

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("no HTTP request should be made")

    client = llm_testkit.make_client(handler)
    with pytest.raises(RoleNotConfigured):
        await client.complete("researcher", [{"role": "user", "content": "hi"}])

    assert await get_model_calls() == []
