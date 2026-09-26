"""System check for LLM role configuration (specs/llm.md, LLM-CHECK-1).

Severity ERROR when DEBUG=False (prod fail-fast via the container
entrypoint's `manage.py check`), WARNING under DEBUG.
"""

from django.conf import settings
from django.core.checks import Error, Warning

from .config import ROLES, configured_roles

E001 = "llm.E001"


def llm_role_config_check(**_kwargs: object) -> list[Error | Warning]:
    """One finding listing all unconfigured roles (never one per role)."""

    missing = [role for role in ROLES if role not in configured_roles()]
    if not missing:
        return []
    hint = (
        "Set LLM_<ROLE>_BASE_URL / LLM_<ROLE>_MODEL per role, or the "
        "LLM_BASE_URL / LLM_MODEL globals (specs/llm.md, LLM-CONFIG-2)."
    )
    message = f"LLM roles not configured: {', '.join(missing)}."
    if settings.DEBUG:
        return [Warning(message, hint=hint, id=E001)]
    return [Error(message, hint=hint, id=E001)]
