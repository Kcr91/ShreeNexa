"""Mock AI provider implementation for deterministic tests and offline fixtures."""

from __future__ import annotations

import json
import time
from typing import Any

from app.ai.accounting import usage_ledger
from app.ai.protocol import (
    AIProvider,
    AIResult,
    AISchemaValidationError,
    AITimeoutError,
    ProviderStatus,
)
from app.ai.redaction import redact_secrets
from app.strategy.ir import StrategyIR


class MockProvider(AIProvider):
    """Deterministic mock provider generating schema-conforming StrategyIR drafts."""

    def __init__(
        self,
        *,
        canned_response: dict[str, Any] | None = None,
        simulated_latency_ms: float = 12.0,
    ) -> None:
        self.canned_response = canned_response
        self.simulated_latency_ms = simulated_latency_ms

    def generate_structured(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        timeout_s: float = 30.0,
    ) -> AIResult:
        """Generate structured StrategyIR conforming to schema."""
        start_time = time.perf_counter()

        if timeout_s <= 0.0:
            raise AITimeoutError(
                f"AI generation timed out after requested {timeout_s}s."
            )

        # Always scrub any secrets from prompt before processing
        scrubbed_prompt = redact_secrets(prompt)

        # Generate payload
        if self.canned_response is not None:
            raw_content = self.canned_response
        else:
            raw_content = {
                "schema_version": "1.0",
                "ir_version": 1,
                "name": "Mock AI Strategy Draft",
                "kind": "stock",
                "author": "AI Generator",
                "description": "Deterministic mock strategy for testing",
                "asset_class": "equity",
                "horizon": "positional",
                "strategy_type": "trend_following",
                "universe": {
                    "type": "static",
                    "instruments": [{"segment": "NSE_EQ", "security_id": "RELIANCE"}],
                },
                "timeframe": "1d",
                "indicators": {
                    "fast_ema": {
                        "fn": "EMA",
                        "inputs": {"field": "close"},
                        "params": {"period": 9},
                    }
                },
                "entries": [
                    {
                        "id": "entry_1",
                        "side": "BUY",
                        "when": {
                            "node": "IndicatorCompare",
                            "left": {"field": "close"},
                            "op": ">",
                            "right": 0.0,
                        },
                    }
                ],
                "exits": [],
                "sizing": {"type": "fixed_qty", "qty": 100},
            }

        # Check required schema fields if specified in schema
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in raw_content:
                raise AISchemaValidationError(
                    f"Generated content missing required schema field: {field}"
                )

        # Verify it validates as canonical StrategyIR
        try:
            StrategyIR.from_dict(raw_content)
        except Exception as exc:
            raise AISchemaValidationError(
                f"Generated content failed StrategyIR model validation: {exc}"
            ) from exc

        elapsed_ms = (time.perf_counter() - start_time) * 1000 + self.simulated_latency_ms
        tokens_used = len(scrubbed_prompt.split()) * 2 + 150
        cost_usd = tokens_used * 0.000002

        # Record accounting
        usage_ledger.record_call(
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            latency_ms=elapsed_ms,
        )

        return AIResult(
            content=raw_content,
            raw_text=json.dumps(raw_content, indent=2),
            tokens_used=tokens_used,
            cost_estimate_usd=round(cost_usd, 6),
            provider_name="MockProvider",
            latency_ms=round(elapsed_ms, 2),
        )

    def get_status(self) -> ProviderStatus:
        """Report mock provider operational status."""
        return ProviderStatus(
            enabled=True,
            provider_name="MockProvider",
            status_message="Deterministic mock provider active for test scenarios.",
            auth_configured=True,
        )
