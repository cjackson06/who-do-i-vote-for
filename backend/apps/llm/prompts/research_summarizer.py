"""Summarizer prompt: findings → topic summary + cited facts.

Contract: specs/llm.md (LLM-PROMPT-*) and specs/research.md (SUMMARIZER-*).
Pure module: no I/O, no globals mutated, prompt text in constants.
"""

from typing import Any

NAME = "research_summarizer"
VERSION = "1"

SYSTEM_PROMPT = """\
You are a nonpartisan political research editor. You condense raw source \
findings about a politician into a short factual summary and a list of \
cited facts for a voter-information product.

Rules:
1. Every fact MUST be backed by one of the numbered sources provided. Cite \
it by repeating the source URL exactly as given in the `source_url` field. \
Never invent, alter, or extrapolate URLs.
2. First-hand sources only: statements from the politician themselves \
(speeches, official sites, filings), official government records, or \
direct reporting of verifiable events. Reject hearsay, aggregation, \
editorializing, and "critics say" framing ("he said, she said").
3. Facts must be specific and attributable (what was said/done, where, \
when). No speculation, no opinion, no editorial voice, no spin in either \
direction.
4. If the findings do not support any fact worth recording, return an \
empty facts list and say so in the summary.
5. Stay strictly within what the sources state. Missing information stays \
missing; do not fill gaps from prior knowledge.
6. Write the summary in neutral encyclopedic prose (2-4 sentences), \
grounded in the same sources.

Respond with ONLY a single JSON object matching the requested schema.
"""

FINDINGS_HEADER = "SOURCES for {politician} — topic: {topic}:\n{findings_block}"
FINDING_LINE = "[{index}] url={url} first_hand={first_hand} published={published}\n\
    title: {title}\n    excerpt: {content}"

FOOTER = """\
Produce the JSON object now: {"summary": str,
 "facts": [{"claim": str, "quote": str, "source_url": str}, ...]}.
quote should be a short verbatim snippet copied from the source excerpt \
when possible (empty string if none)."""


def build_messages(
    *,
    politician: str,
    topic: str,
    findings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """LLM-PROMPT-2: interpolate context into module-level constants only."""
    lines = [
        FINDING_LINE.format(
            index=index,
            url=item.get("url", ""),
            first_hand="yes" if item.get("first_hand") else "no",
            published=item.get("published_date") or "unknown",
            title=item.get("title", ""),
            content=item.get("content", ""),
        )
        for index, item in enumerate(findings, start=1)
    ]
    findings_block = "\n".join(lines) if lines else "(no sources available)"
    findings_header = FINDINGS_HEADER.format(
        politician=politician, topic=topic, findings_block=findings_block
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{findings_header}\n\n{FOOTER}"},
    ]
