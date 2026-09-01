"""Unit tests for expired options ATM strike limits, window slicing, and rolling candle parsing."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, date
from pathlib import Path

import pytest
from app.worker.options_backfill import (
    StrikeUnavailableError,
    generate_30_day_windows,
    parse_dhan_rolling_option_candles,
    save_raw_option_ingest,
    validate_strike_coverage,
)


def test_validate_strike_coverage_index_atm_limits() -> None:
    """Verify ATM±10 strike limits for index options (e.g. NIFTY 50-pt step)."""
    spot = 25000.0
    step = 50.0

    # Within ATM±10: up to 25500 (+10) and 24500 (-10) must succeed
    validate_strike_coverage(
        symbol="NIFTY",
        spot_price=spot,
        requested_strike=25500.0,
        strike_step=step,
        is_index=True,
    )
    validate_strike_coverage(
        symbol="NIFTY",
        spot_price=spot,
        requested_strike=24500.0,
        strike_step=step,
        is_index=True,
    )

    # Beyond ATM±10: 25550 (+11) must raise StrikeUnavailableError with 'strike_unavailable'
    with pytest.raises(StrikeUnavailableError) as exc_info:
        validate_strike_coverage(
            symbol="NIFTY",
            spot_price=spot,
            requested_strike=25550.0,
            strike_step=step,
            is_index=True,
        )
    assert "strike_unavailable" in str(exc_info.value)
    assert exc_info.value.max_strikes == 10


def test_validate_strike_coverage_stock_atm_limits() -> None:
    """Verify ATM±3 strike limits for stock options (e.g. RELIANCE 20-pt step)."""
    spot = 3000.0
    step = 20.0

    # Within ATM±3: up to 3060 (+3) and 2940 (-3) must succeed
    validate_strike_coverage(
        symbol="RELIANCE",
        spot_price=spot,
        requested_strike=3060.0,
        strike_step=step,
        is_index=False,
    )

    # Beyond ATM±3: 3080 (+4) must raise StrikeUnavailableError
    with pytest.raises(StrikeUnavailableError) as exc_info:
        validate_strike_coverage(
            symbol="RELIANCE",
            spot_price=spot,
            requested_strike=3080.0,
            strike_step=step,
            is_index=False,
        )
    assert "strike_unavailable" in str(exc_info.value)
    assert exc_info.value.max_strikes == 3


def test_generate_30_day_windows_slicing() -> None:
    """Verify slicing multi-month range into contiguous <= 30-day windows."""
    start = date(2026, 1, 1)
    end = date(2026, 3, 15)  # 74 days -> 30 + 30 + 14

    windows = generate_30_day_windows(start, end, max_days=30)
    assert len(windows) == 3
    assert windows[0] == (date(2026, 1, 1), date(2026, 1, 30))
    assert windows[1] == (date(2026, 1, 31), date(2026, 3, 1))
    assert windows[2] == (date(2026, 3, 2), date(2026, 3, 15))


def test_parse_dhan_rolling_option_candles() -> None:
    """Verify parsing rolling option response arrays into typed OptionBarRecords."""
    payload = {
        "open": [120.0, 125.0],
        "high": [130.0, 128.0],
        "low": [118.0, 122.0],
        "close": [126.0, 124.0],
        "volume": [1500, 2200],
        "timestamp": [1785642300, 1785642360],
        "oi": [50000, 52000],
        "iv": [14.5, 14.8],
        "spot": [24980.0, 24995.0],
    }

    bars = parse_dhan_rolling_option_candles(
        payload=payload,
        symbol="NIFTY26AUG25000CE",
        security_id="45000",
        underlying_symbol="NIFTY",
        expiry_date="2026-08-27",
        strike_price=25000.0,
        option_type="CALL",
    )

    assert len(bars) == 2
    assert bars[0].symbol == "NIFTY26AUG25000CE"
    assert bars[0].open == 120.0
    assert bars[0].implied_volatility == 14.5
    assert bars[0].spot_price == 24980.0
    assert bars[0].timestamp.tzinfo == UTC


def test_save_raw_option_ingest_redacts_credentials() -> None:
    """Verify raw option response persistence with parameter redaction."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_raw_opt_") as tmp_dir:
        data_root = Path(tmp_dir) / "data"
        raw_bytes = b'{"open": [120.0], "timestamp": [1785642300]}'
        params = {
            "symbol": "NIFTY26AUG25000CE",
            "access_token": "secret-jwt-token-must-not-leak",
            "client_id": "1000000001",
        }

        ingest_id, dest_dir = save_raw_option_ingest(data_root, raw_bytes, params)
        assert (dest_dir / "payload.json").is_file()

        meta = json.loads((dest_dir / "metadata.json").read_text(encoding="utf-8"))
        assert meta["ingest_id"] == ingest_id
        assert "access_token" not in meta["params"]
        assert "client_id" not in meta["params"]
