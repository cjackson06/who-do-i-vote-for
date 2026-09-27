"""run_research task + admin trigger — contract: specs/research.md (RUN-*, TASK-*)."""

import json

import httpx2
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.llm.client import LLMClient
from apps.politicians.models import Politician
from apps.research.admin import enqueue_research
from apps.research.models import ResearchRun
from apps.research.schemas import FetchOutcome, RawFinding
from apps.research.tasks import run_research
from apps.research.topics import TOPICS

pytestmark = pytest.mark.django_db(transaction=True)

# S105-exempt: Django's password validator rejects real-looking strings;
# this is a throwaway test-fixture credential, not a secret.
TEST_PASSWORD = "test-only-password"  # noqa: S105


class FakeAdapter:
    def __init__(self, name: str, topics: tuple[str, ...]) -> None:
        self.name = name
        self.topics = topics
        self.calls: list[str] = []

    async def fetch(self, ref, topic: str) -> FetchOutcome:
        self.calls.append(topic)
        return FetchOutcome(
            findings=[
                RawFinding(
                    url=f"https://src.example/{topic}",
                    title="t",
                    content="text",
                    first_hand=True,
                )
            ]
        )


def _llm() -> LLMClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
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
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"summary": "S.", "facts": []}),
                        },
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

    return LLMClient(
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        max_retries=0,
    )


@pytest.fixture(autouse=True)
def summarizer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.llm.config import ROLES

    for role in ROLES:
        for field in ("BASE_URL", "API_KEY", "MODEL", "TEMPERATURE"):
            monkeypatch.delenv(f"LLM_{role.upper()}_{field}", raising=False)
    monkeypatch.setenv("LLM_SUMMARIZER_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_SUMMARIZER_MODEL", "test-model")


@pytest.fixture(autouse=True)
def clean_db(db) -> None:
    """Leaf-first cleanup (Fact→SourceRecord is PROTECT). Sync fixture:
    this module's TestCase tests write on the main-thread connection."""
    from apps.politicians.models import Fact, PoliticianProfile, SourceRecord

    Fact.objects.all().delete()  # type: ignore[unresolved-attribute]
    SourceRecord.objects.all().delete()  # type: ignore[unresolved-attribute]
    PoliticianProfile.objects.all().delete()  # type: ignore[unresolved-attribute]
    ResearchRun.objects.all().delete()  # type: ignore[unresolved-attribute]
    Politician.objects.all().delete()  # type: ignore[unresolved-attribute]


# RUN-2: task lifecycle
async def test_task_runs_full_lifecycle(db, monkeypatch) -> None:
    """RUN-2: queued → running → completed; swarm runs with registry lookup
    patched out (fake adapters)."""
    politician = await Politician.objects.acreate(name="Task Person")
    run = await ResearchRun.objects.acreate(politician=politician, topics=list(TOPICS))
    adapter = FakeAdapter("tavily_web", ("positions", "voting_record"))
    monkeypatch.setattr(
        "apps.research.swarm.available_adapters", lambda http_client=None: [adapter]
    )
    monkeypatch.setattr("apps.research.swarm.LLMClient", lambda **kwargs: _llm())

    await run_research.acall(politician.pk, run.pk)

    await run.arefresh_from_db()
    assert run.status == ResearchRun.Status.COMPLETED
    assert adapter.calls  # swarm actually fetched
    assert run.finished_at is not None


async def test_task_skips_nonqueued_run(db, monkeypatch) -> None:
    """RUN-2: a run that is not `queued` (stale duplicate) is a no-op."""
    politician = await Politician.objects.acreate(name="Stale Person")
    run = await ResearchRun.objects.acreate(
        politician=politician,
        topics=["positions"],
        status=ResearchRun.Status.RUNNING,
    )
    ran = False

    def fake_adapters(http_client=None):
        nonlocal ran
        ran = True
        return []

    monkeypatch.setattr("apps.research.swarm.available_adapters", fake_adapters)
    await run_research.acall(politician.pk, run.pk)
    assert not ran
    await run.arefresh_from_db()
    assert run.status == ResearchRun.Status.RUNNING  # untouched


async def test_task_marks_failed_and_reraises(db, monkeypatch) -> None:
    """RUN-2: unexpected swarm error → run failed with error text, re-raise."""
    politician = await Politician.objects.acreate(name="Boom Person")
    run = await ResearchRun.objects.acreate(politician=politician, topics=["positions"])

    def boom(ref, topics, **kwargs):
        raise RuntimeError("swarm exploded")

    monkeypatch.setattr("apps.research.tasks.research_politician", boom)
    with pytest.raises(RuntimeError, match="swarm exploded"):
        await run_research.acall(politician.pk, run.pk)
    await run.arefresh_from_db()
    assert run.status == ResearchRun.Status.FAILED
    assert "swarm exploded" in run.error


# RUN-1: admin trigger
@override_settings(
    TASKS={"default": {"BACKEND": "django.tasks.backends.dummy.DummyBackend"}}
)
class AdminTriggerTests(TestCase):
    """RUN-1: the admin action enqueues after commit (staff-only flow)."""

    def setUp(self) -> None:
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", password=TEST_PASSWORD, email="a@b.c"
        )
        self.client.force_login(self.superuser)
        self.politician = Politician.objects.create(name="Admin Person")

    def test_admin_action_creates_run_and_enqueues(self) -> None:
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(
                reverse("admin:politicians_politician_changelist"),
                {
                    "action": "run_research_action",
                    "_selected_action": [str(self.politician.pk)],
                },
                follow=True,
            )
        self.assertEqual(response.status_code, 200)
        run = ResearchRun.objects.get(politician=self.politician)
        self.assertEqual(run.status, ResearchRun.Status.QUEUED)
        self.assertEqual(run.topics, list(TOPICS))
        self.assertEqual(len(callbacks), 1)

        from django.tasks import task_backends

        dummy = task_backends["default"]
        self.assertEqual(len(dummy.results), 1)

    def test_enqueue_research_rejects_unknown_topics(self) -> None:
        with self.assertRaises(ValueError):
            enqueue_research(self.politician, topics=["bogus"])
