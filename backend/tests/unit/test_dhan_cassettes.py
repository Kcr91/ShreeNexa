"""Offline tests driven by recorded DhanHQ v2 cassettes.

The success and 401 cassettes are sanitized captures of real broker responses
(F0.5 acceptance). The 429, 503 and malformed-JSON cassettes stay constructed:
a healthy server will not emit them on demand.
"""

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


RECORDED_FIXTURES = {
    "historical_daily_success",
    "historical_intraday_success",
    "profile_success",
    "auth_failure_401",
}
# A healthy server will not emit these on demand, so they stay constructed.
CONSTRUCTED_FIXTURES = {
    "rate_limit_429",
    "server_error_503",
    "malformed_response",
}


def test_every_cassette_declares_its_provenance() -> None:
    """Each cassette must state whether it is a real capture or a constructed shape."""
    fixtures = sorted(CASSETTES_DIR.glob("*.json"))
    assert {f.stem for f in fixtures} == RECORDED_FIXTURES | CONSTRUCTED_FIXTURES

    for fixture in fixtures:
        metadata = json.loads(fixture.read_text(encoding="utf-8"))["_fixture"]
        recorded = metadata["recorded_broker_response"]

        if fixture.stem in RECORDED_FIXTURES:
            assert recorded is True, f"{fixture.stem} must be a recorded capture"
            assert metadata["classification"] == "recorded"
            assert metadata["source"] == "dhanhq_v2_live_api"
            assert metadata["recorded_at"]
        else:
            assert recorded is False, f"{fixture.stem} must not claim to be recorded"
            assert metadata["classification"] == "synthetic"


def test_no_cassette_leaks_account_identifiers() -> None:
    """Recorded captures must carry no live client id or token material."""
    for fixture in sorted(CASSETTES_DIR.glob("*.json")):
        raw = fixture.read_text(encoding="utf-8")
        document = json.loads(raw)
        if "dhanClientId" in document:
            assert document["dhanClientId"] == "0000000000"
        assert "Bearer " not in raw
        assert "eyJ" not in raw, f"{fixture.stem} appears to contain a JWT"


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
    # Monetary values are zeroed in the cassette; the point is that the recorded
    # field names parse into the model at all.
    assert fund_limit.available_balance == 0.0
    assert fund_limit.sod_limit == 0.0
    assert fund_limit.withdrawable_balance == 0.0

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
    assert len(chart_data.open) == 5
    assert len(chart_data.close) == 5
    assert chart_data.open[0] == 24077.55

    # Regression: the live API returns "timestamp" while the docs show "start_Time".
    # Before the alias fix this produced zero bars from every real response.
    bars = chart_data.to_bars()
    assert len(bars) == 5, "recorded 'timestamp' key must map onto start_time"
    assert bars[0].timestamp == 1788201000
    assert bars[0].open == 24077.55
    assert all(b.high >= b.low for b in bars)


def test_cassette_historical_intraday_success(cassette_client: DhanRestClient) -> None:
    chart_data = cassette_client.get_historical_intraday(
        security_id="1333",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
        from_date="2026-09-01",
        to_date="2026-09-01",
        interval=1,
    )
    assert len(chart_data.open) == 120
    assert chart_data.open[0] == 24077.55

    bars = chart_data.to_bars()
    assert len(bars) == 120
    assert bars[0].timestamp == 1788234300
    # One-minute spacing across the recorded session.
    assert bars[1].timestamp - bars[0].timestamp == 60
    assert all(b.high >= b.low for b in bars)


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
    # Real Dhan v2 returns DH-901 / Invalid_Authentication, not the shape the
    # previous synthetic fixture assumed.
    assert err.error_code == "DH-901"
    assert err.error_type == "Invalid_Authentication"
    assert err.is_retryable is False
    # Regression: live errors carry "errorMessage"; raise_for_status previously read
    # only remarks/message and fell back to a generic string.
    assert "invalid or expired" in err.message.lower()


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
