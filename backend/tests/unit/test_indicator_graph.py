"""Unit tests for compound indicator dependency graph, cycle detection, and execution plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.indicators import (
    CyclicDependencyError,
    DuplicateNodeError,
    IndicatorDependencyGraph,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_indicators_reference.json"


def get_test_dataset() -> dict[str, Any]:
    """Load test price dataset from fixture."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    prices = data["prices"]
    volumes = data["volumes"]
    return {
        "open": [p - 0.5 for p in prices],
        "high": [p + 1.5 for p in prices],
        "low": [p - 1.5 for p in prices],
        "close": prices,
        "volume": volumes,
    }


def test_topological_sort_deterministic_ordering() -> None:
    """Verify Kahn's topological sort resolves dependencies in correct linear order."""
    graph = IndicatorDependencyGraph()
    graph.add_node("sma_fast", "sma(close, 5)")
    graph.add_node("sma_slow", "sma(close, 10)")
    graph.add_node("signal", "crossover(sma_fast, sma_slow)")
    graph.add_node("regime", "if_else(signal, 1.0, 0.0)")

    order = graph.topological_sort()
    assert order.index("sma_fast") < order.index("signal")
    assert order.index("sma_slow") < order.index("signal")
    assert order.index("signal") < order.index("regime")


def test_direct_and_indirect_cycle_detection() -> None:
    """Verify circular dependencies are detected and raise CyclicDependencyError."""
    # 1. Direct cycle: A -> B -> A
    graph_direct = IndicatorDependencyGraph()
    graph_direct.add_node("node_a", "node_b + 1")
    graph_direct.add_node("node_b", "node_a + 1")
    with pytest.raises(CyclicDependencyError) as exc_direct:
        graph_direct.topological_sort()
    assert "Circular dependency detected" in str(exc_direct.value)

    # 2. Indirect 3-node cycle: A -> B -> C -> A
    graph_indirect = IndicatorDependencyGraph()
    graph_indirect.add_node("A", "C + 1")
    graph_indirect.add_node("B", "A + 1")
    graph_indirect.add_node("C", "B + 1")
    with pytest.raises(CyclicDependencyError):
        graph_indirect.topological_sort()


def test_duplicate_node_rejection() -> None:
    """Verify duplicate node names raise DuplicateNodeError."""
    graph = IndicatorDependencyGraph()
    graph.add_node("sma20", "sma(close, 20)")
    with pytest.raises(DuplicateNodeError):
        graph.add_node("sma20", "sma(close, 50)")


def test_compound_indicator_execution_plan() -> None:
    """Verify compiling and executing a multi-stage dependency plan."""
    data = get_test_dataset()
    graph = IndicatorDependencyGraph()

    graph.add_node("sma5", "sma(close, 5)")
    graph.add_node("spread", "close - sma5")
    graph.add_node("is_bullish", "spread > 0")

    plan = graph.compile_plan()
    assert len(plan.execution_order) == 3

    results = plan.execute(data)
    assert "sma5" in results
    assert "spread" in results
    assert "is_bullish" in results

    spread = results["spread"]
    is_bullish = results["is_bullish"]

    for i in range(len(spread)):
        s_val = spread[i]
        b_val = is_bullish[i]
        if s_val is None:
            assert b_val is None
        else:
            assert b_val == (s_val > 0)


def test_shared_subexpression_multiple_dependents() -> None:
    """Verify shared intermediate nodes evaluate and serve multiple downstream nodes."""
    data = get_test_dataset()
    graph = IndicatorDependencyGraph()

    graph.add_node("base_sma", "sma(close, 5)")
    graph.add_node("upper_delta", "high - base_sma")
    graph.add_node("lower_delta", "base_sma - low")
    graph.add_node("bias", "upper_delta > lower_delta")

    plan = graph.compile_plan()
    results = plan.execute(data)

    assert "base_sma" in results
    assert "upper_delta" in results
    assert "lower_delta" in results
    assert "bias" in results
    assert len(results["bias"]) == len(data["close"])
