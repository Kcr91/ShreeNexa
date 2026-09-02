"""Unit tests for Incremental StrategyIR execution engine and Vector/Streaming parity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.strategy.compiler import VectorStrategyCompiler
from app.strategy.incremental import IncrementalStrategyCompiler
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


def test_streaming_orb_strategy_evaluation() -> None:
    """Test real-time bar-by-bar streaming of ORB strategy."""
    raw: dict[str, Any] = {
        "ir_version": 1,
        "name": "Streaming ORB Long",
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
    engine = IncrementalStrategyCompiler.compile(strategy)
    bars = _make_synth_bars(30, start_price=100.0)

    steps = [engine.update(b) for b in bars]
    assert len(steps) == 30
    entry_triggers = [s.entry_signals["orb_entry"] for s in steps]
    assert any(entry_triggers), "Streaming ORB breakout entry should trigger"


def test_vector_incremental_strategy_parity() -> None:
    """Parity Suite: Assert 100% equivalence between vector and streaming strategy runs."""
    raw: dict[str, Any] = {
        "name": "Parity Strategy",
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
            "rsi": {"fn": "RSI", "params": {"period": 14}, "source": "close"},
        },
        "entries": [
            {
                "id": "crossover_entry",
                "side": "BUY",
                "when": {
                    "node": "And",
                    "children": [
                        {
                            "node": "CrossOver",
                            "left": {"ref": "sma5"},
                            "right": {"ref": "sma10"},
                        },
                        {
                            "node": "IndicatorCompare",
                            "left": {"ref": "rsi"},
                            "op": "<",
                            "right": {"const": 75.0},
                        },
                    ],
                },
            }
        ],
        "exits": [
            {
                "id": "crossunder_exit",
                "type": "signal",
                "when": {
                    "node": "CrossUnder",
                    "left": {"ref": "sma5"},
                    "right": {"ref": "sma10"},
                },
            }
        ],
    }

    strategy = StrategyIR.from_dict(raw)
    bars = _make_synth_bars(50, start_price=100.0)

    # 1. Run Vector Engine
    vector_compiled = VectorStrategyCompiler.compile(strategy)
    vector_res = vector_compiled.evaluate(bars)
    vector_entry = vector_res.entry_signals["crossover_entry"]
    vector_exit = vector_res.exit_signals["crossunder_exit"]

    # 2. Run Streaming Engine
    incremental_engine = IncrementalStrategyCompiler.compile(strategy)
    streaming_steps = [incremental_engine.update(b) for b in bars]
    streaming_entry = [s.entry_signals["crossover_entry"] for s in streaming_steps]
    streaming_exit = [s.exit_signals["crossunder_exit"] for s in streaming_steps]

    # 3. Check Exact Parity
    assert (
        streaming_entry == vector_entry
    ), f"Entry signals diverged: {streaming_entry} vs {vector_entry}"
    assert (
        streaming_exit == vector_exit
    ), f"Exit signals diverged: {streaming_exit} vs {vector_exit}"


def test_state_checkpoint_and_restore() -> None:
    """Verify state checkpointing allows seamless mid-stream recovery without signal drift."""
    raw: dict[str, Any] = {
        "name": "Stateful Strategy",
        "kind": "stock",
        "horizon": "swing",
        "strategy_type": "trend_following",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
        },
        "indicators": {
            "sma5": {"fn": "SMA", "params": {"period": 5}, "source": "close"},
            "rsi": {"fn": "RSI", "params": {"period": 14}, "source": "close"},
        },
        "entries": [
            {
                "id": "persist_entry",
                "side": "BUY",
                "when": {
                    "node": "Persist",
                    "bars": 3,
                    "child": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": {"ref": "sma5"},
                    },
                },
            }
        ],
    }

    strategy = StrategyIR.from_dict(raw)
    bars = _make_synth_bars(40, start_price=100.0)

    # Engine A runs full 40 bars
    engine_a = IncrementalStrategyCompiler.compile(strategy)
    for i in range(20):
        engine_a.update(bars[i])

    checkpoint = engine_a.get_state()
    steps_a_remaining = [engine_a.update(bars[i]) for i in range(20, 40)]

    # Engine B restored at bar 20 and runs remaining 20 bars
    engine_b = IncrementalStrategyCompiler.compile(strategy)
    engine_b.restore_state(checkpoint)
    steps_b_remaining = [engine_b.update(bars[i]) for i in range(20, 40)]

    signals_a = [s.entry_signals["persist_entry"] for s in steps_a_remaining]
    signals_b = [s.entry_signals["persist_entry"] for s in steps_b_remaining]
    assert signals_a == signals_b, "Restored engine state produced divergent signals"


def test_engine_reset_lifecycle() -> None:
    """Verify reset() clears all internal state."""
    raw: dict[str, Any] = {
        "name": "Reset Strategy",
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
        "entries": [],
    }

    strategy = StrategyIR.from_dict(raw)
    engine = IncrementalStrategyCompiler.compile(strategy)
    bars = _make_synth_bars(10, start_price=100.0)
    for b in bars:
        engine.update(b)

    assert engine._bar_count == 10
    engine.reset()
    assert engine._bar_count == 0
    assert engine._prev_bar is None
