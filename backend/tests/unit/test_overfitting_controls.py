"""Unit tests for Deflated Sharpe Ratio, CSCV PBO, and White's Reality Check."""

from __future__ import annotations

import random

import pytest
from app.backtest.overfitting import (
    _norm_cdf,
    _norm_ppf,
    calculate_deflated_sharpe_ratio,
    calculate_pbo,
    calculate_whites_reality_check,
    generate_overfitting_report,
)


def test_norm_cdf_and_ppf_accuracy() -> None:
    """Verify standard normal CDF and inverse PPF accuracy and symmetry."""
    assert _norm_cdf(0.0) == pytest.approx(0.5)
    assert _norm_ppf(0.5) == pytest.approx(0.0)
    assert _norm_cdf(1.95996) == pytest.approx(0.975, abs=1e-4)
    assert _norm_ppf(0.975) == pytest.approx(1.95996, abs=1e-4)
    assert _norm_ppf(0.05) == pytest.approx(-1.64485, abs=1e-4)


def test_deflated_sharpe_ratio_multiple_testing_penalty() -> None:
    """Verify DSR decreases as number of trials N and trials variance V increase."""
    # Generate 500 daily returns with positive mean and Sharpe ~1.5
    rng = random.Random(42)
    # Mean = 0.0006, Std = 0.0063 -> Annualized Sharpe = (0.0006 / 0.0063) * sqrt(252) ~ 1.5
    returns = [rng.gauss(0.0006, 0.0063) for _ in range(500)]

    # 1. Single Trial (N = 1): DSR must equal PSR
    dsr_single = calculate_deflated_sharpe_ratio(returns, trials_count=1, trials_variance=0.0)
    assert dsr_single.expected_max_sharpe == 0.0
    assert dsr_single.deflated_sharpe_ratio == pytest.approx(dsr_single.psr)
    assert dsr_single.psr > 0.99  # Strong confidence on 500 bars with SR ~ 1.5

    # 2. Multi-Trial Penalty (N = 100, Variance = 0.5):
    # DSR must penalize for multiple testing: DSR < PSR
    dsr_multi = calculate_deflated_sharpe_ratio(returns, trials_count=100, trials_variance=0.5)
    assert dsr_multi.expected_max_sharpe > 0.0
    assert dsr_multi.deflated_sharpe_ratio < dsr_single.deflated_sharpe_ratio
    assert dsr_multi.estimated_sharpe == pytest.approx(dsr_single.estimated_sharpe)


def test_pbo_cscv_calculation() -> None:
    """Test Probability of Backtest Overfitting (PBO) on persistent vs overfit matrices."""
    # 1. Persistent Matrix: Strategy 0 is consistently superior across all slices
    n_bars = 120
    n_strats = 5
    persistent_matrix: list[list[float]] = []
    for _ in range(n_bars):
        row = [0.01] + [0.001 * (k + 1) for k in range(1, n_strats)]
        persistent_matrix.append(row)

    res_persistent = calculate_pbo(persistent_matrix, num_slices=6)
    assert res_persistent.combinations_count == 20  # 6 choose 3 = 20
    # Relative rank is always 1 / (5 + 1) = 0.1667 (< 0.5)
    assert res_persistent.pbo == 0.0

    # 2. Inverted Matrix (Overfit): Strategy 0 wins in first half, loses in second half
    overfit_matrix: list[list[float]] = []
    for i in range(n_bars):
        if i < n_bars // 2:
            row = [0.05, 0.01, 0.01, 0.01, 0.01]
        else:
            row = [-0.05, 0.02, 0.02, 0.02, 0.02]
        overfit_matrix.append(row)

    res_overfit = calculate_pbo(overfit_matrix, num_slices=6)
    assert res_overfit.pbo > 0.0


def test_whites_reality_check_data_snooping() -> None:
    """Verify White's Reality Check p-value discriminates between noise and genuine alpha."""
    rng = random.Random(42)
    n_bars = 300
    n_strats = 15

    # 1. Pure Noise Matrix (Zero mean Gaussian noise)
    noise_matrix = [[rng.gauss(0.0, 0.01) for _ in range(n_strats)] for _ in range(n_bars)]
    wrc_noise = calculate_whites_reality_check(noise_matrix, iterations=500, seed=42)

    # In pure noise, maximum mean is pure snooping artifact; p-value should not be significant
    assert wrc_noise.p_value > 0.05
    assert not wrc_noise.is_significant

    # 2. Genuine Alpha Matrix (Strategy 0 has strong positive drift)
    alpha_matrix = [
        [rng.gauss(0.003, 0.01)] + [rng.gauss(0.0, 0.01) for _ in range(n_strats - 1)]
        for _ in range(n_bars)
    ]
    wrc_alpha = calculate_whites_reality_check(alpha_matrix, iterations=500, seed=42)

    # Significant alpha rejection
    assert wrc_alpha.p_value < 0.05
    assert wrc_alpha.is_significant


def test_comprehensive_overfitting_report() -> None:
    """Test OverfittingReport generation and threshold alert triggers."""
    rng = random.Random(42)
    returns = [rng.gauss(0.0001, 0.01) for _ in range(100)]

    # Heavy multiple testing penalty triggering warning
    report = generate_overfitting_report(
        selected_returns=returns,
        trials_count=200,
        trials_variance=0.8,
    )

    assert report.is_overfit
    assert len(report.warnings) > 0
    assert "Deflated Sharpe Ratio" in report.warnings[0]
