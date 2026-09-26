"""Typed exceptions for the LLM layer (specs/llm.md)."""


class LLMError(Exception):
    """Base class for app-level LLM errors."""


class RoleNotConfigured(LLMError):
    """A role has no resolvable base_url/model (LLM-CONFIG-2)."""


class StructuredOutputError(LLMError):
    """Malformed/invalid output persisted past the attempt budget (LLM-CLIENT-5)."""

    def __init__(
        self, message: str, *, last_error: str = "", raw_output: str = ""
    ) -> None:
        super().__init__(message)
        self.last_error = last_error
        self.raw_output = raw_output
