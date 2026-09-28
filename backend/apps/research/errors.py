"""Research errors (specs/research.md, Errors table)."""


class ResearchError(Exception):
    """Base class for app-level research errors."""


class AdapterError(ResearchError):
    """A source adapter exhausted its budget or hit a non-retryable failure."""

    def __init__(self, adapter: str, message: str) -> None:
        super().__init__(f"adapter {adapter!r}: {message}")
        self.adapter = adapter
