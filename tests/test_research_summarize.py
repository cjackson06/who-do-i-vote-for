"""Summarizer step — contract: specs/research.md (SUMMARIZER-*), llm prompt rules."""

import json
from datetime import timedelta

import httpx2
import pytest
from django.utils import timezone

from apps.llm.client import LLMClient
from apps.llm.prompts import research_summarizer as prompt
from apps.politicians.models import Politician, SourceRecord
from apps.research.schemas import PoliticianRef
from apps.research.summarize import TopicResult, profile_summary, summarize_topic

pytestmark = pytest.mark.django_db(transaction=True)

ROLE_ENV_FIELDS = ("BASE_URL", "API_KEY", "MODEL", "TEMPERATURE")


# LLM-PROMPT-1/2
def test_prompt_module_conventions() -> None:
    """LLM-PROMPT-1/2: NAME/VERSION exports; build_messages is pure."""
    assert isinstance(prompt.NAME, str) and prompt.NAME
    assert isinstance(prompt.VERSION, str) and prompt.VERSION

    findings = [
        {"url": "https://x.example/a", "title": "T", "content": "C", "first_hand": True}
    ]
    messages = prompt.build_messages(
        politician="Jane", topic="positions", findings=findings
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Jane" in messages[1]["content"]
    assert "https://x.example/a" in messages[1]["content"]
    assert "first_hand=yes" in messages[1]["content"]
    # prompt text lives in constants; no inline prose scattered
    assert "hearsay" in prompt.SYSTEM_PROMPT
    assert "Never invent" in prompt.SYSTEM_PROMPT


@pytest.fixture(autouse=True)
def summarizer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure only the summarizer role."""
    from apps.llm.config import ROLES

    for role in ROLES:
        for field in ROLE_ENV_FIELDS:
            monkeypatch.delenv(f"LLM_{role.upper()}_{field}", raising=False)
    monkeypatch.setenv("LLM_SUMMARIZER_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_SUMMARIZER_MODEL", "test-model")


# SUMMARIZER-1/3
async def test_summarize_topic_validates_citations(db) -> None:
    """SUMMARIZER-1/3: valid citations stored; unknown URLs dropped."""
    politician = await Politician.objects.acreate(name="Cite Person")
    record = await _make_record(politician)

    def handler(request: httpx2.Request) -> httpx2.Response:
        content = json.dumps(
            {
                "summary": "The politician said a thing.",
                "facts": [
                    {
                        "claim": "Said the thing",
                        "quote": "thing",
                        "source_url": "https://src.example/ok",
                    },
                    {
                        "claim": "Ghost claim",
                        "quote": "",
                        "source_url": "https://ghost.example/nope",
                    },
                ],
            }
        )
        return httpx2.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 1,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    llm = LLMClient(
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        max_retries=0,
    )
    result = await summarize_topic(
        llm,
        PoliticianRef(id=politician.pk, name=politician.name),
        "positions",
        [record],
    )
    assert result.dropped == 1
    assert len(result.facts) == 1
    claim, _quote, source_id = result.facts[0]
    assert claim == "Said the thing"
    assert source_id == record.pk


# SUMMARIZER-5
def test_profile_summary_joins_topic_headers() -> None:
    """SUMMARIZER-5: deterministic join under headers, no LLM call."""

    text = profile_summary(
        [
            TopicResult(topic="positions", summary="A."),
            TopicResult(topic="donations", summary="B."),
        ]
    )
    assert text == "## positions\nA.\n\n## donations\nB."


async def _make_record(politician: Politician) -> SourceRecord:
    now = timezone.now()
    url = "https://src.example/ok"
    return await SourceRecord.objects.acreate(
        politician=politician,
        source_type="tavily_web",
        topic="positions",
        url=url,
        url_hash=SourceRecord.url_hash_of(url),
        title="T",
        content="C",
        first_hand=True,
        retrieved_at=now,
        fresh_until=now + timedelta(days=30),
    )
