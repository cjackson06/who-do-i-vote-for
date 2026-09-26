"""LLM core app: model-agnostic client, role config, ModelCall log."""

from django.apps import AppConfig
from django.core.checks import register


class LlmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.llm"

    def ready(self) -> None:
        from .checks import llm_role_config_check

        register(llm_role_config_check)
