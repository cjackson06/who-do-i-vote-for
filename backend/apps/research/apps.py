"""Research app: source adapters, swarm, summarizer, runs (specs/research.md)."""

from django.apps import AppConfig
from django.core.checks import register


class ResearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.research"

    def ready(self) -> None:
        from .checks import research_source_config_check

        register(research_source_config_check)
