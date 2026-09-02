"""Product runtime AI provider protocol, data structures, and errors."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class AIRuntimeError(Exception):
    """Base exception for all product runtime AI errors."""


class AIRuntimeDisabledError(AIRuntimeError):
    """Raised when runtime AI generation is invoked while AI is disabled."""


class AITimeoutError(AIRuntimeError):
    """Raised when structured generation exceeds the configured timeout."""


class AISchemaValidationError(AIRuntimeError):
    """Raised when provider output does not conform to the requested schema."""


class AISecretLeakageError(AIRuntimeError):
    """Raised when a prompt contains unredacted credentials or secrets."""


class ProviderStatus(BaseModel):
    """Current runtime availability and configuration status of an AI provider."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    provider_name: str
    status_message: str
    auth_configured: bool = False


class AIResult(BaseModel):
    """Result of a structured AI generation call."""

    model_config = ConfigDict(extra="forbid")

    content: dict[str, Any]
    raw_text: str
    tokens_used: int = Field(ge=0)
    cost_estimate_usd: float = Field(ge=0.0)
    provider_name: str
    latency_ms: float = Field(ge=0.0)


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for product runtime AI generation providers."""

    def generate_structured(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        timeout_s: float = 30.0,
    ) -> AIResult:
        """Generate structured JSON adhering to the specified schema."""
        ...

    def get_status(self) -> ProviderStatus:
        """Return the current operational status of the provider."""
        ...
