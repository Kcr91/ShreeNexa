"""Offline tests driven by deterministic synthetic Dhan-shaped fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanMalformedResponseError,
    DhanRateLimitError,
    DhanServerError,
)
from app.dhan.transport import CassetteTransport
from pydantic import SecretStr

CASSETTES_DIR = Path(__file__).resolve().parents[1] / "cassettes" / "dhan"


def test_all_cassette_fixtures_are_explicitly_synthetic() -> None:
    fixtures = sorted(CASSETTES_DIR.glob("*.json"))
    assert len(fixtures) == 7
    for fixture in fixtures:
        document = json.loads(fixture.read_text(encoding="utf-8"))
        metadata = document["_fixture"]
        assert metadata == {
            "classification": "synthetic",
            "source": "generated_during_development",
            "recorded_broker_response": False,
            "account_id": "0000000000",
            "credential_profile": "invalid_test_only",
        }


@pytest.fixture
def cassette_client() -> DhanRestClient:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("test_invalid_dhan_access_token"),
        source="environment",
    )
    transport = CassetteTransport(CASSETTES_DIR)
    return DhanRestClient(credentials=creds, transport=transport)


def test_cassette_profile_success(cassette_client: DhanRestClient) -> None:
    fund_limit = cassette_client.get_fund_limits()
    assert fund_limit.client_id == "0000000000"
    assert fund_limit.available_balance == 250000.5
    assert fund_limit.sod_limit == 250000.5
    assert fund_limit.collateral_amount == 50000.0
    assert fund_limit.utilized_amount == 15000.25
    assert fund_limit.withdrawable_balance == 235000.25

    profile = cassette_client.get_profile()
    assert profile.client_id == "0000000000"
    assert profile.active is True
    assert profile.fund_limit is not None


def test_cassette_historical_daily_success(cassette_client: DhanRestClient) -> None:
    chart_data = cassette_client.get_historical_daily(
        security_id="1333",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
        from_date="2026-08-01",
        to_date="2026-08-31",
    )
    assert len(chart_data.open) == 3
    assert len(chart_data.close) == 3
    assert chart_data.open[0] == 24500.0
    assert chart_data.close[-1] == 24700.0
    assert chart_data.volume[0] == 150000

    bars = chart_data.to_bars()
    assert len(bars) == 3
    assert bars[0].timestamp == 1725148800
    assert bars[0].open == 24500.0
    assert bars[0].close == 24600.0
    assert bars[0].volume == 150000


def test_cassette_historical_intraday_success(cassette_client: DhanRestClient) -> None:
    chart_data = cassette_client.get_historical_intraday(
        security_id="1333",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
        from_date="2026-09-01",
        to_date="2026-09-01",
        interval=1,
    )
    assert len(chart_data.open) == 2
    assert chart_data.open[0] == 24500.0
    assert chart_data.close[1] == 24525.0

    bars = chart_data.to_bars()
    assert len(bars) == 2
    assert bars[0].timestamp == 1725162600
    assert bars[1].timestamp == 1725162660


def test_cassette_auth_failure_401() -> None:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("test_invalid_dhan_access_token"),
        source="environment",
    )
    transport = CassetteTransport(CASSETTES_DIR)
    transport.register_cassette("fundlimit", CASSETTES_DIR / "auth_failure_401.json")
    client = DhanRestClient(credentials=creds, transport=transport)

    with pytest.raises(DhanAuthenticationError) as exc_info:
        client.get_fund_limits()

    err = exc_info.value
    assert err.status_code == 401
    assert err.error_code == "RS-9005"
    assert err.is_retryable is False


def test_cassette_rate_limit_429() -> None:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("test_invalid_dhan_access_token"),
        source="environment",
    )
    transport = CassetteTransport(CASSETTES_DIR)
    transport.register_cassette("fundlimit", CASSETTES_DIR / "rate_limit_429.json")
    client = DhanRestClient(credentials=creds, transport=transport)

    with pytest.raises(DhanRateLimitError) as exc_info:
        client.get_fund_limits()

    err = exc_info.value
    assert err.status_code == 429
    assert err.error_code == "DH-429"
    assert err.is_retryable is True


def test_cassette_server_error_503() -> None:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("test_invalid_dhan_access_token"),
        source="environment",
    )
    transport = CassetteTransport(CASSETTES_DIR)
    transport.register_cassette("fundlimit", CASSETTES_DIR / "server_error_503.json")
    client = DhanRestClient(credentials=creds, transport=transport)

    with pytest.raises(DhanServerError) as exc_info:
        client.get_fund_limits()

    err = exc_info.value
    assert err.status_code == 503
    assert err.error_code == "DH-503"
    assert err.is_retryable is True


def test_cassette_malformed_response() -> None:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("test_invalid_dhan_access_token"),
        source="environment",
    )
    transport = CassetteTransport(CASSETTES_DIR)
    transport.register_cassette("fundlimit", CASSETTES_DIR / "malformed_response.json")
    client = DhanRestClient(credentials=creds, transport=transport)

    with pytest.raises(DhanMalformedResponseError) as exc_info:
        client.get_fund_limits()

    err = exc_info.value
    assert err.is_retryable is False
