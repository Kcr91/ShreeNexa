"""Unit tests and security fuzz tests for the safe formula parser, AST validator, and compiler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.indicators import FormulaCompiler, FormulaSecurityError, FormulaSyntaxError

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


@pytest.mark.parametrize(
    "payload",
    [
        "__import__('os').system('calc')",
        "eval('2 + 2')",
        "exec('a = 1')",
        "open('/etc/passwd')",
        "close.__class__",
        "(1).real",
        "lambda x: x + 1",
        "[x for x in close]",
        "{k: v for k, v in ()}",
        "(x for x in close)",
        "shift(close, -1)",
        "shift(close, -5)",
        "__builtins__",
        "__globals__",
        "unregistered_function(close)",
        "import math",
    ],
)
def test_adversarial_security_payloads_blocked(payload: str) -> None:
    """Security Fuzz Test: All dangerous AST constructs and lookahead calls are rejected."""
    compiler = FormulaCompiler()
    with pytest.raises((FormulaSecurityError, FormulaSyntaxError)):
        compiler.compile(payload)


def test_syntax_error_handling() -> None:
    """Verify malformed syntax raises FormulaSyntaxError."""
    compiler = FormulaCompiler()
    with pytest.raises(FormulaSyntaxError):
        compiler.compile("close > > 100")
    with pytest.raises(FormulaSyntaxError):
        compiler.compile("")


def test_arithmetic_and_comparison_formula_evaluation() -> None:
    """Verify evaluating standard arithmetic, comparisons, and boolean logic."""
    data = get_test_dataset()
    compiler = FormulaCompiler()

    # 1. Price spread
    compiled = compiler.compile("(close - open) / open * 100")
    res = compiled.evaluate(data)
    assert len(res) == len(data["close"])
    assert round(res[0], 2) == 0.50

    # 2. Boolean comparison and logic
    compiled_bool = compiler.compile("close > 110.0 and volume >= 2500")
    res_bool = compiled_bool.evaluate(data)
    assert res_bool[0] is False
    assert res_bool[-1] is True


def test_indicator_and_signal_crossover_compilation() -> None:
    """Verify compiling compound indicator signal expressions."""
    data = get_test_dataset()
    compiler = FormulaCompiler()

    # Formula with SMA, EMA, and crossover helper
    formula_str = "crossover(sma(5), ema(5)) or rsi(14) > 50"
    compiled = compiler.compile(formula_str)
    res = compiled.evaluate(data)

    assert len(res) == len(data["close"])
    assert all(x is None or isinstance(x, bool) for x in res)


def test_shift_and_highest_lowest_helpers() -> None:
    """Verify safe backward shift, highest, and lowest helpers."""
    data = get_test_dataset()
    compiler = FormulaCompiler()

    # Safe shift by 2 bars
    compiled_shift = compiler.compile("shift(close, 2)")
    res_shift = compiled_shift.evaluate(data)
    assert res_shift[0] is None
    assert res_shift[1] is None
    assert res_shift[2] == data["close"][0]

    # Highest high over 3 bars
    compiled_hh = compiler.compile("highest(high, 3)")
    res_hh = compiled_hh.evaluate(data)
    assert res_hh[0] is None
    assert res_hh[1] is None
    assert res_hh[2] == max(data["high"][:3])


def test_ternary_if_else_evaluation() -> None:
    """Verify ternary conditional if_else helper."""
    data = get_test_dataset()
    compiler = FormulaCompiler()

    compiled = compiler.compile("if_else(close > open, 1.0, -1.0)")
    res = compiled.evaluate(data)
    assert len(res) == len(data["close"])
    assert all(x in (1.0, -1.0) for x in res)
