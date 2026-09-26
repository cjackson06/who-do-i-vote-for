"""Politician cache app: cited research corpus (specs/politicians.md)."""

from django.apps import AppConfig


class PoliticiansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.politicians"
