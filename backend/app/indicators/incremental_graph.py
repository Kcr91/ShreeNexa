"""Incremental streaming compound indicator graph engine with G1 parity."""

from __future__ import annotations

import ast
import logging
from collections import deque
from typing import Any

from app.indicators.formula import (
    CompiledFormula,
    FormulaEvaluationError,
)
from app.indicators.graph import IndicatorDependencyGraph
from app.indicators.incremental import (
    IncrementalIndicator,
    create_incremental_indicator,
)
from app.indicators.registry import registry
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class _IncrementalNodeEvaluator:
    """Stateful evaluator for a single formula node in a streaming DAG."""

    def __init__(self, formula: CompiledFormula) -> None:
        self.formula = formula
        self.call_states: dict[str, Any] = {}
        self._init_stateful_helpers(self.formula.parsed_ast.body)

    def _init_stateful_helpers(self, node: ast.AST, path: str = "root") -> None:
        """Initialize stateful sub-indicator instances and rolling buffers."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id.lower()
            if func_name in registry._indicators:
                # Build incremental indicator instance
                params: dict[str, Any] = {}
                meta = registry.get(func_name)
                numeric_keys = [
                    k for k, v in meta.default_params.items() if isinstance(v, (int, float))
                ]
                num_idx = 0
                for a in node.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, (int, float)):
                        if num_idx < len(numeric_keys):
                            params[numeric_keys[num_idx]] = a.value
                            num_idx += 1
                    elif isinstance(a, ast.Name):
                        params["column"] = a.id

                for kw in node.keywords:
                    if kw.arg and isinstance(kw.value, ast.Constant):
                        params[kw.arg] = kw.value.value

                self.call_states[path] = create_incremental_indicator(func_name, params)

            elif func_name == "shift":
                bars = 1
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    bars = int(node.args[1].value)  # type: ignore[arg-type]
                self.call_states[path] = deque(maxlen=bars + 1)

            elif func_name in ("crossover", "crossunder", "cross"):
                self.call_states[path] = {"prev_a": None, "prev_b": None}

            elif func_name in ("highest", "lowest"):
                period = 14
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    period = int(node.args[1].value)  # type: ignore[arg-type]
                self.call_states[path] = deque(maxlen=period)

        for i, child in enumerate(ast.iter_child_nodes(node)):
            self._init_stateful_helpers(child, f"{path}_{i}")

    def eval_bar(self, working_bar: dict[str, Any]) -> Any:
        """Evaluate formula against current bar dictionary."""
        return self._eval_ast_node(self.formula.parsed_ast.body, working_bar, "root")

    def _eval_ast_node(self, node: ast.AST, working_bar: dict[str, Any], path: str) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            ident = node.id
            ident_lower = ident.lower()
            if ident_lower in ("open", "high", "low", "close", "volume", "oi", "open_interest"):
                col = "open_interest" if ident_lower == "oi" else ident_lower
                return working_bar.get(col, working_bar.get(ident))
            elif ident in working_bar:
                return working_bar[ident]
            elif ident_lower in working_bar:
                return working_bar[ident_lower]
            elif ident_lower == "true":
                return True
            elif ident_lower == "false":
                return False
            elif ident_lower == "none":
                return None
            else:
                return ident

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_ast_node(node.operand, working_bar, f"{path}_u")
            if operand is None:
                return None
            if isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.Not):
                return not bool(operand)
            elif isinstance(node.op, ast.UAdd):
                return operand
            raise FormulaEvaluationError(f"Unsupported unary op {type(node.op).__name__}")

        elif isinstance(node, ast.BinOp):
            left = self._eval_ast_node(node.left, working_bar, f"{path}_l")
            right = self._eval_ast_node(node.right, working_bar, f"{path}_r")
            if left is None or right is None:
                return None
            op = node.op
            if isinstance(op, ast.Add):
                return left + right
            elif isinstance(op, ast.Sub):
                return left - right
            elif isinstance(op, ast.Mult):
                return left * right
            elif isinstance(op, ast.Div):
                return (left / right) if right != 0 else None
            elif isinstance(op, ast.Mod):
                return left % right
            elif isinstance(op, ast.Pow):
                return left**right
            raise FormulaEvaluationError(f"Unsupported binary op {type(op).__name__}")

        elif isinstance(node, ast.BoolOp):
            values = [
                self._eval_ast_node(v, working_bar, f"{path}_b_{i}")
                for i, v in enumerate(node.values)
            ]
            if any(v is None for v in values):
                return None
            if isinstance(node.op, ast.And):
                return all(bool(v) for v in values)
            elif isinstance(node.op, ast.Or):
                return any(bool(v) for v in values)

        elif isinstance(node, ast.Compare):
            left = self._eval_ast_node(node.left, working_bar, f"{path}_cl")
            for i, (cmp_op, comparator) in enumerate(zip(node.ops, node.comparators, strict=True)):
                right = self._eval_ast_node(comparator, working_bar, f"{path}_cr_{i}")
                if left is None or right is None:
                    return None
                if isinstance(cmp_op, ast.Eq):
                    cmp_res = left == right
                elif isinstance(cmp_op, ast.NotEq):
                    cmp_res = left != right
                elif isinstance(cmp_op, ast.Lt):
                    cmp_res = left < right
                elif isinstance(cmp_op, ast.LtE):
                    cmp_res = left <= right
                elif isinstance(cmp_op, ast.Gt):
                    cmp_res = left > right
                elif isinstance(cmp_op, ast.GtE):
                    cmp_res = left >= right
                else:
                    raise FormulaEvaluationError(f"Unsupported comparator {type(cmp_op).__name__}")
                if not cmp_res:
                    return False
                left = right
            return True

        elif isinstance(node, ast.IfExp):
            cond = self._eval_ast_node(node.test, working_bar, f"{path}_cond")
            if cond is None:
                return None
            if bool(cond):
                return self._eval_ast_node(node.body, working_bar, f"{path}_tb")
            else:
                return self._eval_ast_node(node.orelse, working_bar, f"{path}_fb")

        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id.lower()
            if path in self.call_states:
                state_obj = self.call_states[path]

                if isinstance(state_obj, IncrementalIndicator):
                    # Check if node passed custom column name
                    column = getattr(state_obj, "column", "close")
                    if len(node.args) >= 1 and isinstance(node.args[0], ast.Name):
                        column = node.args[0].id
                    # Evaluate custom column if it was dynamically computed
                    input_bar = dict(working_bar)
                    if column in working_bar:
                        input_bar["close"] = working_bar[column]
                    val = state_obj.update(input_bar)
                    if isinstance(val, dict):
                        first_k = next(iter(val.keys()))
                        return val[first_k]
                    return val

                elif func_name == "shift":
                    series_val = self._eval_ast_node(node.args[0], working_bar, f"{path}_sa")
                    buf: deque[Any] = state_obj
                    buf.append(series_val)
                    if len(buf) == buf.maxlen:
                        return buf[0]
                    return None

                elif func_name in ("crossover", "crossunder", "cross"):
                    curr_a = self._eval_ast_node(node.args[0], working_bar, f"{path}_co_a")
                    curr_b = self._eval_ast_node(node.args[1], working_bar, f"{path}_co_b")
                    p_dict: dict[str, Any] = state_obj
                    prev_a = p_dict["prev_a"]
                    prev_b = p_dict["prev_b"]
                    p_dict["prev_a"] = curr_a
                    p_dict["prev_b"] = curr_b

                    if (
                        curr_a is not None
                        and prev_a is not None
                        and curr_b is not None
                        and prev_b is not None
                    ):
                        if func_name == "crossover":
                            return (curr_a > curr_b) and (prev_a <= prev_b)
                        elif func_name == "crossunder":
                            return (curr_a < curr_b) and (prev_a >= prev_b)
                        elif func_name == "cross":
                            return ((curr_a > curr_b) and (prev_a <= prev_b)) or (
                                (curr_a < curr_b) and (prev_a >= prev_b)
                            )
                    return None

                elif func_name in ("highest", "lowest"):
                    series_val = self._eval_ast_node(node.args[0], working_bar, f"{path}_hl")
                    buf = state_obj
                    buf.append(series_val)
                    if len(buf) == buf.maxlen and all(x is not None for x in buf):
                        return max(buf) if func_name == "highest" else min(buf)
                    return None

            # Fallback evaluation for simple stateless math helpers
            args = [
                self._eval_ast_node(a, working_bar, f"{path}_a_{i}")
                for i, a in enumerate(node.args)
            ]
            if func_name == "abs":
                return abs(args[0]) if args[0] is not None else None
            elif func_name == "min":
                if args[0] is not None and args[1] is not None:
                    return min(args[0], args[1])
                return None
            elif func_name == "max":
                if args[0] is not None and args[1] is not None:
                    return max(args[0], args[1])
                return None
            elif func_name == "if_else":
                return args[1] if bool(args[0]) else args[2]

        raise FormulaEvaluationError(f"Unhandled incremental node {type(node).__name__}")

    def reset(self) -> None:
        """Reset internal buffers and indicator states."""
        for state_obj in self.call_states.values():
            if isinstance(state_obj, IncrementalIndicator):
                state_obj.reset()
            elif isinstance(state_obj, deque):
                state_obj.clear()
            elif isinstance(state_obj, dict):
                for k in state_obj:
                    state_obj[k] = None

    @property
    def state(self) -> dict[str, Any]:
        """Serializable state checkpoint."""
        out: dict[str, Any] = {}
        for path, obj in self.call_states.items():
            if isinstance(obj, IncrementalIndicator):
                out[path] = {"type": "indicator", "state": obj.state}
            elif isinstance(obj, deque):
                out[path] = {"type": "deque", "maxlen": obj.maxlen, "items": list(obj)}
            elif isinstance(obj, dict):
                out[path] = {"type": "dict", "data": dict(obj)}
        return out

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore internal buffers and states from checkpoint."""
        for path, payload in state.items():
            if path in self.call_states:
                obj = self.call_states[path]
                if payload["type"] == "indicator" and isinstance(obj, IncrementalIndicator):
                    obj.restore_state(payload["state"])
                elif payload["type"] == "deque" and isinstance(obj, deque):
                    obj.clear()
                    for item in payload["items"]:
                        obj.append(item)
                elif payload["type"] == "dict" and isinstance(obj, dict):
                    obj.update(payload["data"])


class IncrementalGraphEngine:
    """Real-time streaming compound indicator execution engine."""

    def __init__(self, graph: IndicatorDependencyGraph) -> None:
        self.graph = graph
        self.topological_order = self.graph.topological_sort()
        self.evaluators: dict[str, _IncrementalNodeEvaluator] = {
            name: _IncrementalNodeEvaluator(self.graph.nodes[name])
            for name in self.topological_order
        }

    def update(self, bar: BarRecord | dict[str, Any]) -> dict[str, float | bool | None]:
        """Process incoming new bar through topological DAG and return outputs."""
        working_bar: dict[str, Any] = {}
        if isinstance(bar, BarRecord):
            for field in ("open", "high", "low", "close", "volume", "open_interest"):
                working_bar[field] = getattr(bar, field, 0.0)
        elif isinstance(bar, dict):
            working_bar.update(bar)

        results: dict[str, float | bool | None] = {}
        for name in self.topological_order:
            evaluator = self.evaluators[name]
            val = evaluator.eval_bar(working_bar)
            working_bar[name] = val
            results[name] = val

        return results

    def reset(self) -> None:
        """Clear all buffers and reset indicator states across all nodes."""
        for evaluator in self.evaluators.values():
            evaluator.reset()

    @property
    def state(self) -> dict[str, Any]:
        """Complete graph state checkpoint."""
        return {name: ev.state for name, ev in self.evaluators.items()}

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore complete graph state from checkpoint."""
        for name, node_state in state.items():
            if name in self.evaluators:
                self.evaluators[name].restore_state(node_state)
