"""Unit tests for DhanRestClient and error handling with mock transport."""

from __future__ import annotations

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanClientError,
    DhanMalformedResponseError,
    DhanRateLimitError,
    DhanServerError,
)
from app.dhan.transport import MockTransport
from pydantic import SecretStr


@pytest.fixture
def sample_creds() -> DhanCredentials:
    return DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("test_invalid_dhan_access_token"),
        source="environment",
    )


def test_client_initialization_without_credentials() -> None:
    mock_transport = MockTransport()
    client = DhanRestClient(credentials=None, transport=mock_transport)
    assert "[NONE]" in repr(client)
    assert "[NONE]" in str(client)

    with pytest.raises(DhanAuthenticationError, match="No Dhan credentials"):
        client.get_fund_limits()


def test_mock_transport_success_fund_limits(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "fundlimit",
        status_code=200,
        body={
            "status": "success",
            "data": {
                "dhanClientId": "0000000000",
                "availabelBalance": 125000.75,
                "sodLimit": 125000.75,
                "withdrawableBalance": 100000.0,
            },
        },
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    limits = client.get_fund_limits()
    assert limits.client_id == "0000000000"
    assert limits.available_balance == 125000.75
    assert limits.withdrawable_balance == 100000.0

    profile = client.get_profile()
    assert profile.client_id == "0000000000"
    assert profile.active is True
    assert profile.fund_limit is not None


def test_mock_transport_auth_failure_401(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "fundlimit",
        status_code=401,
        body={
            "status": "failure",
            "remarks": "Invalid token or expired authorization header",
            "errorCode": "RS-9005",
        },
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    with pytest.raises(DhanAuthenticationError) as exc_info:
        client.get_fund_limits()

    err = exc_info.value
    assert err.status_code == 401
    assert err.error_code == "RS-9005"
    assert err.is_retryable is False


def test_mock_transport_rate_limit_429(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "charts/historical",
        status_code=429,
        body={"status": "failure", "remarks": "Rate limit exceeded for IP"},
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    with pytest.raises(DhanRateLimitError) as exc_info:
        client.get_historical_daily(
            security_id="1333",
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
            from_date="2026-08-01",
            to_date="2026-08-31",
        )

    err = exc_info.value
    assert err.status_code == 429
    assert err.is_retryable is True


def test_mock_transport_server_error_503(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "charts/intraday",
        status_code=503,
        body={"status": "failure", "remarks": "Backend service busy"},
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    with pytest.raises(DhanServerError) as exc_info:
        client.get_historical_intraday(
            security_id="1333",
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
            from_date="2026-09-01",
            to_date="2026-09-01",
        )

    err = exc_info.value
    assert err.status_code == 503
    assert err.is_retryable is True


def test_mock_transport_timeout_error(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "marketfeed/quote",
        exception=TimeoutError("Socket read timed out"),
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    with pytest.raises(TimeoutError):
        client.get_quote(security_id="1333", exchange_segment="NSE_EQ")


def test_mock_transport_client_error_400(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "holdings",
        status_code=400,
        body={"status": "failure", "remarks": "Bad request parameters"},
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    with pytest.raises(DhanClientError) as exc_info:
        client.get_holdings()

    err = exc_info.value
    assert err.status_code == 400
    assert err.is_retryable is False


def test_mock_transport_malformed_json(sample_creds: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "positions",
        status_code=200,
        body="<html>502 Bad Gateway Nginx</html>",
    )

    client = DhanRestClient(credentials=sample_creds, transport=mock_transport)
    with pytest.raises(DhanMalformedResponseError) as exc_info:
        client.get_positions()

    err = exc_info.value
    assert err.is_retryable is False


def test_secret_redaction_in_exceptions() -> None:
    raw_secret_token = "dhan_live_token_secret_abcdef123456"
    message_with_secret = f"Authorization failed with token {raw_secret_token}"
    err = DhanAuthenticationError(message_with_secret, status_code=401)

    err_str = str(err)
    err_repr = repr(err)

    assert raw_secret_token not in err_str
    assert raw_secret_token not in err_repr
    assert "[REDACTED]" in err_str
