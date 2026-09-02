"""Unit tests for session-aware live one-minute bar builder and warehouse merge."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.feedd.bar_builder import (
    LiveBarBuilder,
    LiveMinuteBar,
    LiveTick,
    merge_history_and_live,
)
from app.warehouse.schema import BarRecord


def test_dhan_minute_bar_exact_reconciliation() -> None:
    """Built bars reconcile with 100% exact numerical match against Dhan minute bars."""
    fixture_path = Path("backend/tests/fixtures/sample_1m_bars.json")
    assert fixture_path.exists(), "Sample 1m bars fixture must exist"

    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    symbol = fixture_data["symbol"]
    security_id = fixture_data["security_id"]
    segment = fixture_data["exchange_segment"]
    raw_bars = fixture_data["bars"]

    builder = LiveBarBuilder(enforce_session=False)

    for bar in raw_bars:
        bar_ts = datetime.fromisoformat(bar["timestamp"])
        open_p = bar["open"]
        high_p = bar["high"]
        low_p = bar["low"]
        close_p = bar["close"]
        vol = bar["volume"]

        # Simulate 4 sequential ticks inside the minute:
        # 1. Open at :05
        # 2. Low at :20
        # 3. High at :40
        # 4. Close at :55
        ticks = [
            LiveTick(
                segment=segment,
                security_id=security_id,
                symbol=symbol,
                price=open_p,
                volume=vol // 4,
                timestamp=bar_ts + timedelta(seconds=5),
            ),
            LiveTick(
                segment=segment,
                security_id=security_id,
                symbol=symbol,
                price=low_p,
                volume=vol // 4,
                timestamp=bar_ts + timedelta(seconds=20),
            ),
            LiveTick(
                segment=segment,
                security_id=security_id,
                symbol=symbol,
                price=high_p,
                volume=vol // 4,
                timestamp=bar_ts + timedelta(seconds=40),
            ),
            LiveTick(
                segment=segment,
                security_id=security_id,
                symbol=symbol,
                price=close_p,
                volume=vol - (3 * (vol // 4)),
                timestamp=bar_ts + timedelta(seconds=55),
            ),
        ]

        for t in ticks:
            builder.process_tick(t)

    # Force finalize last bar
    builder.force_finalize_active(segment, security_id)

    completed = builder.get_completed_bars(segment, security_id)
    assert len(completed) == len(raw_bars)

    for i, expected in enumerate(raw_bars):
        actual = completed[i]
        exp_ts = datetime.fromisoformat(expected["timestamp"])
        assert actual.timestamp == exp_ts
        assert actual.open == pytest.approx(expected["open"])
        assert actual.high == pytest.approx(expected["high"])
        assert actual.low == pytest.approx(expected["low"])
        assert actual.close == pytest.approx(expected["close"])
        assert actual.volume == expected["volume"]


def test_duplicate_ticks_rejection_without_volume_inflation() -> None:
    """Duplicate ticks with identical signature are rejected and volume is not inflated."""
    builder = LiveBarBuilder(enforce_session=False)
    ts = datetime(2026, 8, 3, 3, 45, 10, tzinfo=UTC)

    tick = LiveTick(
        segment="NSE_EQ",
        security_id="2885",
        symbol="RELIANCE",
        price=2950.0,
        volume=100,
        timestamp=ts,
        sequence=101,
    )

    # Send first time
    bar1 = builder.process_tick(tick)
    assert bar1 is not None
    assert bar1.volume == 100
    assert bar1.tick_count == 1

    # Send duplicate
    bar2 = builder.process_tick(tick)
    assert bar2 is not None
    # Volume must NOT be inflated
    assert bar2.volume == 100
    assert bar2.tick_count == 1
    assert builder.duplicate_ticks_count == 1


def test_out_of_order_tick_handling() -> None:
    """Out-of-order ticks correctly update open, high, low, close bounds."""
    builder = LiveBarBuilder(enforce_session=False)
    minute_start = datetime(2026, 8, 3, 3, 45, 0, tzinfo=UTC)

    # Tick 1: at :10 (P=100)
    builder.process_tick(
        LiveTick(
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            price=100.0,
            volume=50,
            timestamp=minute_start + timedelta(seconds=10),
        )
    )

    # Tick 2: at :40 (P=105)
    builder.process_tick(
        LiveTick(
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            price=105.0,
            volume=50,
            timestamp=minute_start + timedelta(seconds=40),
        )
    )

    # Tick 3: at :20 (P=98) -> Arrives out of order!
    builder.process_tick(
        LiveTick(
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            price=98.0,
            volume=30,
            timestamp=minute_start + timedelta(seconds=20),
        )
    )

    # Tick 4: at :50 (P=102)
    active = builder.process_tick(
        LiveTick(
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            price=102.0,
            volume=20,
            timestamp=minute_start + timedelta(seconds=50),
        )
    )

    assert active is not None
    assert builder.out_of_order_ticks_count == 1
    assert active.open == 100.0  # earliest timestamp :10
    assert active.low == 98.0  # lowest price
    assert active.high == 105.0  # highest price
    assert active.close == 102.0  # latest timestamp :50
    assert active.volume == 150  # 50 + 50 + 30 + 20


def test_late_tick_grace_window_and_dropped_telemetry() -> None:
    """Late ticks within grace window retroactively update finalized bar; older are dropped."""
    builder = LiveBarBuilder(grace_period_sec=15.0, enforce_session=False)
    m1 = datetime(2026, 8, 3, 3, 45, 0, tzinfo=UTC)
    m2 = datetime(2026, 8, 3, 3, 46, 0, tzinfo=UTC)

    # Bar 1 ticks
    builder.process_tick(
        LiveTick(
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            price=100.0,
            volume=100,
            timestamp=m1 + timedelta(seconds=30),
        )
    )

    # Bar 2 tick -> rolls and finalizes Bar 1
    builder.process_tick(
        LiveTick(
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            price=102.0,
            volume=50,
            timestamp=m2 + timedelta(seconds=5),
        )
    )

    # Late tick belonging to Bar 1 at :45 (arriving within 15s grace window)
    late_tick = LiveTick(
        segment="NSE_EQ",
        security_id="1",
        symbol="TEST",
        price=104.0,  # new high for Bar 1
        volume=25,
        timestamp=m1 + timedelta(seconds=45),
    )
    retro = builder.process_tick(late_tick)
    assert retro is not None
    assert retro.timestamp == m1
    assert retro.high == 104.0
    assert retro.volume == 125

    # Very old late tick (from 10 minutes ago) -> dropped
    ancient_tick = LiveTick(
        segment="NSE_EQ",
        security_id="1",
        symbol="TEST",
        price=95.0,
        volume=10,
        timestamp=m1 - timedelta(minutes=10),
    )
    dropped = builder.process_tick(ancient_tick)
    assert dropped is None
    assert builder.dropped_late_ticks_count == 1


def test_session_boundary_enforcement() -> None:
    """Enforces Indian market trading session hours (09:15 to 15:30 IST)."""
    builder = LiveBarBuilder(enforce_session=True)

    # Monday 2026-08-03
    # 08:30 IST is 03:00 UTC (pre-market -> outside session)
    pre_market = LiveTick(
        segment="NSE_EQ",
        security_id="2885",
        symbol="RELIANCE",
        price=2950.0,
        volume=50,
        timestamp=datetime(2026, 8, 3, 3, 0, 0, tzinfo=UTC),
    )
    assert builder.process_tick(pre_market) is None

    # 09:15:10 IST is 03:45:10 UTC (inside session)
    in_session = LiveTick(
        segment="NSE_EQ",
        security_id="2885",
        symbol="RELIANCE",
        price=2950.0,
        volume=100,
        timestamp=datetime(2026, 8, 3, 3, 45, 10, tzinfo=UTC),
    )
    bar = builder.process_tick(in_session)
    assert bar is not None
    assert bar.timestamp == datetime(2026, 8, 3, 3, 45, 0, tzinfo=UTC)


def test_merge_history_and_live() -> None:
    """Merges warehouse historical bars and live bars with deduplication and sorting."""
    base = datetime(2026, 8, 3, 3, 45, 0, tzinfo=UTC)

    # Warehouse history: 3 bars (:45, :46, :47)
    wh_bars = [
        BarRecord(
            timestamp=base,
            exchange_segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=500,
        ),
        BarRecord(
            timestamp=base + timedelta(minutes=1),
            exchange_segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            open=101.0,
            high=103.0,
            low=100.0,
            close=102.5,
            volume=600,
        ),
        BarRecord(
            timestamp=base + timedelta(minutes=2),
            exchange_segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            open=102.5,
            high=104.0,
            low=102.0,
            close=103.0,
            volume=400,
        ),
    ]

    # Live bars: 2 bars (:47 overlapping/refined, :48 new live bar)
    live_bars = [
        LiveMinuteBar(
            timestamp=base + timedelta(minutes=2),
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            open=102.5,
            high=105.0,  # refined live high
            low=102.0,
            close=104.5,
            volume=750,  # refined live volume
            first_tick_time=base + timedelta(minutes=2, seconds=5),
            last_tick_time=base + timedelta(minutes=2, seconds=55),
        ),
        LiveMinuteBar(
            timestamp=base + timedelta(minutes=3),
            segment="NSE_EQ",
            security_id="1",
            symbol="TEST",
            open=104.5,
            high=106.0,
            low=104.0,
            close=105.5,
            volume=800,
            first_tick_time=base + timedelta(minutes=3, seconds=5),
            last_tick_time=base + timedelta(minutes=3, seconds=55),
        ),
    ]

    merged = merge_history_and_live(wh_bars, live_bars)

    # Total 4 unique bars: :45, :46, :47, :48
    assert len(merged) == 4

    # Strictly monotonic timestamps
    for idx in range(1, len(merged)):
        assert merged[idx].timestamp > merged[idx - 1].timestamp

    # At :47 (index 2), the live bar superseded warehouse
    assert merged[2].high == 105.0
    assert merged[2].volume == 750

    # At :48 (index 3), live bar is present
    assert merged[3].close == 105.5
