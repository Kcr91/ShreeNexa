"""Unit tests for composite universe indicator matrix calculation engine."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pyarrow.compute as pc
from app.indicators import (
    IndicatorDependencyGraph,
    UniverseIndicatorMatrixEngine,
)
from app.warehouse.schema import BarRecord


def generate_universe_bars(num_symbols: int = 50, bars_per_symbol: int = 30) -> list[BarRecord]:
    """Generate deterministic synthetic bar dataset for a multi-instrument universe."""
    bars: list[BarRecord] = []
    base_date = datetime(2026, 1, 1, 9, 15, tzinfo=UTC)

    for s_idx in range(num_symbols):
        sym = f"SYM_{s_idx:02d}"
        base_price = 100.0 + s_idx * 5.0
        for b_idx in range(bars_per_symbol):
            ts = base_date + timedelta(days=b_idx)
            # Deterministic price oscillation
            price = base_price + math.sin(b_idx * 0.5 + s_idx) * 10.0 + b_idx * 0.5
            bars.append(
                BarRecord(
                    symbol=sym,
                    exchange_segment="NSE_EQ",
                    security_id=str(1000 + s_idx),
                    timestamp=ts,
                    open=price - 0.5,
                    high=price + 1.5,
                    low=price - 1.5,
                    close=price,
                    volume=10000 + b_idx * 100,
                    open_interest=50000,
                )
            )
    return bars


def test_50_instrument_universe_matrix_parity() -> None:
    """Proof Test: Batch universe matrix engine output matches sequential single-instrument runs."""
    bars = generate_universe_bars(num_symbols=50, bars_per_symbol=30)

    graph = IndicatorDependencyGraph()
    graph.add_node("sma5", "sma(close, 5)")
    graph.add_node("sma10", "sma(close, 10)")
    graph.add_node("spread", "sma5 - sma10")
    graph.add_node("is_bullish", "spread > 0")

    # 1. Batch universe matrix computation
    engine = UniverseIndicatorMatrixEngine()
    matrix_table = engine.compute_matrix_from_bars(bars, graph)

    assert matrix_table.num_rows == len(bars)
    assert "sma5" in matrix_table.column_names
    assert "sma10" in matrix_table.column_names
    assert "spread" in matrix_table.column_names
    assert "is_bullish" in matrix_table.column_names

    # 2. Compare against per-instrument sequential execution
    plan = graph.compile_plan()
    symbols = sorted({b.symbol for b in bars})

    for sym in symbols:
        sym_bars = [b for b in bars if b.symbol == sym]
        sym_dict = {
            "open": [b.open for b in sym_bars],
            "high": [b.high for b in sym_bars],
            "low": [b.low for b in sym_bars],
            "close": [b.close for b in sym_bars],
            "volume": [b.volume for b in sym_bars],
        }
        seq_results = plan.execute(sym_dict)

        # Extract from batch matrix table
        mask = pc.equal(matrix_table["symbol"], sym)
        sym_matrix = matrix_table.filter(mask)
        # Sort by timestamp
        sym_matrix = sym_matrix.take(pc.sort_indices(sym_matrix["timestamp"]))

        for node_name in plan.execution_order:
            seq_series = seq_results[node_name]
            mat_series = sym_matrix[node_name].to_pylist()
            assert len(seq_series) == len(mat_series) == len(sym_bars)

            for i in range(len(sym_bars)):
                s_val = seq_series[i]
                m_val = mat_series[i]

                if s_val is None:
                    assert m_val is None, f"{sym} {node_name} at {i}: expected None"
                else:
                    assert m_val is not None, f"{sym} {node_name} at {i}: expected {s_val}"
                    if isinstance(s_val, bool):
                        assert m_val == s_val
                    else:
                        diff = abs(float(m_val) - float(s_val))
                        assert diff < 1e-5, f"{sym} {node_name} diff at {i}: {m_val} vs {s_val}"


def test_empty_universe_matrix() -> None:
    """Verify empty input handling."""
    engine = UniverseIndicatorMatrixEngine()
    graph = IndicatorDependencyGraph()
    graph.add_node("sma5", "sma(close, 5)")
    res = engine.compute_matrix_from_bars([], graph)
    assert res.num_rows == 0
