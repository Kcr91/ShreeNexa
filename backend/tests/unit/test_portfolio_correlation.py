"""Unit tests for cross-strategy return and signal correlation matrices with NumPy parity."""

from __future__ import annotations

from datetime import date

from app.portfolio import (
    MissingPeriodPolicy,
    align_pairwise_series,
    compute_correlation_matrix,
    compute_series_correlation,
    compute_signal_correlation_matrix,
)


def _reference_pearson(x: list[float], y: list[float]) -> float:
    """Independent reference implementation of Pearson correlation."""
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = (sum((v - mean_x) ** 2 for v in x) * sum((v - mean_y) ** 2 for v in y)) ** 0.5
    return float(round(num / den, 6))


def test_correlation_matrix_numpy_reference_parity() -> None:
    # 3 distinct return series
    r1 = [0.012, -0.005, 0.021, -0.015, 0.008, 0.014, -0.003, 0.019]
    r2 = [0.009, -0.002, 0.015, -0.011, 0.005, 0.010, -0.001, 0.013]  # High positive correlation
    r3 = [-0.008, 0.004, -0.014, 0.010, -0.006, -0.011, 0.002, -0.015]  # Negative correlation

    series_map = {
        "strat_1": r1,
        "strat_2": r2,
        "strat_3": r3,
    }

    result = compute_correlation_matrix(series_map)

    # Reference calculation matching NumPy np.corrcoef
    ref_1_2 = _reference_pearson(r1, r2)
    ref_1_3 = _reference_pearson(r1, r3)
    ref_2_3 = _reference_pearson(r2, r3)

    assert abs(result.matrix[0][1] - ref_1_2) <= 1e-5
    assert abs(result.matrix[0][2] - ref_1_3) <= 1e-5
    assert abs(result.matrix[1][2] - ref_2_3) <= 1e-5

    # Also test standard golden fixture: x=[1,2,3,4], y=[1,3,2,4] -> r=0.800000 exactly
    g_x = [1.0, 2.0, 3.0, 4.0]
    g_y = [1.0, 3.0, 2.0, 4.0]
    g_res, _ = compute_series_correlation(g_x, g_y)
    assert abs(g_res - 0.800000) <= 1e-6

    # Assert diagonal is 1.0
    for i in range(3):
        assert result.matrix[i][i] == 1.0

    # Assert matrix is strictly symmetric
    for i in range(3):
        for j in range(3):
            assert result.matrix[i][j] == result.matrix[j][i]


def test_missing_period_policies() -> None:
    d1 = date(2026, 9, 1)
    d2 = date(2026, 9, 2)
    d3 = date(2026, 9, 3)
    d4 = date(2026, 9, 4)
    d5 = date(2026, 9, 5)

    series_a = {d1: 0.01, d2: -0.02, d3: 0.03, d4: 0.015}
    series_b = {d2: -0.018, d3: 0.028, d4: 0.012, d5: -0.005}

    # 1. DROP_COMMON: inner join on d2, d3, d4
    vec_a, vec_b = align_pairwise_series(series_a, series_b, policy=MissingPeriodPolicy.DROP_COMMON)
    assert len(vec_a) == 3
    assert len(vec_b) == 3
    assert vec_a == [-0.02, 0.03, 0.015]
    assert vec_b == [-0.018, 0.028, 0.012]

    # 2. FILL_ZERO: union of d1..d5 with 0.0 for missing
    vec_a_zero, vec_b_zero = align_pairwise_series(
        series_a, series_b, policy=MissingPeriodPolicy.FILL_ZERO
    )
    assert len(vec_a_zero) == 5
    assert len(vec_b_zero) == 5
    assert vec_a_zero[4] == 0.0  # d5 missing in series_a
    assert vec_b_zero[0] == 0.0  # d1 missing in series_b

    # Verify correlation matrix sample counts with DROP_COMMON
    matrix_res = compute_correlation_matrix(
        {"strat_a": series_a, "strat_b": series_b},
        policy=MissingPeriodPolicy.DROP_COMMON,
    )
    assert matrix_res.sample_counts[0][1] == 3
    assert matrix_res.matrix[0][1] > 0.95  # Strong correlation on common dates


def test_constant_series_zero_variance_behavior() -> None:
    # Constant series (e.g. 100% cash with 0.0 return)
    constant_series = [0.0, 0.0, 0.0, 0.0, 0.0]
    varying_series = [0.01, -0.02, 0.015, -0.01, 0.02]

    coeff, warning = compute_series_correlation(constant_series, varying_series)

    # Must return 0.0 without ZeroDivisionError
    assert coeff == 0.0
    assert warning is not None
    assert "Constant series" in warning


def test_short_series_min_periods_handling() -> None:
    short_x = [0.05]
    short_y = [0.02]

    coeff, warning = compute_series_correlation(short_x, short_y, min_periods=2)

    assert coeff == 0.0
    assert warning is not None
    assert "Short series" in warning


def test_signal_correlation_matrix() -> None:
    d1 = date(2026, 9, 1)
    d2 = date(2026, 9, 2)
    d3 = date(2026, 9, 3)
    d4 = date(2026, 9, 4)

    # Identical trend signals
    signals_trend = {d1: 1.0, d2: 1.0, d3: -1.0, d4: 0.0}
    # Opposite mean-reversion signals
    signals_contrarian = {d1: -1.0, d2: -1.0, d3: 1.0, d4: 0.0}

    res = compute_signal_correlation_matrix(
        {"trend": signals_trend, "contrarian": signals_contrarian}
    )

    # Exactly inverse signals should have correlation == -1.0
    assert abs(res.matrix[0][1] - (-1.0)) <= 1e-5
    assert res.matrix[0][0] == 1.0
    assert res.matrix[1][1] == 1.0
