"""Unit tests for the charts/rollingoption client method and open-interest plumbing."""

from __future__ import annotations

import json
from typing import Any

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.limits_config import get_category_for_endpoint
from app.dhan.models import DhanHistoricalData, DhanRollingOptionData
from app.dhan.transport import MockTransport
from pydantic import SecretStr


class CapturingTransport:
    """Mock transport recording the request it was handed."""

    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body
        self.last_json: dict[str, Any] | None = None
        self.last_path: str | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> tuple[int, dict[str, str], bytes]:
        self.last_json = json_data
        self.last_path = path
        return 200, {"Content-Type": "application/json"}, json.dumps(self.body).encode()


class PermissiveLimiter:
    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        return 0.0

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        return True

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        return {}


LEG = {
    "open": [120.0, 125.0],
    "high": [130.0, 128.0],
    "low": [118.0, 122.0],
    "close": [126.0, 124.0],
    "volume": [1500, 2200],
    "oi": [50000, 52000],
    "iv": [14.5, 14.8],
    "spot": [24980.0, 24995.0],
    "strike": [25000.0, 25000.0],
    "timestamp": [1785642300, 1785642360],
}


def build_client(transport: Any) -> DhanRestClient:
    return DhanRestClient(
        credentials=DhanCredentials(client_id="0000000000", access_token=SecretStr("t")),
        transport=transport,
        limiter=PermissiveLimiter(),
    )


class TestRollingOptionRequest:
    def test_builds_the_documented_payload(self) -> None:
        transport = CapturingTransport({"ce": LEG, "pe": LEG})
        client = build_client(transport)

        client.get_rolling_option_history(
            "13",
            from_date="2026-01-01",
            to_date="2026-02-14",
            instrument="OPTIDX",
            expiry_flag="WEEK",
            expiry_code=1,
            strike="ATM+3",
            option_type="CALL",
        )

        assert transport.last_path == "charts/rollingoption"
        sent = transport.last_json
        assert sent is not None
        assert sent["securityId"] == "13"
        assert sent["exchangeSegment"] == "NSE_FNO"
        assert sent["instrument"] == "OPTIDX"
        assert sent["expiryFlag"] == "WEEK"
        assert sent["expiryCode"] == 1
        assert sent["strike"] == "ATM+3"
        assert sent["drvOptionType"] == "CALL"
        assert sent["interval"] == "1"
        assert sent["fromDate"] == "2026-01-01"
        assert sent["toDate"] == "2026-02-14"

    def test_requests_iv_oi_and_spot_by_default(self) -> None:
        """These three are the reason to use rollingoption at all."""
        transport = CapturingTransport({"ce": LEG, "pe": LEG})
        client = build_client(transport)

        client.get_rolling_option_history("13", from_date="2026-01-01", to_date="2026-01-10")

        sent = transport.last_json
        assert sent is not None
        for field in ("iv", "oi", "spot", "strike"):
            assert field in sent["requiredData"]

    def test_option_type_is_always_sent(self) -> None:
        """drvOptionType is required by the live API despite the docs marking it optional.

        Omitting it returns DH-905 "drvOptionType is required", verified against the
        live API. Only the requested leg is populated, so a full CE+PE chain costs two
        calls per strike rather than one.
        """
        transport = CapturingTransport({"ce": LEG, "pe": None})
        client = build_client(transport)

        client.get_rolling_option_history("13", from_date="2026-01-01", to_date="2026-01-10")

        sent = transport.last_json
        assert sent is not None
        assert sent["drvOptionType"] == "CALL"

    def test_null_leg_is_normalised_to_empty(self) -> None:
        """The unrequested leg comes back as JSON null, not an empty object."""
        transport = CapturingTransport({"data": {"ce": LEG, "pe": None}})
        client = build_client(transport)

        result = client.get_rolling_option_history(
            "13", from_date="2026-01-01", to_date="2026-01-10", option_type="CALL"
        )

        assert result.ce.bar_count() == 2
        assert result.pe.bar_count() == 0

    def test_strike_is_normalised_to_upper_case(self) -> None:
        transport = CapturingTransport({"ce": LEG, "pe": LEG})
        client = build_client(transport)

        client.get_rolling_option_history(
            "13", from_date="2026-01-01", to_date="2026-01-10", strike="atm-10"
        )

        sent = transport.last_json
        assert sent is not None
        assert sent["strike"] == "ATM-10"

    def test_routes_to_the_intraday_rate_limit_bucket(self) -> None:
        """rollingoption shares historical_intraday's 7,000/day budget, not daily's."""
        assert get_category_for_endpoint("POST", "charts/rollingoption") == "historical_intraday"


class TestRollingOptionResponse:
    def test_parses_both_legs_with_iv_oi_and_spot(self) -> None:
        transport = CapturingTransport({"ce": LEG, "pe": LEG})
        client = build_client(transport)

        result = client.get_rolling_option_history(
            "13", from_date="2026-01-01", to_date="2026-01-10"
        )

        assert isinstance(result, DhanRollingOptionData)
        assert result.ce.bar_count() == 2
        assert result.pe.bar_count() == 2
        assert result.ce.open_interest == [50000, 52000]
        assert result.ce.implied_volatility == [14.5, 14.8]
        assert result.ce.spot == [24980.0, 24995.0]
        assert result.ce.timestamp == [1785642300, 1785642360]

    def test_accepts_legs_nested_under_data(self) -> None:
        transport = CapturingTransport({"data": {"ce": LEG, "pe": LEG}})
        client = build_client(transport)

        result = client.get_rolling_option_history(
            "13", from_date="2026-01-01", to_date="2026-01-10"
        )

        assert result.ce.bar_count() == 2

    def test_missing_leg_yields_empty_rather_than_raising(self) -> None:
        """A strike with no CE quotes must not abort the whole window."""
        transport = CapturingTransport({"ce": LEG, "pe": None})
        client = build_client(transport)

        result = client.get_rolling_option_history(
            "13", from_date="2026-01-01", to_date="2026-01-10"
        )

        assert result.ce.bar_count() == 2
        assert result.pe.bar_count() == 0

    def test_bar_count_is_bounded_by_the_shortest_array(self) -> None:
        ragged = dict(LEG)
        ragged["close"] = [126.0]
        transport = CapturingTransport({"ce": ragged, "pe": LEG})
        client = build_client(transport)

        result = client.get_rolling_option_history(
            "13", from_date="2026-01-01", to_date="2026-01-10"
        )

        assert result.ce.bar_count() == 1


class TestOpenInterestPlumbing:
    def test_oi_flag_defaults_to_false_on_chart_calls(self) -> None:
        transport = CapturingTransport({"open": [], "high": [], "low": [], "close": []})
        client = build_client(transport)

        client.get_historical_daily("13", "IDX_I", "INDEX", "2026-01-01", "2026-01-10")

        sent = transport.last_json
        assert sent is not None
        assert sent["oi"] == "false"

    def test_oi_flag_is_sent_when_requested(self) -> None:
        transport = CapturingTransport({"open": [], "high": [], "low": [], "close": []})
        client = build_client(transport)

        client.get_historical_intraday(
            "45000",
            "NSE_FNO",
            "FUTIDX",
            "2026-01-01",
            "2026-01-10",
            include_open_interest=True,
        )

        sent = transport.last_json
        assert sent is not None
        assert sent["oi"] == "true"

    def test_open_interest_survives_into_bars(self) -> None:
        data = DhanHistoricalData.model_validate(
            {
                "open": [1.0, 2.0],
                "high": [3.0, 4.0],
                "low": [0.5, 1.5],
                "close": [2.5, 3.5],
                "volume": [10, 20],
                "oi": [111, 222],
                "timestamp": [1785642300, 1785642360],
            }
        )
        bars = data.to_bars()

        assert [b.open_interest for b in bars] == [111, 222]

    def test_absent_open_interest_defaults_to_zero(self) -> None:
        """Equity responses carry no OI; bars must still build."""
        data = DhanHistoricalData.model_validate(
            {
                "open": [1.0],
                "high": [3.0],
                "low": [0.5],
                "close": [2.5],
                "volume": [10],
                "timestamp": [1785642300],
            }
        )
        bars = data.to_bars()

        assert len(bars) == 1
        assert bars[0].open_interest == 0


def test_mock_transport_default_shape_still_parses() -> None:
    transport = MockTransport()
    transport.register("rollingoption", body={"ce": LEG, "pe": LEG})
    client = build_client(transport)

    result = client.get_rolling_option_history("13", from_date="2026-01-01", to_date="2026-01-10")
    assert result.ce.bar_count() == 2


def test_non_dict_payload_is_rejected() -> None:
    class ListTransport:
        def request(
            self,
            method: str,
            path: str,
            *,
            params: dict[str, Any] | None = None,
            json_data: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: float = 10.0,
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {}, b"[1, 2, 3]"

    client = build_client(ListTransport())
    with pytest.raises(Exception, match="rollingoption"):
        client.get_rolling_option_history("13", from_date="2026-01-01", to_date="2026-01-10")
