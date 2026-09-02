"""Disabled AI provider implementation, serving as safe default."""

from __future__ import annotations

from typing import Any

from app.ai.protocol import (
    AIProvider,
    AIResult,
    AIRuntimeDisabledError,
    ProviderStatus,
)


class DisabledProvider(AIProvider):
    """Default runtime provider ensuring product functions without external AI costs."""

    def generate_structured(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        timeout_s: float = 30.0,
    ) -> AIResult:
        """Reject generation attempts while provider remains disabled."""
        raise AIRuntimeDisabledError(
            "Product runtime AI is disabled by policy. "
            "To enable natural-language strategy generation, an approved provider "
            "adapter must be explicitly configured and authorized."
        )

    def get_status(self) -> ProviderStatus:
        """Report disabled status cleanly for health checks and UI banners."""
        return ProviderStatus(
            enabled=False,
            provider_name="DisabledProvider",
            status_message=(
                "Runtime AI generation is disabled by policy. "
                "No external API credentials or usage costs are active."
            ),
            auth_configured=False,
        )
