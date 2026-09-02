"""Unit and G1/G2 parity tests for StrategySignal nodes and cycle detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.strategy import (
    AndNode,
    CompareOp,
    FieldOperand,
    IndicatorCompareNode,
    NotNode,
    StrategyGraph,
    StrategyGraphCycleError,
    StrategyIR,
    StrategyNotFoundError,
    StrategySignalNode,
)
from app.warehouse.schema import BarRecord


def _make_dummy_strategy(
    strategy_id: str,
    when: Any = None,
    exit_when: Any = None,
) -> StrategyIR:
    when_node = when or IndicatorCompareNode(
        left=FieldOperand(field="close"),
        op=CompareOp.GT,
        right=100.0,
    )
    raw = {
        "ir_version": 1,
        "name": f"Strategy {strategy_id}",
        "kind": "stock",
        "horizon": "intraday",
        "strategy_type": "trend_following",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
        },
        "timeframe": "1d",
        "entries": [{"id": "long_1", "type": "buy", "when": when_node}],
        "exits": [{"id": "exit_1", "type": "signal", "when": exit_when}] if exit_when else [],
    }
    return StrategyIR.model_validate(raw)


def test_cycle_detection_direct_two_node() -> None:
    # A -> B -> A
    strat_a = _make_dummy_strategy(
        "A",
        when=StrategySignalNode(strategy_id="B", signal="entry"),
    )
    strat_b = _make_dummy_strategy(
        "B",
        when=StrategySignalNode(strategy_id="A", signal="entry"),
    )

    with pytest.raises(StrategyGraphCycleError) as exc_info:
        StrategyGraph({"A": strat_a, "B": strat_b})

    assert "Cycle detected" in str(exc_info.value)


def test_cycle_detection_indirect_three_node() -> None:
    # A -> B -> C -> A
    strat_a = _make_dummy_strategy("A", when=StrategySignalNode(strategy_id="B", signal="entry"))
    strat_b = _make_dummy_strategy("B", when=StrategySignalNode(strategy_id="C", signal="entry"))
    strat_c = _make_dummy_strategy("C", when=StrategySignalNode(strategy_id="A", signal="entry"))

    with pytest.raises(StrategyGraphCycleError) as exc_info:
        StrategyGraph({"A": strat_a, "B": strat_b, "C": strat_c})

    assert "Cycle detected" in str(exc_info.value)


def test_cycle_detection_self_reference() -> None:
    # A -> A
    strat_a = _make_dummy_strategy("A", when=StrategySignalNode(strategy_id="A", signal="entry"))

    with pytest.raises(StrategyGraphCycleError):
        StrategyGraph({"A": strat_a})


def test_missing_strategy_reference_raises() -> None:
    strat_a = _make_dummy_strategy(
        "A", when=StrategySignalNode(strategy_id="NON_EXISTENT", signal="entry")
    )

    with pytest.raises(StrategyNotFoundError):
        StrategyGraph({"A": strat_a})


def test_topological_execution_order() -> None:
    # A (independent), B (independent)
    # C depends on A and B
    # D depends on C
    strat_a = _make_dummy_strategy("A")
    strat_b = _make_dummy_strategy("B")
    strat_c = _make_dummy_strategy(
        "C",
        when=AndNode(
            children=[
                StrategySignalNode(strategy_id="A", signal="entry"),
                StrategySignalNode(strategy_id="B", signal="entry"),
            ]
        ),
    )
    strat_d = _make_dummy_strategy(
        "D",
        when=StrategySignalNode(strategy_id="C", signal="entry"),
    )

    graph = StrategyGraph({"D": strat_d, "C": strat_c, "B": strat_b, "A": strat_a})
    order = graph.topological_order()

    assert set(order) == {"A", "B", "C", "D"}
    # A and B must precede C
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")
    # C must precede D
    assert order.index("C") < order.index("D")


def test_signal_level_boolean_composition_and_or_not() -> None:
    # Strat A: close > 100
    strat_a = _make_dummy_strategy(
        "A",
        when=IndicatorCompareNode(left=FieldOperand(field="close"), op=CompareOp.GT, right=100.0),
    )
    # Strat B: volume > 500
    strat_b = _make_dummy_strategy(
        "B",
        when=IndicatorCompareNode(left=FieldOperand(field="volume"), op=CompareOp.GT, right=500.0),
    )
    # Strat C: A entry AND NOT B entry
    strat_c = _make_dummy_strategy(
        "C",
        when=AndNode(
            children=[
                StrategySignalNode(strategy_id="A", signal="entry"),
                NotNode(child=StrategySignalNode(strategy_id="B", signal="entry")),
            ]
        ),
    )

    graph = StrategyGraph({"A": strat_a, "B": strat_b, "C": strat_c})

    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    bars = [
        # Bar 0: close=90, vol=300 -> A=False, B=False -> C=False
        BarRecord(
            symbol="TEST",
            exchange_segment="NSE_EQ",
            security_id="1333",
            timestamp=t0,
            open=90.0,
            high=95.0,
            low=85.0,
            close=90.0,
            volume=300,
            open_interest=0,
        ),
        # Bar 1: close=110, vol=300 -> A=True, B=False -> C=True!
        BarRecord(
            symbol="TEST",
            exchange_segment="NSE_EQ",
            security_id="1333",
            timestamp=t0 + timedelta(minutes=1),
            open=105.0,
            high=115.0,
            low=100.0,
            close=110.0,
            volume=300,
            open_interest=0,
        ),
        # Bar 2: close=110, vol=600 -> A=True, B=True -> C=False (blocked by NOT B)
        BarRecord(
            symbol="TEST",
            exchange_segment="NSE_EQ",
            security_id="1333",
            timestamp=t0 + timedelta(minutes=2),
            open=110.0,
            high=120.0,
            low=108.0,
            close=110.0,
            volume=600,
            open_interest=0,
        ),
    ]

    results = graph.evaluate_vector(bars)
    c_entry = results["C"].entry_signals["long_1"]

    assert c_entry == [False, True, False]


def test_g1_g2_parity_across_composed_strategies() -> None:
    # 3-strategy composed pipeline:
    # Trend (Strat 1): SMA fast > SMA slow
    # Filter (Strat 2): Volume > 200
    # Exec (Strat 3): Strat 1 Entry AND Strat 2 Entry
    strat_1 = StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": "TrendStrategy",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1m",
            "indicators": {
                "sma_fast": {"fn": "sma", "params": {"period": 3}},
                "sma_slow": {"fn": "sma", "params": {"period": 5}},
            },
            "entries": [
                {
                    "id": "e1",
                    "type": "buy",
                    "when": {"node": "CrossOver", "left": "sma_fast", "right": "sma_slow"},
                }
            ],
        }
    )
    strat_2 = StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": "VolFilter",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1m",
            "entries": [
                {
                    "id": "e2",
                    "type": "buy",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "volume"},
                        "op": ">",
                        "right": 200.0,
                    },
                }
            ],
        }
    )
    strat_3 = StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": "ComposedComposite",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1m",
            "entries": [
                {
                    "id": "e3",
                    "type": "buy",
                    "when": {
                        "node": "And",
                        "children": [
                            {"node": "StrategySignal", "strategy_id": "strat_1", "signal": "entry"},
                            {"node": "StrategySignal", "strategy_id": "strat_2", "signal": "entry"},
                        ],
                    },
                }
            ],
        }
    )

    graph = StrategyGraph({"strat_1": strat_1, "strat_2": strat_2, "strat_3": strat_3})

    # Generate 15 test bars
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    prices = [
        100.0,
        101.0,
        102.0,
        101.5,
        103.0,
        105.0,
        104.0,
        106.0,
        108.0,
        110.0,
        107.0,
        109.0,
        111.0,
        112.0,
        115.0,
    ]
    volumes = [150, 250, 180, 300, 220, 400, 190, 250, 310, 150, 500, 210, 280, 320, 450]

    bars = [
        BarRecord(
            symbol="TEST",
            exchange_segment="NSE_EQ",
            security_id="1333",
            timestamp=t0 + timedelta(minutes=i),
            open=p - 0.5,
            high=p + 1.0,
            low=p - 1.0,
            close=p,
            volume=volumes[i],
            open_interest=0,
        )
        for i, p in enumerate(prices)
    ]

    # G1: Vectorized execution
    g1_results = graph.evaluate_vector(bars)

    # G2: Streaming incremental execution
    inc_engine = graph.create_incremental_engine()
    g2_steps = [inc_engine.update(bar) for bar in bars]

    # Verify G1 / G2 bit-for-bit equivalence for all strategies across all bars
    for strat_id in ("strat_1", "strat_2", "strat_3"):
        g1_res = g1_results[strat_id]
        for e_id, g1_mask in g1_res.entry_signals.items():
            g2_mask = [step[strat_id].entry_signals[e_id] for step in g2_steps]
            assert g1_mask == g2_mask, (
                f"G1/G2 mismatch for strategy {strat_id} entry {e_id}:\n"
                f"G1: {g1_mask}\n"
                f"G2: {g2_mask}"
            )
