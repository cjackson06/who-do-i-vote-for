"""Role-config resolution — contract: specs/llm.md (LLM-CONFIG-1/2)."""

import pytest

from apps.llm.config import configured_roles, resolve_role_config
from apps.llm.exceptions import RoleNotConfigured


def test_role_specific_beats_global(llm_env, monkeypatch) -> None:
    """LLM-CONFIG-2: LLM_<ROLE>_* wins over LLM_* globals."""

    monkeypatch.setenv("LLM_BASE_URL", "http://global.test/v1")
    monkeypatch.setenv("LLM_MODEL", "global-model")

    config = resolve_role_config("researcher")

    assert config.base_url == "http://llm.test/v1"
    assert config.model == "test-model"
    assert config.api_key == "test-key"


def test_global_fallback_and_empty_api_key_default(llm_env, monkeypatch) -> None:
    """LLM-CONFIG-2: globals fill gaps; missing api_key defaults to EMPTY."""

    monkeypatch.setenv("LLM_BASE_URL", "http://global.test/v1")
    monkeypatch.setenv("LLM_MODEL", "global-model")

    config = resolve_role_config("profiler")

    assert config.base_url == "http://global.test/v1"
    assert config.model == "global-model"
    assert config.api_key == "EMPTY"


def test_missing_config_raises_role_not_configured(llm_env) -> None:
    """LLM-CONFIG-2: no role vars, no globals -> RoleNotConfigured."""

    with pytest.raises(RoleNotConfigured, match="profiler"):
        resolve_role_config("profiler")


def test_unknown_role_raises_value_error(llm_env) -> None:
    """LLM-CONFIG-1: the role set is closed."""

    with pytest.raises(ValueError, match="Unknown LLM role"):
        resolve_role_config("hacker")


def test_temperature_parsing(llm_env, monkeypatch) -> None:
    """LLM-CONFIG-2: temperature float; junk value is a loud error."""

    monkeypatch.setenv("LLM_RESEARCHER_TEMPERATURE", "0.4")
    assert resolve_role_config("researcher").temperature == 0.4

    monkeypatch.setenv("LLM_RESEARCHER_TEMPERATURE", "bogus")
    with pytest.raises(ValueError, match="not a float"):
        resolve_role_config("researcher")


def test_configured_roles_helper(llm_env) -> None:
    """LLM-CHECK-1: only roles with resolvable config are reported."""

    assert configured_roles() == ("researcher",)
