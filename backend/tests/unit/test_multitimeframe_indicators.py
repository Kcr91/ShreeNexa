"""Unit tests for timeframe-aware multi-resolution indicator calculation pipeline."""

from __future__ import annotations

from datetime import date, time, timedelta

from app.indicators import (
    IndicatorDependencyGraph,
    MultiTimeframeIndicatorPipeline,
    TimeframeAlignmentMode,
)
from app.marketdata.calendar import make_ist_datetime, to_utc
from app.warehouse.schema import BarRecord, bars_to_arrow_table


def generate_1m_bars(start_hour: int = 9, start_min: int = 15, count: int = 60) -> list[BarRecord]:
    """Generate sequential 1-minute intraday bars for testing."""
    bars: list[BarRecord] = []
    base_time = make_ist_datetime(date(2026, 1, 5), time(start_hour, start_min))
    base_price = 100.0

    for i in range(count):
        bar_dt = base_time + timedelta(minutes=i)
        p = base_price + i * 0.5
        bars.append(
            BarRecord(
                symbol="RELIANCE",
                exchange_segment="NSE_EQ",
                security_id="2885",
                timestamp=to_utc(bar_dt),
                open=p,
                high=p + 1.0,
                low=p - 0.5,
                close=p + 0.5,
                volume=1000 + i * 10,
                open_interest=5000,
            )
        )
    return bars


def test_multi_timeframe_lookahead_free_alignment() -> None:
    """Anti-Lookahead Test: HTF indicator outputs become available only after the HTF bar closes."""
    bars = generate_1m_bars(start_hour=9, start_min=15, count=60)
    pipeline = MultiTimeframeIndicatorPipeline()

    # Compute 15-minute SMA (period=2) on 1-minute bars
    # 15m bar 0: 09:15-09:30 (closes at 09:30)
    # 15m bar 1: 09:30-09:45 (closes at 09:45, period=2 SMA becomes valid here!)
    # 15m bar 2: 09:45-10:00 (closes at 10:00)
    # 15m bar 3: 10:00-10:15 (closes at 10:15)
    res = pipeline.compute_indicator(
        bars,
        target_tf="15m",
        indicator_name="sma",
        params={"period": 2, "column": "close"},
        alignment_mode=TimeframeAlignmentMode.LOOKAHEAD_FREE,
    )

    assert len(res) == len(bars)
    assert isinstance(res, list)

    # From 09:15 (idx 0) to 09:44 (idx 29): should be None because 2nd 15m bar hasn't closed yet
    for i in range(30):
        assert res[i] is None, f"Expected None at minute {i}, got {res[i]}"

    # At 09:45 (idx 30) up to 09:59 (idx 44): value must be non-None and constant
    first_val = res[30]
    assert first_val is not None
    for i in range(30, 45):
        assert res[i] == first_val, f"Value changed prematurely at minute {i}"

    # At 10:00 (idx 45): updates to the new completed 15m bar's SMA
    second_val = res[45]
    assert second_val is not None
    assert second_val != first_val
    for i in range(45, 60):
        assert res[i] == second_val


def test_multi_timeframe_compound_dag_execution() -> None:
    """Verify executing compound dependency graphs across higher timeframes."""
    bars = generate_1m_bars(start_hour=9, start_min=15, count=60)
    pipeline = MultiTimeframeIndicatorPipeline()

    graph = IndicatorDependencyGraph()
    graph.add_node("sma2", "sma(close, 2)")
    graph.add_node("sma3", "sma(close, 3)")
    graph.add_node("spread", "sma2 - sma3")

    results = pipeline.compute_graph(bars, target_tf="15m", graph=graph)
    assert "sma2" in results
    assert "sma3" in results
    assert "spread" in results

    spread = results["spread"]
    assert len(spread) == len(bars)
    # 15m SMA(3) completes after 3 bars (09:15, 09:30, 09:45) which closes at 10:00 (idx 45)
    for i in range(45):
        assert spread[i] is None
    assert spread[45] is not None


def test_multi_timeframe_pyarrow_table_input() -> None:
    """Verify pipeline accepts PyArrow Tables as input seamlessly."""
    bars = generate_1m_bars(start_hour=9, start_min=15, count=45)
    table = bars_to_arrow_table(bars)
    pipeline = MultiTimeframeIndicatorPipeline()

    res = pipeline.compute_indicator(
        table, target_tf="15m", indicator_name="sma", params={"period": 2}
    )
    assert isinstance(res, list)
    assert len(res) == 45
    assert res[30] is not None
