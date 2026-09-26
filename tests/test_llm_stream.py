"""LLMClient.stream — contract: specs/llm.md (LLM-STREAM-*)."""

import httpx2
import openai
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


async def test_stream_yields_deltas_and_logs_row(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-STREAM-1/2: deltas in order; one ok row with usage if supplied."""

    usage = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            content=llm_testkit.sse(["Hel", "lo"], usage=usage),
            headers={"content-type": "text/event-stream"},
            request=request,
        )

    client = llm_testkit.make_client(handler)
    deltas = [
        delta
        async for delta in client.stream(
            "researcher", [{"role": "user", "content": "hi"}]
        )
    ]

    assert deltas == ["Hel", "lo"]
    [row] = await get_model_calls()
    assert row.status == "ok"
    assert row.response_format == "text"
    assert row.total_tokens == 5
    assert row.latency_ms >= 0


async def test_stream_without_usage_stays_null(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-STREAM-2: missing usage chunk -> null tokens, never an error."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            content=llm_testkit.sse(["a"], usage=None),
            headers={"content-type": "text/event-stream"},
            request=request,
        )

    client = llm_testkit.make_client(handler)
    deltas = [delta async for delta in client.stream("researcher", [])]

    assert deltas == ["a"]
    [row] = await get_model_calls()
    assert row.total_tokens is None
    assert row.status == "ok"


async def test_stream_error_logs_and_propagates(
    llm_env, llm_testkit, get_model_calls
) -> None:
    """LLM-STREAM-2/LLM-CLIENT-6: error row written, SDK error propagates."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            500, json={"error": {"message": "boom"}}, request=request
        )

    client = llm_testkit.make_client(handler)
    with pytest.raises(openai.InternalServerError):
        async for _ in client.stream("researcher", [{"role": "user", "content": "x"}]):
            pass

    [row] = await get_model_calls()
    assert row.status == "error"
