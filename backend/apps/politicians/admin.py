"""Admin for the politician cache (specs/politicians.md).

`Politician` itself is registered by apps.research.admin, which owns the
"Run research" trigger (RUN-1) — a single registration, no override hack.
"""

from django.contrib import admin

from .models import Fact, PoliticianProfile, SourceRecord


@admin.register(PoliticianProfile)
class PoliticianProfileAdmin(admin.ModelAdmin):
    list_display = ("politician", "scope", "generated_at", "research_run")
    list_filter = ("scope",)
    search_fields = ("politician__name",)


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ("topic", "claim", "politician_name", "source_record")
    list_filter = ("topic",)
    search_fields = ("claim", "profile__politician__name")

    @admin.display(description="politician")
    def politician_name(self, obj: Fact) -> str:
        profile = obj.profile  # ty: relation descriptors resolve at runtime
        return str(profile.politician)  # ty: ignore[possibly-missing-attribute]


@admin.register(SourceRecord)
class SourceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "source_type",
        "topic",
        "url",
        "first_hand",
        "retrieved_at",
        "fresh_until",
    )
    list_filter = ("source_type", "first_hand", "topic")
    search_fields = ("url", "title")
