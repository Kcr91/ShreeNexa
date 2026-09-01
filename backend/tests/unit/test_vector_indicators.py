"""Unit tests for indicator registry, primitives, warm-up rules, and reference parity."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pytest
from app.indicators import registry

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_indicators_reference.json"


def test_indicator_registry_discovery() -> None:
    """Verify all 12 primitives are registered in the global registry."""
    indicators = registry.list_indicators()
    names = {ind.name for ind in indicators}

    expected_names = {
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
    }
    assert expected_names.issubset(names)


def test_sma_and_obv_reference_parity() -> None:
    """Verify SMA and OBV calculations against sample_indicators_reference.json."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    prices = data["prices"]
    volumes = data["volumes"]

    dataset = {
        "close": prices,
        "volume": volumes,
    }

    # SMA(5)
    sma_res = registry.compute("sma", dataset, params={"period": 5, "column": "close"})
    assert isinstance(sma_res, list)

    expected_sma = data["expected_sma_5"]
    for i, exp in enumerate(expected_sma):
        if exp is None:
            assert sma_res[i] is None
        else:
            assert sma_res[i] is not None
            assert abs(sma_res[i] - exp) < 1e-4

    # OBV
    obv_res = registry.compute("obv", dataset)
    assert isinstance(obv_res, list)
    expected_obv = data["expected_obv"]
    for i, exp in enumerate(expected_obv):
        assert obv_res[i] is not None
        assert abs(obv_res[i] - exp) < 1e-4


def test_rsi_and_bollinger_bands_calculation() -> None:
    """Verify RSI and Bollinger Bands multi-output indicator execution."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    prices = data["prices"]
    dataset = {"close": prices}

    # RSI(5)
    rsi_res = registry.compute("rsi", dataset, params={"period": 5})
    assert isinstance(rsi_res, list)
    assert rsi_res[0] is None
    # Values after warmup should be in [0, 100]
    valid_rsi = [x for x in rsi_res if x is not None]
    assert len(valid_rsi) > 0
    assert all(0.0 <= x <= 100.0 for x in valid_rsi)

    # Bollinger Bands(5, 2.0)
    bb_res = registry.compute("bollinger_bands", dataset, params={"period": 5, "std_dev": 2.0})
    assert isinstance(bb_res, dict)
    assert "upper" in bb_res
    assert "middle" in bb_res
    assert "lower" in bb_res
    assert "pct_b" in bb_res
    assert "bandwidth" in bb_res

    # Upper >= Middle >= Lower
    for i in range(4, len(prices)):
        u = bb_res["upper"][i]
        m = bb_res["middle"][i]
        low = bb_res["lower"][i]
        assert u is not None and m is not None and low is not None
        assert u >= m >= low


def test_arrow_table_and_multi_output_macd() -> None:
    """Verify invocation with PyArrow Table and MACD dictionary outputs."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    prices = data["prices"]
    table = pa.Table.from_pydict({"close": prices})

    macd_res = registry.compute(
        "macd",
        table,
        params={"fast_period": 3, "slow_period": 6, "signal_period": 3},
    )
    assert isinstance(macd_res, dict)
    assert "macd" in macd_res
    assert "signal" in macd_res
    assert "hist" in macd_res


def test_missing_indicator_raises_key_error() -> None:
    """Verify querying an unregistered indicator raises KeyError."""
    with pytest.raises(KeyError, match="not found in registry"):
        registry.compute("non_existent_indicator", {"close": [1, 2, 3]})
