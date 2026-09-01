"""Hypothesis-based property tests for technical indicator mathematical invariants."""

from __future__ import annotations

import math

import hypothesis.strategies as st
from app.indicators.registry import registry
from hypothesis import given, settings

# Price list strategy: realistic positive price sequences
prices_strategy = st.lists(
    st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    min_size=20,
    max_size=50,
)


@given(
    st.lists(
        st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        min_size=5,
        max_size=30,
    )
)
@settings(max_examples=50)
def test_identity_period_1_sma_and_ema(prices: list[float]) -> None:
    """Identity Law: Period=1 SMA and EMA equal the exact underlying price series."""
    data = {"close": prices}
    sma_out = registry.compute("sma", data, params={"period": 1, "column": "close"})
    ema_out = registry.compute("ema", data, params={"period": 1, "column": "close"})

    assert isinstance(sma_out, list)
    assert isinstance(ema_out, list)

    for i in range(len(prices)):
        s_val = sma_out[i]
        e_val = ema_out[i]
        assert s_val is not None
        assert e_val is not None
        assert math.isclose(s_val, prices[i], rel_tol=1e-5)
        assert math.isclose(e_val, prices[i], rel_tol=1e-5)


@given(
    st.floats(min_value=10.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=15, max_value=40),
)
@settings(max_examples=50)
def test_constant_series_invariants(const_price: float, length: int) -> None:
    """Constant Series: Flat price series produces zero dispersion and constant mean."""
    prices = [const_price] * length
    data = {
        "open": prices,
        "high": prices,
        "low": prices,
        "close": prices,
        "volume": [1000.0] * length,
    }

    sma = registry.compute("sma", data, params={"period": 5, "column": "close"})
    ema = registry.compute("ema", data, params={"period": 5, "column": "close"})
    rstd = registry.compute("rolling_std", data, params={"period": 5, "column": "close"})
    bb = registry.compute(
        "bollinger_bands", data, params={"period": 5, "std_dev": 2.0, "column": "close"}
    )
    atr = registry.compute("atr", data, params={"period": 5})

    assert isinstance(sma, list)
    assert isinstance(ema, list)
    assert isinstance(rstd, list)
    assert isinstance(bb, dict)
    assert isinstance(atr, list)

    for i in range(4, length):
        s_val = sma[i]
        e_val = ema[i]
        r_val = rstd[i]
        a_val = atr[i]
        bb_m = bb["middle"][i]
        bb_u = bb["upper"][i]
        bb_l = bb["lower"][i]

        assert s_val is not None and math.isclose(s_val, const_price, rel_tol=1e-5)
        assert e_val is not None and math.isclose(e_val, const_price, rel_tol=1e-5)
        assert r_val is not None and math.isclose(r_val, 0.0, abs_tol=1e-5)
        assert a_val is not None and math.isclose(a_val, 0.0, abs_tol=1e-5)
        assert bb_m is not None and math.isclose(bb_m, const_price, rel_tol=1e-5)
        assert bb_u is not None and math.isclose(bb_u, const_price, rel_tol=1e-5)
        assert bb_l is not None and math.isclose(bb_l, const_price, rel_tol=1e-5)


@given(
    prices_strategy,
    st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50)
def test_scale_homogeneity_property(prices: list[float], alpha: float) -> None:
    """Scale Homogeneity: Indicator(alpha * X) == alpha * Indicator(X)."""
    scaled_prices = [p * alpha for p in prices]

    d1 = {"close": prices}
    d2 = {"close": scaled_prices}

    sma_base = registry.compute("sma", d1, params={"period": 5, "column": "close"})
    sma_scaled = registry.compute("sma", d2, params={"period": 5, "column": "close"})
    rstd_base = registry.compute("rolling_std", d1, params={"period": 5, "column": "close"})
    rstd_scaled = registry.compute("rolling_std", d2, params={"period": 5, "column": "close"})

    assert isinstance(sma_base, list) and isinstance(sma_scaled, list)
    assert isinstance(rstd_base, list) and isinstance(rstd_scaled, list)

    for i in range(4, len(prices)):
        b_sma = sma_base[i]
        s_sma = sma_scaled[i]
        assert b_sma is not None and s_sma is not None
        expected_sma = b_sma * alpha
        assert math.isclose(s_sma, expected_sma, rel_tol=1e-4)

        b_rstd = rstd_base[i]
        s_rstd = rstd_scaled[i]
        assert b_rstd is not None and s_rstd is not None
        expected_rstd = b_rstd * alpha
        assert math.isclose(s_rstd, expected_rstd, rel_tol=1e-4)


@given(
    prices_strategy,
    st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50)
def test_translation_invariance_property(prices: list[float], beta: float) -> None:
    """Translation Invariance: Dispersions remain invariant under constant additions."""
    shifted_prices = [p + beta for p in prices]
    d1 = {"close": prices}
    d2 = {"close": shifted_prices}

    rstd_base = registry.compute("rolling_std", d1, params={"period": 5, "column": "close"})
    rstd_shifted = registry.compute("rolling_std", d2, params={"period": 5, "column": "close"})
    sma_base = registry.compute("sma", d1, params={"period": 5, "column": "close"})
    sma_shifted = registry.compute("sma", d2, params={"period": 5, "column": "close"})

    assert isinstance(rstd_base, list) and isinstance(rstd_shifted, list)
    assert isinstance(sma_base, list) and isinstance(sma_shifted, list)

    for i in range(4, len(prices)):
        b_rstd = rstd_base[i]
        s_rstd = rstd_shifted[i]
        assert b_rstd is not None and s_rstd is not None
        assert math.isclose(s_rstd, b_rstd, rel_tol=1e-4)

        b_sma = sma_base[i]
        s_sma = sma_shifted[i]
        assert b_sma is not None and s_sma is not None
        expected_sma = b_sma + beta
        assert math.isclose(s_sma, expected_sma, rel_tol=1e-4)


@given(prices_strategy)
@settings(max_examples=50)
def test_boundedness_and_envelope_ordering(prices: list[float]) -> None:
    """Boundedness & Envelope Monotonicity: 0 <= RSI <= 100 and lower <= middle <= upper."""
    n = len(prices)
    highs = [p + 2.0 for p in prices]
    lows = [max(0.1, p - 2.0) for p in prices]
    data = {
        "open": prices,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": [1000.0] * n,
    }

    rsi = registry.compute("rsi", data, params={"period": 14, "column": "close"})
    stoch = registry.compute("stochastic", data, params={"k_period": 14, "d_period": 3})
    bb = registry.compute(
        "bollinger_bands", data, params={"period": 10, "std_dev": 2.0, "column": "close"}
    )

    assert isinstance(rsi, list)
    assert isinstance(stoch, dict)
    assert isinstance(bb, dict)

    for i in range(n):
        r_val = rsi[i]
        if r_val is not None:
            assert -1e-5 <= r_val <= 100.00001, f"RSI bound violation: {r_val}"

        k_val = stoch["k"][i]
        if k_val is not None:
            assert -1e-5 <= k_val <= 100.00001, f"Stochastic %K bound violation: {k_val}"

        bb_m = bb["middle"][i]
        bb_l = bb["lower"][i]
        bb_u = bb["upper"][i]
        if bb_m is not None and bb_l is not None and bb_u is not None:
            assert bb_l <= bb_m + 1e-5, f"Bollinger lower > middle: {bb_l} vs {bb_m}"
            assert bb_m <= bb_u + 1e-5, f"Bollinger middle > upper: {bb_m} vs {bb_u}"
