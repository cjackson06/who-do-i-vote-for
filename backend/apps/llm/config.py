"""Role configuration resolved from env (specs/llm.md, LLM-CONFIG-*)."""

import os

from pydantic import BaseModel

from .exceptions import RoleNotConfigured

ROLES: tuple[str, ...] = (
    "profiler",
    "researcher",
    "summarizer",
    "matcher",
    "recommender",
    "judge",
)


class RoleConfig(BaseModel):
    """One role's OpenAI-compatible endpoint configuration."""

    base_url: str
    api_key: str = "EMPTY"
    model: str
    temperature: float | None = None


def _role_env(role: str, field: str) -> str | None:
    """Role-specific env value (LLM_<ROLE>_<FIELD>), if set non-empty."""

    return os.getenv(f"LLM_{role.upper()}_{field}") or None


def resolve_role_config(role: str) -> RoleConfig:
    """Resolve a role's config (LLM-CONFIG-2); role-specific beats global.

    Raises RoleNotConfigured when base_url/model are missing, ValueError for
    unknown roles (LLM-CONFIG-1). Never exposes api_key values in errors.
    """

    if role not in ROLES:
        raise ValueError(f"Unknown LLM role: {role!r}")

    base_url = _role_env(role, "BASE_URL") or os.getenv("LLM_BASE_URL")
    model = _role_env(role, "MODEL") or os.getenv("LLM_MODEL")
    if not base_url or not model:
        raise RoleNotConfigured(
            f"LLM role {role!r} is not configured: set LLM_{role.upper()}_BASE_URL "
            f"and LLM_{role.upper()}_MODEL (or the LLM_BASE_URL / LLM_MODEL globals)."
        )

    api_key = _role_env(role, "API_KEY") or os.getenv("LLM_API_KEY") or "EMPTY"
    temp_raw = _role_env(role, "TEMPERATURE") or os.getenv("LLM_TEMPERATURE")
    temperature = None
    if temp_raw is not None:
        try:
            temperature = float(temp_raw)
        except ValueError as exc:
            raise ValueError(
                f"LLM temperature for role {role!r} is not a float: {temp_raw!r}"
            ) from exc

    return RoleConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
    )


def configured_roles() -> tuple[str, ...]:
    """Roles with fully resolvable config (used by checks, LLM-CHECK-1)."""

    ok = []
    for role in ROLES:
        try:
            resolve_role_config(role)
        except RoleNotConfigured:
            continue
        ok.append(role)
    return tuple(ok)
