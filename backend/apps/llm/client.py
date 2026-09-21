"""Async OpenAI-compatible LLM client (specs/llm.md, LLM-CLIENT-*)."""

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx2
from asgiref.sync import sync_to_async
from openai import AsyncOpenAI, BadRequestError, NotFoundError
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel, ValidationError

from .config import RoleConfig, resolve_role_config
from .exceptions import StructuredOutputError
from .models import ModelCall

MAX_ATTEMPTS = 3
ERROR_TEXT_LIMIT = 2000
RAW_SNIPPET_LIMIT = 500

RETRY_INSTRUCTION = (
    "Your previous response could not be parsed as valid JSON for the required "
    "schema ({error}). Respond again with ONLY a single JSON object that "
    "matches the schema exactly. No prose, no code fences."
)

JSON_MODE_INSTRUCTION = (
    "Respond with ONLY a single JSON object that validates against this JSON "
    "Schema (no prose, no code fences):\n{schema}"
)


class LLMClient:
    """Async LLM calls with role config, structured outputs, ModelCall log.

    Cheap to build: config is resolved per call (env may change); one
    AsyncOpenAI per (base_url, api_key, model) is cached per instance
    (LLM-CONFIG-4). Tests inject `http_client` to mock the transport.
    """

    def __init__(
        self,
        http_client: httpx2.AsyncClient | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._http_client = http_client
        self._max_retries = max_retries
        self._sdk_clients: dict[tuple[str, str, str], AsyncOpenAI] = {}
        # LLM-CLIENT-3: per-role json_schema support, flipped off on 400/404
        self._json_schema_ok: dict[str, bool] = {}

    async def complete(
        self,
        role: str,
        messages: list[dict[str, str]],
        *,
        schema: type[BaseModel] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
        attempts: int = MAX_ATTEMPTS,
    ) -> str | BaseModel:
        """LLM-CLIENT-1: text (str) or schema-validated pydantic instance."""

        config = resolve_role_config(role)
        sdk = self._sdk_client(config)
        temp = temperature if temperature is not None else config.temperature

        if schema is None:
            return await self._complete_text(
                role=role,
                config=config,
                sdk=sdk,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
            )
        return await self._complete_structured(
            role=role,
            config=config,
            sdk=sdk,
            messages=messages,
            schema=schema,
            temperature=temp,
            max_tokens=max_tokens,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            attempts=attempts,
        )

    async def stream(
        self,
        role: str,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """LLM-STREAM-1..3: text deltas; one ModelCall row at stream end."""

        config = resolve_role_config(role)
        sdk = self._sdk_client(config)
        temp = temperature if temperature is not None else config.temperature

        started = time.perf_counter()
        usage = None
        error_text = ""
        status = ModelCall.Status.OK
        try:
            response = await sdk.chat.completions.create(
                model=config.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temp,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in response:
                if getattr(chunk, "usage", None) is not None:
                    usage = chunk.usage
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    yield delta
        except Exception as exc:
            # LLM-CLIENT-6: log then propagate as-is
            error_text = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT]
            status = ModelCall.Status.ERROR
            raise
        finally:
            await self._log(
                role=role,
                config=config,
                response_format=ModelCall.ResponseFormat.TEXT,
                attempts=1,
                status=status,
                latency_ms=_elapsed_ms(started),
                usage=usage,
                error=error_text,
            )

    async def _complete_text(
        self,
        *,
        role: str,
        config: RoleConfig,
        sdk: AsyncOpenAI,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
        prompt_name: str | None,
        prompt_version: str | None,
    ) -> str:
        started = time.perf_counter()
        error_text = ""
        status = ModelCall.Status.OK
        usage = None
        try:
            response = await sdk.chat.completions.create(
                model=config.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            usage = response.usage
            text = response.choices[0].message.content or ""
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT]
            status = ModelCall.Status.ERROR
            raise
        finally:
            await self._log(
                role=role,
                config=config,
                response_format=ModelCall.ResponseFormat.TEXT,
                attempts=1,
                status=status,
                latency_ms=_elapsed_ms(started),
                usage=usage,
                error=error_text,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
            )
        return text

    async def _complete_structured(
        self,
        *,
        role: str,
        config: RoleConfig,
        sdk: AsyncOpenAI,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        temperature: float | None,
        max_tokens: int | None,
        prompt_name: str | None,
        prompt_version: str | None,
        attempts: int,
    ) -> BaseModel:
        started = time.perf_counter()
        json_schema_ok = self._json_schema_ok.get(role, True)
        response_format = (
            ModelCall.ResponseFormat.JSON_SCHEMA
            if json_schema_ok
            else ModelCall.ResponseFormat.JSON_MODE
        )
        schema_note = [
            {
                "role": "user",
                "content": JSON_MODE_INSTRUCTION.format(
                    schema=json.dumps(schema.model_json_schema())
                ),
            }
        ]
        retry_extra: list[dict[str, str]] = []
        attempts_made = 1
        usage: CompletionUsage | None = None
        last_error = ""
        last_raw = ""

        async def log_outcome(
            status: str, error_text: str, final_usage: CompletionUsage | None
        ) -> None:
            await self._log(
                role=role,
                config=config,
                response_format=response_format,
                attempts=attempts_made,
                status=status,
                latency_ms=_elapsed_ms(started),
                usage=final_usage,
                error=error_text,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
            )

        for attempt in range(1, attempts + 1):
            attempts_made = attempt
            if json_schema_ok:
                # LLM-CLIENT-2: native structured output first
                request_messages = messages + retry_extra
                response_kwargs: dict[str, Any] = {
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema.__name__,
                            "strict": False,
                            "schema": schema.model_json_schema(),
                        },
                    }
                }
            else:
                # LLM-CLIENT-3: JSON-mode fallback (schema in messages)
                request_messages = messages + schema_note + retry_extra
                response_kwargs = {"response_format": {"type": "json_object"}}

            try:
                response = await sdk.chat.completions.create(
                    model=config.model,
                    messages=request_messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **response_kwargs,
                )
            except (BadRequestError, NotFoundError) as exc:
                if json_schema_ok:
                    # LLM-CLIENT-3: transparent downgrade; consumes the attempt
                    self._json_schema_ok[role] = False
                    json_schema_ok = False
                    response_format = ModelCall.ResponseFormat.JSON_MODE
                    last_error = f"json_schema rejected by endpoint: {exc}"[
                        :ERROR_TEXT_LIMIT
                    ]
                    continue
                # JSON-mode call itself rejected → propagate (LLM-CLIENT-6)
                error_text = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT]
                await log_outcome(ModelCall.Status.ERROR, error_text, usage)
                raise

            raw = response.choices[0].message.content or ""
            usage = response.usage
            last_raw = raw
            try:
                # LLM-CLIENT-4: client-side parse for both modes
                parsed = schema.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                # LLM-CLIENT-4/5: re-ask with the invalid output + error
                last_error = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT]
                retry_extra = _retry_messages(raw, last_error)
                continue
            await log_outcome(ModelCall.Status.OK, "", usage)
            return parsed

        message = (
            f"structured output for role {role!r} failed after "
            f"{attempts} attempts (last error: {last_error})"
        )
        await log_outcome(ModelCall.Status.ERROR, message[:ERROR_TEXT_LIMIT], usage)
        raise StructuredOutputError(
            message, last_error=last_error, raw_output=last_raw[:RAW_SNIPPET_LIMIT]
        )

    async def _log(
        self,
        *,
        role: str,
        config: RoleConfig,
        response_format: str,
        attempts: int,
        status: str,
        latency_ms: int,
        usage: CompletionUsage | None,
        error: str,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        """LLM-CALL-1/2/3: one row per invocation; keys never stored."""

        manager = ModelCall.objects  # type: ignore[unresolved-attribute]
        await sync_to_async(manager.create)(
            role=role,
            model=config.model,
            base_url=config.base_url,
            prompt_name=prompt_name or "",
            prompt_version=prompt_version or "",
            response_format=response_format,
            attempts=attempts,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            latency_ms=latency_ms,
            status=status,
            error=error[:ERROR_TEXT_LIMIT],
        )

    def _sdk_client(self, config: RoleConfig) -> AsyncOpenAI:
        key = (config.base_url, config.api_key, config.model)
        if key not in self._sdk_clients:
            kwargs: dict[str, Any] = {
                "base_url": config.base_url,
                "api_key": config.api_key,
            }
            if self._http_client is not None:
                kwargs["http_client"] = self._http_client
            if self._max_retries is not None:
                kwargs["max_retries"] = self._max_retries
            self._sdk_clients[key] = AsyncOpenAI(**kwargs)
        return self._sdk_clients[key]


def _retry_messages(raw: str, error: str) -> list[dict[str, str]]:
    """LLM-CLIENT-5: echo invalid output + concrete error as re-ask context."""

    return [
        {"role": "assistant", "content": raw if raw.strip() else "(empty response)"},
        {"role": "user", "content": RETRY_INSTRUCTION.format(error=error)},
    ]


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
