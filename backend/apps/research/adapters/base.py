"""SourceAdapter protocol and shared adapter helpers (specs/research.md)."""

import re
from typing import Protocol, runtime_checkable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx2

from ..errors import AdapterError
from ..schemas import FetchOutcome, PoliticianRef

SECRET_PARAMS = frozenset({"api_key", "apikey", "key", "token"})
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

_SECRET_IN_TEXT = re.compile(
    r"([?&])(" + "|".join(SECRET_PARAMS) + r")=([^&\s'\"]+)", re.IGNORECASE
)


def sanitize_url(url: str) -> str:
    """RUN-3: strip secret query params before any storage/logging."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    safe_query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in SECRET_PARAMS
        ]
    )
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, safe_query, parts.fragment)
    )


def redact_message(message: str) -> str:
    """Scrub secret-bearing query params from exception text (TAVILY-7)."""
    return _SECRET_IN_TEXT.sub(r"\1\2=***", message)


def is_retryable(status: int) -> bool:
    return status in RETRYABLE_STATUSES


@runtime_checkable
class SourceAdapter(Protocol):
    """Pluggable source; implements fetch() and returns FetchOutcome."""

    name: str
    topics: tuple[str, ...]

    def __init__(self, http_client: httpx2.AsyncClient) -> None: ...

    async def fetch(self, ref: PoliticianRef, topic: str) -> FetchOutcome: ...


def ensure_topic(adapter_name: str, topic: str, topics: tuple[str, ...]) -> None:
    if topic not in topics:
        raise AdapterError(adapter_name, f"topic {topic!r} not covered by this adapter")
