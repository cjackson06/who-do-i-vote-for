"""Adapter registry (specs/research.md, Registry).

Adding an adapter = new module implementing the protocol + one entry here.
No orchestrator edits (exit criterion).
"""

from typing import TYPE_CHECKING

import httpx2

from .adapters.fec import FECAdapter
from .adapters.tavily import TavilyAdapter
from .settings import fec_configured, tavily_configured
from .topics import (
    CONTROVERSIES,
    POSITIONS,
    VOTING_RECORD,
)

if TYPE_CHECKING:
    from .adapters.base import SourceAdapter

CLIENT_TIMEOUT_SECONDS = 40.0


def available_adapters(
    http_client: httpx2.AsyncClient | None = None,
) -> list["SourceAdapter"]:
    """Adapters whose source is configured (unconfigured → skipped)."""
    client = http_client or httpx2.AsyncClient(timeout=CLIENT_TIMEOUT_SECONDS)
    adapters: list[SourceAdapter] = []
    if tavily_configured():
        adapters.append(
            TavilyAdapter(
                client,
                name="tavily_web",
                topics=(POSITIONS, VOTING_RECORD),
                tavily_topic="general",
            )
        )
        adapters.append(
            TavilyAdapter(
                client,
                name="tavily_news",
                topics=(CONTROVERSIES,),
                tavily_topic="news",
                time_range="year",
            )
        )
    if fec_configured():
        adapters.append(FECAdapter(client))
    return adapters
