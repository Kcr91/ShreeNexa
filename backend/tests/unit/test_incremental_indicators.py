"""Unit tests for incremental indicator streaming, G1 parity property, and state persistence."""

from __future__ import annotations

import json
from pathlib import Path

from app.indicators import create_incremental_indicator, registry

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_indicators_reference.json"


def get_sample_bars() -> list[dict[str, float]]:
    """Construct a synthetic series of OHLCV bars from reference fixture."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    prices = data["prices"]
    volumes = data["volumes"]

    bars: list[dict[str, float]] = []
    for c, v in zip(prices, volumes, strict=True):
        bars.append(
            {
                "open": c - 0.5,
                "high": c + 1.5,
                "low": c - 1.5,
                "close": c,
                "volume": float(v),
            }
        )
    return bars


def test_g1_parity_for_all_registered_primitives() -> None:
    """G1 Property Test: Streaming bar-by-bar matches batch vector compute for every primitive."""
    bars = get_sample_bars()
    data_dict = {
        "open": [b["open"] for b in bars],
        "high": [b["high"] for b in bars],
        "low": [b["low"] for b in bars],
        "close": [b["close"] for b in bars],
        "volume": [b["volume"] for b in bars],
    }

    indicators = registry.list_indicators()
    assert len(indicators) >= 12

    for meta in indicators:
        name = meta.name
        # 1. Compute batch vector output
        vec_out = registry.compute(name, data_dict, params=meta.default_params)

        # 2. Compute incremental streaming output bar-by-bar
        inc_ind = create_incremental_indicator(name, params=meta.default_params)
        inc_outputs: list[float | dict[str, float | None] | None] = []

        for b in bars:
            val = inc_ind.update(b)
            inc_outputs.append(val)

        # 3. Assert exact parity
        assert len(inc_outputs) == len(bars), f"Length mismatch for {name}"

        if isinstance(vec_out, list):
            for i in range(len(bars)):
                v_val = vec_out[i]
                i_val = inc_outputs[i]
                if v_val is None:
                    assert i_val is None, f"{name} at {i}: expected None, got {i_val}"
                else:
                    assert i_val is not None, f"{name} at {i}: expected {v_val}, got None"
                    assert isinstance(i_val, (int, float))
                    diff = abs(float(i_val) - float(v_val))
                    assert diff < 1e-3, (
                        f"G1 parity failure on {name} at index {i}: vector={v_val}, inc={i_val}"
                    )
        elif isinstance(vec_out, dict):
            for k in meta.output_keys:
                v_list = vec_out[k]
                for i in range(len(bars)):
                    v_val = v_list[i]
                    i_dict = inc_outputs[i]
                    if v_val is None:
                        # For multi-output indicators during warm-up
                        if i_dict is not None:
                            assert isinstance(i_dict, dict)
                    else:
                        assert i_dict is not None, f"{name}[{k}] at {i}: expected {v_val}, got None"
                        assert isinstance(i_dict, dict)
                        assert k in i_dict, f"Missing key {k} in incremental output for {name}"
                        dict_val = i_dict[k]
                        assert dict_val is not None
                        diff = abs(float(dict_val) - float(v_val))
                        assert diff < 1e-3, (
                            f"G1 parity failure {name}[{k}] at {i}: vec={v_val}, inc={dict_val}"
                        )


def test_incremental_state_checkpoint_and_restore() -> None:
    """Verify serialization and restoration of incremental indicator state."""
    bars = get_sample_bars()
    inc = create_incremental_indicator("sma", {"period": 5, "column": "close"})

    # Feed first 7 bars
    for b in bars[:7]:
        inc.update(b)

    state = inc.state
    val_7 = inc.update(bars[7])

    # Clone state into new indicator and feed bar 7
    inc_restored = create_incremental_indicator("sma", {"period": 5, "column": "close"})
    inc_restored.restore_state(state)
    val_restored_7 = inc_restored.update(bars[7])

    assert val_7 == val_restored_7


def test_incremental_reset_cleans_buffers() -> None:
    """Verify reset() clears all internal state and buffers."""
    bars = get_sample_bars()
    inc = create_incremental_indicator("sma", {"period": 5, "column": "close"})

    for b in bars[:5]:
        inc.update(b)
    assert inc.is_ready is True

    inc.reset()
    assert inc.is_ready is False
    assert inc.update(bars[0]) is None
