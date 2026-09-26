"""Read-only admin for the ModelCall log."""

from django.contrib import admin
from django.http import HttpRequest

from .models import ModelCall


@admin.register(ModelCall)
class ModelCallAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "model",
        "status",
        "attempts",
        "response_format",
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "created_at",
    )
    list_filter = ("role", "status", "response_format", "prompt_name")
    search_fields = ("model", "error")
    readonly_fields = (
        "role",
        "model",
        "base_url",
        "prompt_name",
        "prompt_version",
        "response_format",
        "attempts",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "latency_ms",
        "status",
        "error",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: ModelCall | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ModelCall | None = None
    ) -> bool:
        return False
