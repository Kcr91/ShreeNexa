"""Strategy dependency graph, cycle detection, and composite execution engine."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
from typing import Any

import pyarrow as pa

from app.strategy.compiler import CompiledStrategy, StrategyEvaluationResult
from app.strategy.incremental import IncrementalStrategyEngine, StrategyEvaluationStep
from app.strategy.ir import (
    AndNode,
    NotNode,
    OrNode,
    PersistNode,
    PriceLevelBreakNode,
    SequenceNode,
    SignalNode,
    StrategyIR,
    StrategySignalNode,
)
from app.warehouse.schema import BarRecord


class StrategyGraphCycleError(ValueError):
    """Raised when a recursive dependency cycle is detected in a strategy graph."""


class StrategyNotFoundError(KeyError):
    """Raised when a StrategySignalNode references an unregistered strategy ID."""


def extract_strategy_dependencies(ir: StrategyIR) -> set[str]:
    """Inspect all entry and exit condition trees and return referenced strategy IDs."""
    deps: set[str] = set()

    def _walk(node: SignalNode | None) -> None:
        if node is None:
            return
        if isinstance(node, StrategySignalNode):
            deps.add(str(node.strategy_id))
        elif isinstance(node, (AndNode, OrNode)):
            for child in node.children:
                _walk(child)
        elif isinstance(node, (NotNode, PersistNode)):
            _walk(node.child)
        elif isinstance(node, SequenceNode):
            for step in node.steps:
                _walk(step)
        elif isinstance(node, PriceLevelBreakNode):
            if node.after:
                _walk(node.after)

    for entry in ir.entries:
        _walk(entry.when)
    for exit_rule in ir.exits:
        if exit_rule.when:
            _walk(exit_rule.when)

    return deps


class StrategyGraph:
    """Directed dependency graph of strategies connected via StrategySignal nodes."""

    def __init__(self, strategies: Mapping[str, StrategyIR]) -> None:
        self.strategies: dict[str, StrategyIR] = dict(strategies)
        self._dependencies: dict[str, set[str]] = {}

        # 1. Extract and validate dependencies
        for strat_id, ir in self.strategies.items():
            deps = extract_strategy_dependencies(ir)
            for dep in deps:
                if dep not in self.strategies:
                    raise StrategyNotFoundError(
                        f"Strategy '{strat_id}' references unknown strategy '{dep}'"
                    )
            self._dependencies[strat_id] = deps

        # 2. Enforce cycle detection immediately on graph construction
        self.detect_cycles()

    def detect_cycles(self) -> None:
        """Detect any direct, indirect, or self-referential cycles in the graph."""
        # 0 = unvisited, 1 = visiting (in active recursion stack), 2 = visited
        state: dict[str, int] = {k: 0 for k in self.strategies}
        stack: list[str] = []

        def _dfs(node: str) -> None:
            state[node] = 1
            stack.append(node)

            for dep in self._dependencies.get(node, ()):
                if state[dep] == 1:
                    # Found cycle! Reconstruct cycle path
                    cycle_idx = stack.index(dep)
                    cycle_path = [*stack[cycle_idx:], dep]
                    raise StrategyGraphCycleError(
                        f"Cycle detected in strategy graph: {' -> '.join(cycle_path)}"
                    )
                elif state[dep] == 0:
                    _dfs(dep)

            stack.pop()
            state[node] = 2

        for node in self.strategies:
            if state[node] == 0:
                _dfs(node)

    def topological_order(self) -> list[str]:
        """Return execution order such that producers are evaluated before consumers."""
        # Producer (dep) -> Consumer (strat)
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {k: 0 for k in self.strategies}

        for strat, deps in self._dependencies.items():
            in_degree[strat] = len(deps)
            for dep in deps:
                adj[dep].append(strat)

        queue: deque[str] = deque([k for k, deg in in_degree.items() if deg == 0])
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for consumer in adj[node]:
                in_degree[consumer] -= 1
                if in_degree[consumer] == 0:
                    queue.append(consumer)

        if len(order) != len(self.strategies):
            raise StrategyGraphCycleError("Unresolvable cycle in strategy dependencies")

        return order

    def evaluate_vector(
        self, data: pa.Table | dict[str, Any] | list[BarRecord]
    ) -> dict[str, StrategyEvaluationResult]:
        """Execute G1 vectorized evaluation in topological dependency order."""
        order = self.topological_order()
        accumulated_signals: dict[tuple[str, str], list[bool]] = {}
        results: dict[str, StrategyEvaluationResult] = {}

        for strat_id in order:
            ir = self.strategies[strat_id]
            compiled = CompiledStrategy(ir)
            res = compiled.evaluate(data, external_signals=accumulated_signals)
            results[strat_id] = res

            # Register entry signals
            for e_id, mask in res.entry_signals.items():
                accumulated_signals[(strat_id, e_id)] = mask
                accumulated_signals[(strat_id, f"entry_{e_id}")] = mask

            if res.entry_signals:
                any_entry = [
                    any(res.entry_signals[k][i] for k in res.entry_signals)
                    for i in range(res.series_length)
                ]
                accumulated_signals[(strat_id, "entry")] = any_entry

            # Register exit signals
            for x_id, mask in res.exit_signals.items():
                accumulated_signals[(strat_id, x_id)] = mask
                accumulated_signals[(strat_id, f"exit_{x_id}")] = mask

            if res.exit_signals:
                any_exit = [
                    any(res.exit_signals[k][i] for k in res.exit_signals)
                    for i in range(res.series_length)
                ]
                accumulated_signals[(strat_id, "exit")] = any_exit

        return results

    def create_incremental_engine(self) -> CompositeIncrementalEngine:
        """Create a G2 real-time streaming incremental engine for the composed graph."""
        return CompositeIncrementalEngine(self)


class CompositeIncrementalEngine:
    """Coordinates streaming execution across composed strategies in topological order."""

    def __init__(self, graph: StrategyGraph) -> None:
        self.graph = graph
        self.order = graph.topological_order()
        self.engines: dict[str, IncrementalStrategyEngine] = {
            s_id: IncrementalStrategyEngine(graph.strategies[s_id]) for s_id in self.order
        }

    def update(self, bar: BarRecord) -> dict[str, StrategyEvaluationStep]:
        """Process an incoming market bar sequentially through the strategy graph."""
        accumulated: dict[tuple[str, str], bool] = {}
        steps: dict[str, StrategyEvaluationStep] = {}

        for strat_id in self.order:
            engine = self.engines[strat_id]
            step = engine.update(bar, external_signals=accumulated)
            steps[strat_id] = step

            # Register signals for downstream consumers
            for e_id, val in step.entry_signals.items():
                accumulated[(strat_id, e_id)] = val
                accumulated[(strat_id, f"entry_{e_id}")] = val
            accumulated[(strat_id, "entry")] = any(step.entry_signals.values())

            for x_id, val in step.exit_signals.items():
                accumulated[(strat_id, x_id)] = val
                accumulated[(strat_id, f"exit_{x_id}")] = val
            accumulated[(strat_id, "exit")] = any(step.exit_signals.values())

        return steps
