"""Unit tests for 90-day window slicing, intraday candle parsing, and quality reporting."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

from app.warehouse.schema import BarRecord
from app.worker.minute_backfill import (
    analyze_minute_bars,
    generate_90_day_windows,
    parse_dhan_intraday_candles,
    save_raw_minute_ingest,
)


def test_generate_90_day_windows_slicing() -> None:
    """Verify slicing broad date range into contiguous <= 90-day windows."""
    start = date(2026, 1, 1)
    end = date(2026, 8, 31)  # 243 days -> 90 + 90 + 63

    windows = generate_90_day_windows(start, end, max_days=90)
    assert len(windows) == 3

    # Check contiguous bounds
    assert windows[0] == (date(2026, 1, 1), date(2026, 3, 31))
    assert windows[1] == (date(2026, 4, 1), date(2026, 6, 29))
    assert windows[2] == (date(2026, 6, 30), date(2026, 8, 31))


def test_parse_dhan_intraday_candles() -> None:
    """Verify parsing 1m intraday candles from JSON payload arrays."""
    payload = {
        "open": [1650.0, 1652.5],
        "high": [1655.0, 1654.0],
        "low": [1648.0, 1651.0],
        "close": [1652.5, 1653.0],
        "volume": [500, 750],
        "start_Time": [1785642300, 1785642360],
        "open_interest": [100, 120],
    }

    bars = parse_dhan_intraday_candles(
        payload=payload,
        symbol="HDFCBANK",
        security_id="1333",
        exchange_segment="NSE_EQ",
    )

    assert len(bars) == 2
    assert bars[0].symbol == "HDFCBANK"
    assert bars[0].open == 1650.0
    assert bars[0].close == 1652.5
    assert bars[1].volume == 750
    assert bars[1].open_interest == 120


def test_analyze_minute_bars_quality_and_duplicates() -> None:
    """Verify duplicate detection and quality report on 1m bars."""
    t1 = datetime(2026, 8, 1, 9, 15, tzinfo=UTC)
    t2 = datetime(2026, 8, 1, 9, 16, tzinfo=UTC)

    bars_with_dupes = [
        BarRecord(
            timestamp=t1,
            exchange_segment="NSE_EQ",
            security_id="1333",
            symbol="HDFCBANK",
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=500,
            open_interest=0,
        ),
        BarRecord(
            timestamp=t1,  # duplicate
            exchange_segment="NSE_EQ",
            security_id="1333",
            symbol="HDFCBANK",
            open=1650.0,
            high=1655.0,
            low=1648.0,
            close=1652.0,
            volume=500,
            open_interest=0,
        ),
        BarRecord(
            timestamp=t2,
            exchange_segment="NSE_EQ",
            security_id="1333",
            symbol="HDFCBANK",
            open=1652.0,
            high=1656.0,
            low=1650.0,
            close=1654.0,
            volume=600,
            open_interest=0,
        ),
    ]

    report = analyze_minute_bars(
        bars=bars_with_dupes,
        symbol="HDFCBANK",
        security_id="1333",
        exchange_segment="NSE_EQ",
    )

    assert report.total_bars == 3
    assert report.duplicate_count == 1
    assert report.sha256 != ""


def test_save_raw_minute_ingest_redacts_credentials() -> None:
    """Verify saving raw 1m payload redacts credentials."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_raw_1m_") as tmp_dir:
        data_root = Path(tmp_dir) / "data"
        raw_bytes = b'{"open": [100.0], "start_Time": [1785642300]}'
        params = {
            "symbol": "HDFCBANK",
            "access_token": "secret-jwt-token-must-not-leak",
            "client_id": "1000000001",
            "interval": "1m",
        }

        ingest_id, dest_dir = save_raw_minute_ingest(data_root, raw_bytes, params)
        assert (dest_dir / "payload.json").is_file()

        meta = json.loads((dest_dir / "metadata.json").read_text(encoding="utf-8"))
        assert meta["ingest_id"] == ingest_id
        assert "access_token" not in meta["params"]
        assert "client_id" not in meta["params"]
        assert meta["params"]["symbol"] == "HDFCBANK"
