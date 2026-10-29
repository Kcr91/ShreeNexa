"""Unit tests for the rule-based strategy-text extractor."""

from __future__ import annotations

import pytest

from app.strategy.extraction import (
    extract_strategy_from_text,
    extract_text_from_pdf_bytes,
)


EMA_CROSS_TEXT = """
Moving Average Crossover Strategy
=================================

Timeframe: 15-minute chart on NIFTY 50 index.

Indicators:
- 9-period exponential moving average (EMA)
- 21-period EMA
- RSI(14) as a confirmation filter

Entry Conditions:
Buy when the 9 EMA crosses above the 21 EMA and RSI > 50.

Exit Conditions:
Exit when the 9 EMA crosses below the 21 EMA.

Risk Management:
Maintain a stop loss of 1.5% below entry and a target of 3% above entry.
"""


def test_extracts_indicators_from_ema_cross_text() -> None:
    result = extract_strategy_from_text(EMA_CROSS_TEXT, name="EMA Cross")
    ir = result.strategy_ir
    assert ir["name"] == "EMA Cross"
    assert ir["timeframe"] == "15m"
    # Should include EMA (two periods) and RSI
    inds = ir["indicators"]
    ind_keys = set(inds.keys())
    assert any(k.startswith("ema_") for k in ind_keys)
    assert any(k.startswith("rsi") for k in ind_keys)


def test_detects_stop_loss_and_target_percentages() -> None:
    result = extract_strategy_from_text(EMA_CROSS_TEXT)
    exits = result.strategy_ir["exits"]
    sl = next(e for e in exits if e["type"] == "stop")
    tp = next(e for e in exits if e["type"] == "target")
    assert sl["pct"] == 1.5
    assert tp["pct"] == 3.0


def test_report_lists_components_with_source_text() -> None:
    result = extract_strategy_from_text(EMA_CROSS_TEXT)
    rep = result.extraction_report
    assert rep.confidence in {"high", "medium"}
    assert len(rep.components_found.indicators) >= 2
    assert rep.components_found.timeframe is not None
    assert any("stop" in c.description.lower() for c in rep.components_found.risk_params)


def test_handles_empty_input_without_crashing() -> None:
    result = extract_strategy_from_text("")
    assert result.success is True
    assert result.strategy_ir["timeframe"] == "15m"
    assert any("timeframe" in w.lower() for w in result.extraction_report.warnings)


def test_mean_reversion_inferred_from_rsi() -> None:
    text = "RSI(14) based mean-reversion. Buy when RSI < 30. Sell when RSI > 70. Stop loss 2%. Target 4%."
    result = extract_strategy_from_text(text)
    assert result.strategy_ir["strategy_type"] == "mean_reversion"


def test_pypdf_missing_raises_clear_runtime_error() -> None:
    # When pypdf is not installed in the test env, the loader raises a clear
    # RuntimeError whose message tells the user how to install it. This test
    # does not care which path hits — just that the message is actionable.
    pypdf_present: bool
    try:
        import pypdf  # noqa: F401

        pypdf_present = True
    except ImportError:
        pypdf_present = False

    if pypdf_present:
        pytest.skip("pypdf is installed; cannot assert the missing-import branch here.")

    with pytest.raises(RuntimeError, match="pypdf"):
        extract_text_from_pdf_bytes(b"%PDF-1.4\n%EOF\n")
