"""Unit tests for incremental compound indicator graph streaming engine and G1 graph parity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.indicators import (
    IncrementalGraphEngine,
    IndicatorDependencyGraph,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_indicators_reference.json"


def get_test_bars() -> list[dict[str, float]]:
    """Load test price dataset from fixture as individual bar records."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    prices = data["prices"]
    volumes = data["volumes"]
    bars: list[dict[str, float]] = []
    for c, v in zip(prices, volumes, strict=True):
        bars.append(
            {
                "open": c - 0.5,
                "high": c + 1.5,
                "low": c - 1.5,
                "close": c,
                "volume": float(v),
            }
        )
    return bars


def test_g1_compound_graph_parity_streaming_vs_batch() -> None:
    """G1 Parity Property Test: Streaming bar updates match batch vectorized graph execution."""
    bars = get_test_bars()
    batch_data = {
        "open": [b["open"] for b in bars],
        "high": [b["high"] for b in bars],
        "low": [b["low"] for b in bars],
        "close": [b["close"] for b in bars],
        "volume": [b["volume"] for b in bars],
    }

    graph = IndicatorDependencyGraph()
    graph.add_node("sma5", "sma(close, 5)")
    graph.add_node("sma10", "sma(close, 10)")
    graph.add_node("spread", "sma5 - sma10")
    graph.add_node("is_bullish", "spread > 0")

    # 1. Execute batch vector plan
    batch_plan = graph.compile_plan()
    batch_results = batch_plan.execute(batch_data)

    # 2. Execute incremental streaming engine
    stream_engine = IncrementalGraphEngine(graph)
    stream_results: dict[str, list[Any]] = {name: [] for name in batch_plan.execution_order}

    for b in bars:
        bar_out = stream_engine.update(b)
        for name in batch_plan.execution_order:
            stream_results[name].append(bar_out[name])

    # 3. Verify exact parity for all nodes
    for name in batch_plan.execution_order:
        b_series = batch_results[name]
        s_series = stream_results[name]
        assert len(b_series) == len(s_series) == len(bars)

        for i in range(len(bars)):
            b_val = b_series[i]
            s_val = s_series[i]

            if b_val is None:
                assert s_val is None, f"{name} at {i}: expected None, got {s_val}"
            else:
                assert s_val is not None, f"{name} at {i}: expected {b_val}, got None"
                if isinstance(b_val, bool):
                    assert s_val is True or s_val is False
                    assert b_val == s_val, f"{name} boolean mismatch at {i}: {b_val} vs {s_val}"
                else:
                    diff = abs(float(s_val) - float(b_val))
                    assert diff < 1e-3, (
                        f"G1 graph parity failure on {name} at {i}: batch={b_val}, stream={s_val}"
                    )


def test_incremental_graph_state_checkpoint_and_restore() -> None:
    """Verify freezing and restoring state across multi-node streaming graph."""
    bars = get_test_bars()
    graph = IndicatorDependencyGraph()
    graph.add_node("sma5", "sma(close, 5)")
    graph.add_node("spread", "close - sma5")

    engine = IncrementalGraphEngine(graph)
    # Stream first 7 bars
    for b in bars[:7]:
        engine.update(b)

    state_checkpoint = engine.state
    val_7 = engine.update(bars[7])

    # Clone new engine and restore
    restored_engine = IncrementalGraphEngine(graph)
    restored_engine.restore_state(state_checkpoint)
    val_restored_7 = restored_engine.update(bars[7])

    assert val_7 == val_restored_7


def test_incremental_graph_reset() -> None:
    """Verify reset() clears all internal buffers across all nodes."""
    bars = get_test_bars()
    graph = IndicatorDependencyGraph()
    graph.add_node("sma5", "sma(close, 5)")

    engine = IncrementalGraphEngine(graph)
    for b in bars[:5]:
        engine.update(b)

    res_5 = engine.update(bars[5])
    assert res_5["sma5"] is not None

    engine.reset()
    res_fresh = engine.update(bars[0])
    assert res_fresh["sma5"] is None
