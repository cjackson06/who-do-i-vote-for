"""Admin for the politician cache (Phase 2: browse; Phase 3: trigger)."""

from django.contrib import admin

from .models import Fact, Politician, PoliticianProfile, SourceRecord


@admin.register(Politician)
class PoliticianAdmin(admin.ModelAdmin):
    list_display = ("name", "party", "office", "state", "fec_candidate_id")
    list_filter = ("party", "state")
    search_fields = ("name", "fec_candidate_id")
    readonly_fields = ("created_at", "updated_at")
    inlines: list[type[admin.TabularInline]] = []


@admin.register(PoliticianProfile)
class PoliticianProfileAdmin(admin.ModelAdmin):
    list_display = ("politician", "scope", "generated_at")
    list_filter = ("scope",)
    search_fields = ("politician__name",)


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ("topic", "claim", "politician_name")
    list_filter = ("topic",)
    search_fields = ("claim", "profile__politician__name")

    @admin.display(description="politician")
    def politician_name(self, obj: Fact) -> str:
        return str(obj.profile.politician)


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
