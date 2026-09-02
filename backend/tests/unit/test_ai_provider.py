"""Unit and contract tests for product runtime AIProvider and boundary."""

from __future__ import annotations

import pytest
from app.ai import (
    AIRuntimeDisabledError,
    AISchemaValidationError,
    AITimeoutError,
    DisabledProvider,
    MockProvider,
    contains_secret,
    get_ai_provider,
    redact_secrets,
    usage_ledger,
)
from app.strategy.ir import StaticUniverse, StrategyIR


def test_disabled_provider_reports_clean_status_and_rejects_calls() -> None:
    provider = DisabledProvider()
    status = provider.get_status()

    assert status.enabled is False
    assert status.provider_name == "DisabledProvider"
    assert "disabled by policy" in status.status_message.lower()
    assert status.auth_configured is False

    with pytest.raises(AIRuntimeDisabledError) as exc_info:
        provider.generate_structured("Create an EMA cross strategy", schema={})

    assert "disabled by policy" in str(exc_info.value)


def test_mock_provider_generates_schema_valid_strategy_ir() -> None:
    usage_ledger.reset()
    provider = MockProvider()
    status = provider.get_status()

    assert status.enabled is True
    assert status.provider_name == "MockProvider"

    schema = {
        "required": ["ir_version", "name", "kind", "universe", "indicators", "entries", "exits"]
    }
    result = provider.generate_structured(
        prompt="Design a 5-minute intraday momentum strategy for NIFTY",
        schema=schema,
        timeout_s=10.0,
    )

    assert result.provider_name == "MockProvider"
    assert result.tokens_used > 0
    assert result.cost_estimate_usd >= 0.0
    assert result.latency_ms > 0

    # Ensure generated content strictly validates as StrategyIR
    strategy = StrategyIR.from_dict(result.content)
    assert strategy.ir_version == 1
    assert strategy.kind.value == "stock"
    assert isinstance(strategy.universe, StaticUniverse)
    assert len(strategy.universe.instruments) > 0
    assert "fast_ema" in strategy.indicators
    assert len(strategy.entries) > 0

    # Verify usage accounting
    summary = usage_ledger.get_summary()
    assert summary.total_calls == 1
    assert summary.total_tokens == result.tokens_used


def test_mock_provider_schema_validation_failure() -> None:
    invalid_canned = {
        "ir_version": 1,
        "name": "Broken Strategy",
        # Missing required StrategyIR fields
    }
    provider = MockProvider(canned_response=invalid_canned)

    with pytest.raises(AISchemaValidationError):
        provider.generate_structured(
            "Give me a strategy",
            schema={"required": ["universe"]},
        )


def test_mock_provider_timeout_enforcement() -> None:
    provider = MockProvider()
    with pytest.raises(AITimeoutError) as exc_info:
        provider.generate_structured("Test prompt", schema={}, timeout_s=0.0)

    assert "timed out" in str(exc_info.value)


def test_secret_redaction_scrubs_credentials_and_tokens() -> None:
    sample_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    prompt_with_secrets = (
        f"Strategy query: client_id=1100234589 with token Bearer abc123def456 and JWT {sample_jwt} "
        "and password=SuperSecretPassword123! and api_key=dhan_live_secret_key_889900"
    )

    assert contains_secret(prompt_with_secrets) is True

    scrubbed = redact_secrets(prompt_with_secrets)

    # Ensure no secret strings remain in scrubbed text
    assert "1100234589" not in scrubbed
    assert "SuperSecretPassword123!" not in scrubbed
    assert "dhan_live_secret_key_889900" not in scrubbed
    assert sample_jwt not in scrubbed
    assert "[REDACTED_JWT]" in scrubbed
    assert "client_id=[REDACTED]" in scrubbed
    assert "password=[REDACTED]" in scrubbed
    assert "api_key=[REDACTED]" in scrubbed


def test_provider_factory_boundaries() -> None:
    # Default is DisabledProvider
    default_p = get_ai_provider()
    assert isinstance(default_p, DisabledProvider)

    # Explicit mock
    mock_p = get_ai_provider("mock")
    assert isinstance(mock_p, MockProvider)

    # Unauthorized provider throws AIRuntimeDisabledError
    with pytest.raises(AIRuntimeDisabledError):
        get_ai_provider("openai")
