"""Safe domain-specific formula parser, AST security validator, and compiler."""

from __future__ import annotations

import ast
import logging
from typing import Any

import pyarrow as pa

from app.indicators.registry import extract_series_nullable, registry

logger = logging.getLogger(__name__)


class FormulaError(Exception):
    """Base exception for formula processing errors."""


class FormulaSyntaxError(FormulaError):
    """Expression syntax or parsing failure."""


class FormulaSecurityError(FormulaError):
    """AST security violation, disallowed node, attribute lookup, or lookahead violation."""


class FormulaEvaluationError(FormulaError):
    """Runtime evaluation or mathematical failure."""


ALLOWED_FUNCTIONS = {
    # Indicators
    "sma",
    "ema",
    "macd",
    "supertrend",
    "rsi",
    "stoch",
    "roc",
    "atr",
    "bollinger_bands",
    "obv",
    "vwap",
    "zscore",
    "rolling_std",
    # Signal and Math helpers
    "crossover",
    "crossunder",
    "cross",
    "shift",
    "highest",
    "lowest",
    "abs",
    "min",
    "max",
    "if_else",
}

ALLOWED_IDENTIFIERS = {
    "open",
    "high",
    "low",
    "close",
    "volume",
    "oi",
    "open_interest",
    "true",
    "false",
    "none",
    "True",
    "False",
    "None",
}


class FormulaASTValidator(ast.NodeVisitor):
    """Strict AST visitor that validates expression structure against an allowlist."""

    ALLOWED_NODES = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.Compare,
        ast.IfExp,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.keyword,
        # Operators
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Not,
        ast.Invert,
        ast.And,
        ast.Or,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        # Argument lists
        ast.Load,
    )

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, self.ALLOWED_NODES):
            raise FormulaSecurityError(
                f"Disallowed AST node type '{type(node).__name__}' in formula"
            )
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        id_str = node.id
        if id_str.startswith("__") or id_str.endswith("__"):
            raise FormulaSecurityError(f"Dunder identifier '{id_str}' is forbidden")
        if id_str.lower() not in ALLOWED_IDENTIFIERS and id_str.lower() not in ALLOWED_FUNCTIONS:
            pass
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        raise FormulaSecurityError(
            f"Attribute access '.{node.attr}' is strictly forbidden in formulas"
        )

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            raise FormulaSecurityError("Dynamic or computed function calls are forbidden")
        func_name = node.func.id.lower()
        if func_name not in ALLOWED_FUNCTIONS:
            raise FormulaSecurityError(
                f"Function '{node.func.id}' is not in the allowlisted function registry"
            )

        # Check lookahead in shift(series, bars)
        if func_name == "shift":
            if len(node.args) >= 2:
                bars_arg = node.args[1]
                if isinstance(bars_arg, ast.UnaryOp) and isinstance(bars_arg.op, ast.USub):
                    raise FormulaSecurityError("Negative shift lookahead is strictly forbidden")
                if isinstance(bars_arg, ast.Constant) and isinstance(bars_arg.value, (int, float)):
                    if bars_arg.value < 0:
                        raise FormulaSecurityError("Negative shift lookahead is strictly forbidden")

        self.generic_visit(node)


def helper_crossover(a: list[Any], b: list[Any]) -> list[bool | None]:
    """Element-wise crossover: a[t] > b[t] and a[t-1] <= b[t-1]."""
    n = max(len(a), len(b))
    out: list[bool | None] = [None] * n
    for i in range(1, n):
        a_curr, a_prev = a[i], a[i - 1]
        b_curr, b_prev = b[i], b[i - 1]
        if a_curr is not None and a_prev is not None and b_curr is not None and b_prev is not None:
            out[i] = (a_curr > b_curr) and (a_prev <= b_prev)
        else:
            out[i] = None
    return out


def helper_crossunder(a: list[Any], b: list[Any]) -> list[bool | None]:
    """Element-wise crossunder: a[t] < b[t] and a[t-1] >= b[t-1]."""
    n = max(len(a), len(b))
    out: list[bool | None] = [None] * n
    for i in range(1, n):
        a_curr, a_prev = a[i], a[i - 1]
        b_curr, b_prev = b[i], b[i - 1]
        if a_curr is not None and a_prev is not None and b_curr is not None and b_prev is not None:
            out[i] = (a_curr < b_curr) and (a_prev >= b_prev)
        else:
            out[i] = None
    return out


def helper_cross(a: list[Any], b: list[Any]) -> list[bool | None]:
    """Element-wise cross: crossover or crossunder."""
    co = helper_crossover(a, b)
    cu = helper_crossunder(a, b)
    n = len(co)
    out: list[bool | None] = [None] * n
    for i in range(n):
        if co[i] is None or cu[i] is None:
            out[i] = None
        else:
            out[i] = bool(co[i] or cu[i])
    return out


def helper_shift(series: list[Any], bars: int) -> list[Any]:
    """Backward shift by bars >= 0."""
    if bars < 0:
        raise FormulaSecurityError("Negative shift lookahead is strictly forbidden")
    n = len(series)
    if bars == 0:
        return list(series)
    return [None] * min(bars, n) + list(series[: max(0, n - bars)])


def helper_highest(series: list[Any], period: int) -> list[float | None]:
    """Rolling highest value over period."""
    n = len(series)
    out: list[float | None] = [None] * n
    for i in range(period - 1, n):
        window = [x for x in series[i - period + 1 : i + 1] if x is not None]
        if len(window) == period:
            out[i] = max(window)
    return out


def helper_lowest(series: list[Any], period: int) -> list[float | None]:
    """Rolling lowest value over period."""
    n = len(series)
    out: list[float | None] = [None] * n
    for i in range(period - 1, n):
        window = [x for x in series[i - period + 1 : i + 1] if x is not None]
        if len(window) == period:
            out[i] = min(window)
    return out


def helper_if_else(cond: list[Any], true_val: Any, false_val: Any) -> list[Any]:
    """Element-wise ternary selection."""
    n = len(cond)
    out: list[Any] = [None] * n
    t_list = true_val if isinstance(true_val, list) else [true_val] * n
    f_list = false_val if isinstance(false_val, list) else [false_val] * n

    for i in range(n):
        c = cond[i]
        if c is None:
            out[i] = None
        elif bool(c):
            out[i] = t_list[i]
        else:
            out[i] = f_list[i]
    return out


class CompiledFormula:
    """Compiled, sandboxed technical formula expression ready for execution."""

    def __init__(self, raw_formula: str, parsed_ast: ast.Expression) -> None:
        self.raw_formula = raw_formula
        self.parsed_ast = parsed_ast

    def evaluate(self, data: pa.Table | dict[str, Any]) -> list[Any]:
        """Execute formula against price/volume dataset."""
        evaluator = _FormulaEvaluator(data)
        res = evaluator.eval_node(self.parsed_ast.body)
        if isinstance(res, list):
            return res
        # Single scalar literal expanded to length of dataset
        n = evaluator.series_length
        return [res] * n


class _FormulaEvaluator:
    """Internal recursive AST evaluator for verified formula trees."""

    def __init__(self, data: pa.Table | dict[str, Any]) -> None:
        self.data = data
        if isinstance(data, pa.Table):
            self.series_length = data.num_rows
        elif isinstance(data, dict):
            first_val: list[Any] = next(iter(data.values()), [])
            self.series_length = len(first_val)
        else:
            self.series_length = 0

    def eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            name_lower = node.id.lower()
            if name_lower in ("open", "high", "low", "close", "volume", "oi", "open_interest"):
                col = "open_interest" if name_lower == "oi" else name_lower
                return extract_series_nullable(self.data, col)
            elif (
                isinstance(self.data, pa.Table)
                and (node.id in self.data.column_names or name_lower in self.data.column_names)
            ) or (
                isinstance(self.data, dict) and (node.id in self.data or name_lower in self.data)
            ):
                col_target = (
                    node.id
                    if (isinstance(self.data, dict) and node.id in self.data)
                    else name_lower
                )
                return extract_series_nullable(self.data, col_target)
            elif name_lower == "true":
                return True
            elif name_lower == "false":
                return False
            elif name_lower == "none":
                return None
            else:
                return node.id

        elif isinstance(node, ast.UnaryOp):
            operand = self.eval_node(node.operand)
            un_op = node.op
            if isinstance(un_op, ast.USub):
                return self._map_unary(operand, lambda x: -x)
            elif isinstance(un_op, ast.Not):
                return self._map_unary(operand, lambda x: not bool(x))
            elif isinstance(un_op, ast.UAdd):
                return operand
            raise FormulaEvaluationError(f"Unsupported unary operator {type(un_op).__name__}")

        elif isinstance(node, ast.BinOp):
            left = self.eval_node(node.left)
            right = self.eval_node(node.right)
            bin_op = node.op
            if isinstance(bin_op, ast.Add):
                return self._map_binary(left, right, lambda a, b: a + b)
            elif isinstance(bin_op, ast.Sub):
                return self._map_binary(left, right, lambda a, b: a - b)
            elif isinstance(bin_op, ast.Mult):
                return self._map_binary(left, right, lambda a, b: a * b)
            elif isinstance(bin_op, ast.Div):
                return self._map_binary(left, right, lambda a, b: (a / b) if b != 0 else None)
            elif isinstance(bin_op, ast.Mod):
                return self._map_binary(left, right, lambda a, b: a % b)
            elif isinstance(bin_op, ast.Pow):
                return self._map_binary(left, right, lambda a, b: a**b)
            raise FormulaEvaluationError(f"Unsupported binary operator {type(bin_op).__name__}")

        elif isinstance(node, ast.BoolOp):
            bool_op = node.op
            values = [self.eval_node(v) for v in node.values]
            if isinstance(bool_op, ast.And):
                res = values[0]
                for v in values[1:]:
                    res = self._map_binary(res, v, lambda a, b: bool(a and b))
                return res
            elif isinstance(bool_op, ast.Or):
                res = values[0]
                for v in values[1:]:
                    res = self._map_binary(res, v, lambda a, b: bool(a or b))
                return res

        elif isinstance(node, ast.Compare):
            left = self.eval_node(node.left)
            res = None
            for cmp_op, comparator in zip(node.ops, node.comparators, strict=True):
                right = self.eval_node(comparator)
                if isinstance(cmp_op, ast.Eq):
                    cmp_res = self._map_binary(left, right, lambda a, b: a == b)
                elif isinstance(cmp_op, ast.NotEq):
                    cmp_res = self._map_binary(left, right, lambda a, b: a != b)
                elif isinstance(cmp_op, ast.Lt):
                    cmp_res = self._map_binary(left, right, lambda a, b: a < b)
                elif isinstance(cmp_op, ast.LtE):
                    cmp_res = self._map_binary(left, right, lambda a, b: a <= b)
                elif isinstance(cmp_op, ast.Gt):
                    cmp_res = self._map_binary(left, right, lambda a, b: a > b)
                elif isinstance(cmp_op, ast.GtE):
                    cmp_res = self._map_binary(left, right, lambda a, b: a >= b)
                else:
                    raise FormulaEvaluationError(f"Unsupported comparator {type(cmp_op).__name__}")
                left = right
                if res is None:
                    res = cmp_res
                else:
                    res = self._map_binary(res, cmp_res, lambda a, b: bool(a and b))
            return res

        elif isinstance(node, ast.IfExp):
            cond = self.eval_node(node.test)
            true_val = self.eval_node(node.body)
            false_val = self.eval_node(node.orelse)
            cond_list = cond if isinstance(cond, list) else [cond] * self.series_length
            return helper_if_else(cond_list, true_val, false_val)

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FormulaEvaluationError("Invalid dynamic call")
            func_name = node.func.id.lower()
            args = [self.eval_node(a) for a in node.args]
            kwargs = {kw.arg: self.eval_node(kw.value) for kw in node.keywords if kw.arg}

            # Built-in math / signal functions
            if func_name == "crossover":
                return helper_crossover(args[0], args[1])
            elif func_name == "crossunder":
                return helper_crossunder(args[0], args[1])
            elif func_name == "cross":
                return helper_cross(args[0], args[1])
            elif func_name == "shift":
                return helper_shift(args[0], int(args[1]))
            elif func_name == "highest":
                return helper_highest(args[0], int(args[1]))
            elif func_name == "lowest":
                return helper_lowest(args[0], int(args[1]))
            elif func_name == "if_else":
                return helper_if_else(args[0], args[1], args[2])
            elif func_name == "abs":
                return self._map_unary(args[0], abs)
            elif func_name == "min":
                return self._map_binary(args[0], args[1], min)
            elif func_name == "max":
                return self._map_binary(args[0], args[1], max)

            # Indicator registry functions
            if func_name in registry._indicators:
                params: dict[str, Any] = {}
                meta = registry.get(func_name)
                exec_data: dict[str, Any] = {}
                if isinstance(self.data, pa.Table):
                    for col in self.data.column_names:
                        exec_data[col] = self.data[col].to_pylist()
                elif isinstance(self.data, dict):
                    exec_data.update(self.data)

                numeric_keys = [
                    k for k, v in meta.default_params.items() if isinstance(v, (int, float))
                ]
                num_idx = 0

                for a in args:
                    if isinstance(a, list):
                        exec_data["_indicator_input_series"] = a
                        params["column"] = "_indicator_input_series"
                    elif isinstance(a, (int, float)):
                        if num_idx < len(numeric_keys):
                            params[numeric_keys[num_idx]] = a
                            num_idx += 1
                    elif isinstance(a, str):
                        params["column"] = a

                params.update(kwargs)

                res = registry.compute(func_name, exec_data, params=params)
                if isinstance(res, dict):
                    first_k = next(iter(res.keys()))
                    return res[first_k]
                return res

            raise FormulaEvaluationError(f"Function '{func_name}' not implemented in evaluator")

        raise FormulaEvaluationError(f"Unhandled AST node {type(node).__name__}")

    def _map_unary(self, val: Any, func: Any) -> list[Any]:
        if not isinstance(val, list):
            res = func(val) if val is not None else None
            return [res] * self.series_length
        return [func(x) if x is not None else None for x in val]

    def _map_binary(self, a: Any, b: Any, func: Any) -> list[Any]:
        n = self.series_length
        a_list = a if isinstance(a, list) else [a] * n
        b_list = b if isinstance(b, list) else [b] * n

        out: list[Any] = [None] * n
        for i in range(n):
            x = a_list[i]
            y = b_list[i]
            if x is None or y is None:
                out[i] = None
            else:
                try:
                    out[i] = func(x, y)
                except ZeroDivisionError:
                    out[i] = None
        return out


class FormulaCompiler:
    """Compiles and sandboxes technical formulas."""

    def __init__(self, validator: FormulaASTValidator | None = None) -> None:
        self.validator = validator or FormulaASTValidator()

    def compile(self, formula_str: str) -> CompiledFormula:
        """Parse formula, run security visitor, and return CompiledFormula."""
        if not formula_str or not formula_str.strip():
            raise FormulaSyntaxError("Empty formula expression")

        try:
            parsed = ast.parse(formula_str.strip(), mode="eval")
        except SyntaxError as e:
            raise FormulaSyntaxError(f"Syntax error in formula: {e}") from e

        # Validate AST security
        self.validator.visit(parsed)

        return CompiledFormula(raw_formula=formula_str, parsed_ast=parsed)
