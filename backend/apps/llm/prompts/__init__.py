"""Prompt module conventions (specs/llm.md, LLM-PROMPT-*).

Prompt modules live in this package, one per prompt; each exports:

- `NAME: str` — stable identifier (stored on ModelCall for eval lineage)
- `VERSION: str` — bumped whenever the wording changes
- `build_messages(**ctx) -> list[ChatMessage]` — a PURE function returning
  the OpenAI-style message list; all prompt text lives in module-level
  constants; no I/O, no globals mutated, no client calls inside.

Prompt modules are added alongside the features that use them (research
swarm, profiler, matcher, ... land in Phases 2-3). Call sites pass
`NAME`/`VERSION` to `LLMClient.complete(..., prompt_name=, prompt_version=)`.
"""

from typing import TypedDict


class ChatMessage(TypedDict):
    """OpenAI-style chat message (LLM-PROMPT-1)."""

    role: str
    content: str
