"""Factory and provider boundary for product runtime AI."""

from __future__ import annotations

import os

from app.ai.disabled import DisabledProvider
from app.ai.mock import MockProvider
from app.ai.protocol import AIProvider, AIRuntimeDisabledError


def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    """Instantiate the active AI provider according to system configuration.

    Runtime AI defaults to DisabledProvider to enforce zero unexpected API costs
    and complete isolation from development Codex sessions.
    """
    mode = (
        provider_name
        or os.environ.get("SHREENEXA_AI_PROVIDER", "disabled")
    ).lower().strip()

    if mode == "mock":
        return MockProvider()
    elif mode in ("disabled", "none", "default"):
        return DisabledProvider()
    else:
        # A real provider adapter requires an explicit recorded architecture/cost decision
        raise AIRuntimeDisabledError(
            f"Unsupported or unauthorized AI provider '{mode}'. "
            "Product runtime AI is disabled until a provider decision is approved."
        )
