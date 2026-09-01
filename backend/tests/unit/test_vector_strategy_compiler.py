"""Unit tests for Vectorized StrategyIR compiler and G2 anti-lookahead audit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.strategy.compiler import VectorStrategyCompiler
from app.strategy.ir import StrategyIR
from app.warehouse.schema import BarRecord


def _make_synth_bars(n: int = 50, start_price: float = 100.0) -> list[BarRecord]:
    base_time = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    bars: list[BarRecord] = []
    p = start_price
    for i in range(n):
        ts = base_time + timedelta(minutes=5 * i)
        # Create an upward trend with a breakout after bar 5
        if i == 6:
            p += 5.0
        elif i > 6:
            p += 0.5
        else:
            p += 0.1
        bars.append(
            BarRecord(
                symbol="TEST",
                exchange_segment="NSE_EQ",
                security_id="1333",
                timestamp=ts,
                open=p - 0.2,
                high=p + 0.5,
                low=p - 0.5,
                close=p,
                volume=1000 + i * 50,
                open_interest=0,
            )
        )
    return bars


def test_canonical_orb_strategy_evaluation() -> None:
    """Test evaluation of canonical ORB strategy with RSI and EMA filters."""
    raw: dict[str, Any] = {
        "ir_version": 1,
        "name": "ORB Long",
        "kind": "stock",
        "horizon": "intraday",
        "strategy_type": "trend_following",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
        },
        "timeframe": "5m",
        "indicators": {
            "rsi14": {"fn": "RSI", "params": {"period": 14}, "source": "close"},
            "ema5": {"fn": "EMA", "params": {"period": 5}, "source": "close"},
            "orh": {"fn": "OPENING_RANGE_HIGH", "params": {"minutes": 15}},
        },
        "entries": [
            {
                "id": "orb_entry",
                "side": "BUY",
                "when": {
                    "node": "And",
                    "children": [
                        {"node": "TimeWindow", "mode": "clock", "from": "09:30", "to": "14:30"},
                        {
                            "node": "PriceLevelBreak",
                            "level": {"ref": "orh"},
                            "direction": "above",
                            "after": {
                                "node": "IndicatorCompare",
                                "left": {"field": "close"},
                                "op": ">",
                                "right": {"ref": "ema5"},
                            },
                        },
                    ],
                },
            }
        ],
        "exits": [{"id": "eod", "type": "time", "at": "15:15"}],
    }

    strategy = StrategyIR.from_dict(raw)
    compiled = VectorStrategyCompiler.compile(strategy)
    bars = _make_synth_bars(30, start_price=100.0)

    res = compiled.evaluate(bars)
    assert res.series_length == 30
    assert "orb_entry" in res.entry_signals
    assert "eod" in res.exit_signals
    assert any(res.entry_signals["orb_entry"]), "ORB breakout entry signal should have fired"


def test_crossover_and_sequence_strategy() -> None:
    """Test Sequence and CrossOver signal nodes."""
    raw: dict[str, Any] = {
        "name": "Sequence Strategy",
        "kind": "stock",
        "horizon": "swing",
        "strategy_type": "trend_following",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
        },
        "indicators": {
            "sma5": {"fn": "SMA", "params": {"period": 5}, "source": "close"},
            "sma10": {"fn": "SMA", "params": {"period": 10}, "source": "close"},
        },
        "entries": [
            {
                "id": "seq_entry",
                "side": "BUY",
                "when": {
                    "node": "Sequence",
                    "within": 10,
                    "steps": [
                        {
                            "node": "IndicatorCompare",
                            "left": {"field": "close"},
                            "op": ">",
                            "right": {"ref": "sma10"},
                        },
                        {"node": "CrossOver", "left": {"ref": "sma5"}, "right": {"ref": "sma10"}},
                    ],
                },
            }
        ],
    }

    strategy = StrategyIR.from_dict(raw)
    compiled = VectorStrategyCompiler.compile(strategy)
    bars = _make_synth_bars(40, start_price=50.0)

    res = compiled.evaluate(bars)
    assert res.series_length == 40
    assert "seq_entry" in res.entry_signals
    assert isinstance(res.entry_signals["seq_entry"], list)


def test_persist_and_pct_change_signals() -> None:
    """Test Persist and PctChange signal nodes."""
    raw: dict[str, Any] = {
        "name": "Persist Strategy",
        "kind": "stock",
        "horizon": "swing",
        "strategy_type": "trend_following",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
        },
        "indicators": {
            "sma5": {"fn": "SMA", "params": {"period": 5}, "source": "close"},
        },
        "entries": [
            {
                "id": "persist_entry",
                "side": "BUY",
                "when": {
                    "node": "And",
                    "children": [
                        {
                            "node": "Persist",
                            "bars": 3,
                            "child": {
                                "node": "IndicatorCompare",
                                "left": {"field": "close"},
                                "op": ">",
                                "right": {"ref": "sma5"},
                            },
                        },
                        {
                            "node": "PctChange",
                            "source": "close",
                            "lookback": 3,
                            "op": ">",
                            "value": 0.1,
                        },
                    ],
                },
            }
        ],
    }

    strategy = StrategyIR.from_dict(raw)
    compiled = VectorStrategyCompiler.compile(strategy)
    bars = _make_synth_bars(35, start_price=200.0)

    res = compiled.evaluate(bars)
    assert res.series_length == 35
    assert "persist_entry" in res.entry_signals


def test_g2_truncated_data_lookahead_audit() -> None:
    """G2 Anti-Lookahead Property: Signals at bar t are invariant under addition of future bars."""
    raw: dict[str, Any] = {
        "name": "Audit Strategy",
        "kind": "stock",
        "horizon": "swing",
        "strategy_type": "trend_following",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
        },
        "indicators": {
            "sma5": {"fn": "SMA", "params": {"period": 5}, "source": "close"},
            "sma15": {"fn": "SMA", "params": {"period": 15}, "source": "close"},
        },
        "entries": [
            {
                "id": "trend_entry",
                "side": "BUY",
                "when": {
                    "node": "CrossOver",
                    "left": {"ref": "sma5"},
                    "right": {"ref": "sma15"},
                },
            }
        ],
    }

    strategy = StrategyIR.from_dict(raw)
    compiled = VectorStrategyCompiler.compile(strategy)
    full_bars = _make_synth_bars(60, start_price=100.0)
    full_res = compiled.evaluate(full_bars)
    full_mask = full_res.entry_signals["trend_entry"]

    for trunc_len in (25, 35, 45, 55):
        sub_bars = full_bars[:trunc_len]
        sub_res = compiled.evaluate(sub_bars)
        sub_mask = sub_res.entry_signals["trend_entry"]

        assert sub_mask == full_mask[:trunc_len], (
            f"G2 lookahead violation detected at truncation {trunc_len}: "
            f"{sub_mask} vs {full_mask[:trunc_len]}"
        )
