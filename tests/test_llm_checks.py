"""LLM startup check — contract: specs/llm.md (LLM-CHECK-1)."""

from django.core.checks import Error, Warning
from django.test import override_settings

from apps.llm.checks import E001, llm_role_config_check
from apps.llm.config import ROLES


def test_check_warns_under_debug(llm_env) -> None:
    """LLM-CHECK-1: DEBUG=True -> WARNING listing unconfigured roles.

    (pytest-django runs tests with DEBUG=False, so DEBUG is forced here.)
    """

    with override_settings(DEBUG=True):
        findings = llm_role_config_check()

    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, Warning)
    assert finding.id == E001
    assert "profiler" in finding.msg
    assert "researcher" not in finding.msg


def test_check_empty_when_all_configured(llm_env, monkeypatch) -> None:
    """LLM-CHECK-1: fully configured -> no findings."""

    for role in ROLES:
        monkeypatch.setenv(f"LLM_{role.upper()}_BASE_URL", "http://llm.test/v1")
        monkeypatch.setenv(f"LLM_{role.upper()}_MODEL", "test-model")

    assert llm_role_config_check() == []


def test_check_errors_in_prod(llm_env) -> None:
    """LLM-CHECK-1: DEBUG=False -> ERROR (prod entrypoint fails fast)."""

    with override_settings(DEBUG=False):
        findings = llm_role_config_check()

    assert len(findings) == 1
    assert isinstance(findings[0], Error)
    assert findings[0].id == E001
