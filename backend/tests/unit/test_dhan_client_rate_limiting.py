"""Unit tests for DhanRestClient integration with rate limiter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.exceptions import DhanRateLimitError
from app.dhan.limiter import InMemoryTokenBucket
from app.dhan.limits_config import BackoffSpec, DhanLimitsConfig, RateLimitSpec
from app.dhan.transport import CassetteTransport
from pydantic import SecretStr

CASSETTES_DIR = Path(__file__).resolve().parents[1] / "cassettes" / "dhan"


class RecordingLimiter:
    """Mock rate limiter that records all acquire() calls."""

    def __init__(self) -> None:
        self.acquired: list[tuple[str, float, float]] = []

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        self.acquired.append((category, cost, timeout))
        return 0.0

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        return True

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        return {"category": category, "alert_80_pct": False}


@pytest.fixture
def client_with_recorder() -> tuple[DhanRestClient, RecordingLimiter]:
    recorder = RecordingLimiter()
    transport = CassetteTransport(cassette_dir=CASSETTES_DIR)
    creds = DhanCredentials(client_id="1000000001", access_token=SecretStr("mock_valid_token"))
    client = DhanRestClient(credentials=creds, transport=transport, limiter=recorder)
    return client, recorder


def test_client_routes_fund_limits_to_account_category(
    client_with_recorder: tuple[DhanRestClient, RecordingLimiter],
) -> None:
    client, recorder = client_with_recorder
    client.get_fund_limits()

    assert len(recorder.acquired) == 1
    category, cost, _timeout = recorder.acquired[0]
    assert category == "account_funds_holdings"
    assert cost == 1.0


def test_client_routes_historical_daily_to_historical_daily_category(
    client_with_recorder: tuple[DhanRestClient, RecordingLimiter],
) -> None:
    client, recorder = client_with_recorder
    client.get_historical_daily("1333", "NSE_EQ", "EQUITY", "2026-01-01", "2026-01-10")

    assert len(recorder.acquired) == 1
    category, cost, _timeout = recorder.acquired[0]
    assert category == "historical_daily"
    assert cost == 1.0


def test_client_routes_historical_intraday_to_historical_intraday_category(
    client_with_recorder: tuple[DhanRestClient, RecordingLimiter],
) -> None:
    client, recorder = client_with_recorder
    client.get_historical_intraday("1333", "NSE_EQ", "EQUITY", "2026-01-01", "2026-01-02", 1)

    assert len(recorder.acquired) == 1
    category, cost, _timeout = recorder.acquired[0]
    assert category == "historical_intraday"
    assert cost == 1.0


def test_client_raises_rate_limit_error_on_limiter_exhaustion() -> None:
    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=1.0, burst=1, description="Low burst"),
        backoff=BackoffSpec(base_delay_seconds=0.01, max_delay_seconds=0.05, jitter_ratio=0.1),
        categories={
            "account_funds_holdings": RateLimitSpec(rate=0.01, burst=1, description="Very slow")
        },
    )
    limiter = InMemoryTokenBucket(config)
    transport = CassetteTransport(cassette_dir=CASSETTES_DIR)
    creds = DhanCredentials(client_id="1000000001", access_token=SecretStr("mock_valid_token"))
    client = DhanRestClient(credentials=creds, transport=transport, limiter=limiter, timeout=0.05)

    # 1st call consumes the single token
    client.get_fund_limits()

    # 2nd call should time out quickly and raise DhanRateLimitError
    with pytest.raises(DhanRateLimitError):
        client.get_fund_limits()
