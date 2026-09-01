"""Compound indicator dependency graph, topological resolver, cycle detector, and execution plan."""

from __future__ import annotations

import ast
import logging
from collections import defaultdict, deque
from typing import Any

import pyarrow as pa

from app.indicators.formula import (
    ALLOWED_FUNCTIONS,
    ALLOWED_IDENTIFIERS,
    CompiledFormula,
    FormulaCompiler,
)

logger = logging.getLogger(__name__)


class GraphError(Exception):
    """Base exception for indicator graph errors."""


class CyclicDependencyError(GraphError):
    """Circular dependency detected in indicator graph."""


class DuplicateNodeError(GraphError):
    """Duplicate node registered in graph."""


class IndicatorDependencyGraph:
    """Directed Acyclic Graph representing compound indicator calculation dependencies."""

    def __init__(self, compiler: FormulaCompiler | None = None) -> None:
        self.compiler = compiler or FormulaCompiler()
        self.nodes: dict[str, CompiledFormula] = {}
        self.dependencies: dict[str, set[str]] = defaultdict(set)
        self.dependents: dict[str, set[str]] = defaultdict(set)

    def add_node(
        self,
        name: str,
        formula: str | CompiledFormula,
        explicit_deps: list[str] | None = None,
    ) -> None:
        """Register a formula node with automatic or explicit dependency extraction."""
        name_clean = name.strip()
        if name_clean in self.nodes:
            raise DuplicateNodeError(f"Node '{name_clean}' already exists in graph")

        if isinstance(formula, str):
            compiled = self.compiler.compile(formula)
        else:
            compiled = formula

        self.nodes[name_clean] = compiled
        deps: set[str] = set()

        if explicit_deps is not None:
            deps.update(d.strip() for d in explicit_deps)
        else:
            # Extract identifier dependencies from AST
            for node in ast.walk(compiled.parsed_ast):
                if isinstance(node, ast.Name):
                    ident = node.id
                    ident_lower = ident.lower()
                    if (
                        ident_lower not in ALLOWED_IDENTIFIERS
                        and ident_lower not in ALLOWED_FUNCTIONS
                    ):
                        deps.add(ident)

        self.dependencies[name_clean] = deps
        for dep in deps:
            self.dependents[dep].add(name_clean)

    def topological_sort(self) -> list[str]:
        """Produce deterministic execution order via Kahn's algorithm or raise cycle error."""
        # Compute in-degrees considering only nodes that are defined in self.nodes
        in_degree: dict[str, int] = {node: 0 for node in self.nodes}
        for node, deps in self.dependencies.items():
            for dep in deps:
                if dep in self.nodes:
                    in_degree[node] += 1

        queue: deque[str] = deque([node for node, deg in in_degree.items() if deg == 0])
        # Sort queue for deterministic execution order
        queue = deque(sorted(queue))
        sorted_order: list[str] = []

        while queue:
            curr = queue.popleft()
            sorted_order.append(curr)

            for dependent in sorted(self.dependents.get(curr, set())):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(sorted_order) != len(self.nodes):
            # Graph has cycle; identify cycle components
            cycle_path = self._find_cycle()
            raise CyclicDependencyError(
                f"Circular dependency detected in graph: {' -> '.join(cycle_path)}"
            )

        return sorted_order

    def _find_cycle(self) -> list[str]:
        """DFS traversal to locate circular dependency path for error diagnostic."""
        visited: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited
        parent: dict[str, str | None] = {}
        path: list[str] = []

        def dfs(u: str) -> bool:
            visited[u] = 1
            for v in sorted(self.dependencies.get(u, set())):
                if v not in self.nodes:
                    continue
                if visited.get(v, 0) == 1:
                    # Found cycle
                    path.append(v)
                    curr: str | None = u
                    while curr is not None and curr != v:
                        path.append(curr)
                        curr = parent.get(curr)
                    path.append(v)
                    path.reverse()
                    return True
                elif visited.get(v, 0) == 0:
                    parent[v] = u
                    if dfs(v):
                        return True
            visited[u] = 2
            return False

        for node in self.nodes:
            if visited.get(node, 0) == 0:
                parent[node] = None
                if dfs(node):
                    return path
        return list(self.nodes.keys())

    def compile_plan(self) -> IndicatorExecutionPlan:
        """Compile graph into an executable execution plan."""
        order = self.topological_sort()
        plan_nodes = [(name, self.nodes[name]) for name in order]
        return IndicatorExecutionPlan(plan_nodes)


class IndicatorExecutionPlan:
    """Executable plan running topologically ordered formulas with shared subexpression caching."""

    def __init__(self, plan_nodes: list[tuple[str, CompiledFormula]]) -> None:
        self.plan_nodes = plan_nodes

    @property
    def execution_order(self) -> list[str]:
        """List of node names in topological execution order."""
        return [name for name, _ in self.plan_nodes]

    def execute(self, data: pa.Table | dict[str, Any]) -> dict[str, list[Any]]:
        """Execute all nodes in plan and return dictionary of named result series."""
        # Convert input dataset to working dictionary
        working_dict: dict[str, Any] = {}
        if isinstance(data, pa.Table):
            for col in data.column_names:
                working_dict[col] = data[col].to_pylist()
        elif isinstance(data, dict):
            working_dict.update(data)

        results: dict[str, list[Any]] = {}

        for name, formula in self.plan_nodes:
            res = formula.evaluate(working_dict)
            working_dict[name] = res
            results[name] = res

        return results
