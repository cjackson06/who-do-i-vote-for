"""System checks for research source configuration (specs/research.md).

Sources are optional-but-primary: a missing key disables the adapter and is
reported always with WARNING severity (the app boots, research just can't
start) — unlike LLM roles, whose absence ever fails prod fast.
"""

from django.core.checks import Warning

W001 = "research.W001"
W002 = "research.W002"


def research_source_config_check(**_kwargs: object) -> list[Warning]:
    """One finding per disabled source adapter."""
    warnings: list[Warning] = []
    from .settings import fec_configured, tavily_configured

    if not tavily_configured():
        warnings.append(
            Warning(
                "TAVILY_API_KEY is not set; the Tavily source adapter is "
                "disabled (web/news research will be unavailable).",
                hint="Set TAVILY_API_KEY in the environment or .env "
                "(specs/research.md, Env table).",
                id=W001,
            )
        )
    if not fec_configured():
        warnings.append(
            Warning(
                "FEC_API_KEY is not set; the FEC source adapter is disabled "
                "(donations will be unavailable: set FEC_API_KEY; DEMO_KEY "
                "requires FEC_DEMO=1).",
                id=W002,
            )
        )
    return warnings
