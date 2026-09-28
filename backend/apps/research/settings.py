"""Research source configuration (specs/research.md, SETTINGS-6).

Thin typed access to the Settings fields; adapters and the registry read
through here so env-vs-`.env` precedence stays in one place. Missing keys
mean the adapter is skipped (research.W001/W002), never a crash.
"""

from dataclasses import dataclass

DEMO_KEY = "DEMO_KEY"


def tavily_api_key() -> str | None:
    from django.conf import settings

    return settings.TAVILY_API_KEY


def tavily_base_url() -> str:
    from django.conf import settings

    return settings.TAVILY_BASE_URL


def fec_api_key() -> str | None:
    from django.conf import settings

    return settings.FEC_API_KEY


def fec_base_url() -> str:
    from django.conf import settings

    return settings.FEC_BASE_URL


def fec_demo() -> bool:
    from django.conf import settings

    return bool(settings.FEC_DEMO)


def tavily_configured() -> bool:
    return bool(tavily_api_key())


def fec_configured() -> bool:
    return bool(fec_api_key()) or fec_demo()


@dataclass(frozen=True)
class FECConfig:
    api_key: str
    base_url: str


def fec_settings() -> FECConfig:
    """FEC config; DEMO_KEY opt-in wired via FEC_DEMO=1 (FEC-3)."""
    key = fec_api_key() or (DEMO_KEY if fec_demo() else None)
    if not key:
        raise RuntimeError("FEC adapter queried while unconfigured (FEC-3)")
    return FECConfig(api_key=key, base_url=fec_base_url())
