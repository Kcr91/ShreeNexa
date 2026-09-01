"""Unit tests for session-aware bar resampling and OHLCV invariant validation."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
from app.marketdata.calendar import make_ist_datetime
from app.marketdata.resampler import (
    BarResampler,
    PartialBarPolicy,
    Timeframe,
    parse_timeframe,
)
from app.warehouse.schema import BarRecord, bars_to_arrow_table

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_1m_bars.json"


def test_parse_timeframe_valid_and_invalid() -> None:
    """Verify parsing supported timeframe strings and rejecting unsupported values."""
    assert parse_timeframe("3m") == Timeframe.M3
    assert parse_timeframe("5m") == Timeframe.M5
    assert parse_timeframe("15m") == Timeframe.M15
    assert parse_timeframe("25m") == Timeframe.M25
    assert parse_timeframe("30m") == Timeframe.M30
    assert parse_timeframe("60m") == Timeframe.H1
    assert parse_timeframe("1h") == Timeframe.H1
    assert parse_timeframe("1d") == Timeframe.D1
    assert parse_timeframe("1w") == Timeframe.W1

    with pytest.raises(ValueError):
        parse_timeframe("45m")


def test_resample_fixture_5m_bar_aggregations() -> None:
    """Verify 5m resampling against independent sample_1m_bars.json fixture."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bars = [
        BarRecord(
            timestamp=datetime.fromisoformat(b["timestamp"]),
            exchange_segment=data["exchange_segment"],
            security_id=data["security_id"],
            symbol=data["symbol"],
            open=b["open"],
            high=b["high"],
            low=b["low"],
            close=b["close"],
            volume=b["volume"],
            open_interest=b["open_interest"],
        )
        for b in data["bars"]
    ]

    resampler = BarResampler()
    resampled = resampler.resample_bars(bars, timeframe="5m")

    assert len(resampled) == 1
    r = resampled[0]
    assert r.open == 2950.0
    assert r.high == 2962.0
    assert r.low == 2948.0
    assert r.close == 2960.0
    assert r.volume == 5600  # 1000 + 1200 + 800 + 1500 + 1100
    assert r.high >= max(r.open, r.close)
    assert r.low <= min(r.open, r.close)


def test_full_session_intraday_resampling_and_partial_policy() -> None:
    """Verify full 375-bar session (09:15-15:30 IST) resampling into 5m, 15m, and 60m."""
    d = date(2026, 8, 3)
    start_utc = make_ist_datetime(d, time(9, 15))

    # Generate 375 consecutive 1-minute bars
    bars_1m: list[BarRecord] = []
    total_vol = 0
    for i in range(375):
        ts = start_utc + timedelta(minutes=i)
        vol = 100 + i
        total_vol += vol
        bars_1m.append(
            BarRecord(
                timestamp=ts,
                exchange_segment="NSE_EQ",
                security_id="2885",
                symbol="RELIANCE",
                open=2900.0 + i * 0.1,
                high=2901.0 + i * 0.1,
                low=2899.0 + i * 0.1,
                close=2900.5 + i * 0.1,
                volume=vol,
                open_interest=50000 + i,
            )
        )

    resampler = BarResampler()

    # 5m bars: 375 / 5 = 75 bars
    bars_5m = resampler.resample_bars(bars_1m, "5m")
    assert len(bars_5m) == 75
    assert sum(b.volume for b in bars_5m) == total_vol

    # 15m bars: 375 / 15 = 25 bars
    bars_15m = resampler.resample_bars(bars_1m, "15m")
    assert len(bars_15m) == 25
    assert sum(b.volume for b in bars_15m) == total_vol

    # 60m bars with EMIT_PARTIAL: 6 full 60m bars + 1 15m bar (15:15-15:30) = 7 bars
    bars_60m_emit = resampler.resample_bars(bars_1m, "60m", policy=PartialBarPolicy.EMIT_PARTIAL)
    assert len(bars_60m_emit) == 7
    assert sum(b.volume for b in bars_60m_emit) == total_vol

    # 60m bars with DROP_INCOMPLETE: drops the 15:15-15:30 incomplete 15m bar = 6 bars
    bars_60m_drop = resampler.resample_bars(bars_1m, "60m", policy=PartialBarPolicy.DROP_INCOMPLETE)
    assert len(bars_60m_drop) == 6


def test_daily_and_weekly_resampling_and_arrow_table() -> None:
    """Verify daily and weekly aggregations and PyArrow table conversion."""
    # 5 trading days in a week (Monday to Friday)
    start_monday = date(2026, 8, 3)
    bars_all: list[BarRecord] = []
    total_vol = 0

    for day_offset in range(5):
        day_date = start_monday + timedelta(days=day_offset)
        day_open_utc = make_ist_datetime(day_date, time(9, 15))
        for minute_offset in range(375):
            ts = day_open_utc + timedelta(minutes=minute_offset)
            vol = 50
            total_vol += vol
            bars_all.append(
                BarRecord(
                    timestamp=ts,
                    exchange_segment="NSE_EQ",
                    security_id="2885",
                    symbol="RELIANCE",
                    open=2900.0,
                    high=2920.0,
                    low=2890.0,
                    close=2910.0,
                    volume=vol,
                    open_interest=100000,
                )
            )

    resampler = BarResampler()

    # Daily resampling: 5 days -> 5 daily bars
    daily_bars = resampler.resample_bars(bars_all, "1d")
    assert len(daily_bars) == 5
    assert sum(b.volume for b in daily_bars) == total_vol

    # Weekly resampling: 1 week -> 1 weekly bar
    weekly_bars = resampler.resample_bars(bars_all, "1w")
    assert len(weekly_bars) == 1
    assert weekly_bars[0].volume == total_vol

    # Arrow table resampling test
    table_1m = bars_to_arrow_table(bars_all)
    table_resampled = resampler.resample_table(table_1m, "1d")
    assert table_resampled.num_rows == 5
