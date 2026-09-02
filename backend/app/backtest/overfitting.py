"""Statistical multi-testing correction, Deflated Sharpe Ratio, and CSCV PBO analysis."""

from __future__ import annotations

import itertools
import math
import random

from pydantic import BaseModel, ConfigDict, Field


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function (CDF)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF using Acklam's algorithm (16-digit precision)."""
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")

    # Coefficients in rational approximations
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )


class DeflatedSharpeResult(BaseModel):
    """Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR) analysis."""

    model_config = ConfigDict(extra="forbid")

    estimated_sharpe: float
    expected_max_sharpe: float
    psr: float
    deflated_sharpe_ratio: float
    skewness: float
    kurtosis: float
    trials_count: int
    observations_count: int


class PBOResult(BaseModel):
    """Probability of Backtest Overfitting (PBO) via CSCV."""

    model_config = ConfigDict(extra="forbid")

    pbo: float = Field(description="Probability of Backtest Overfitting in [0, 1]")
    combinations_count: int
    logits: list[float]
    relative_ranks: list[float]


class WhiteRealityCheckResult(BaseModel):
    """White's Reality Check for data snooping."""

    model_config = ConfigDict(extra="forbid")

    best_strategy_mean: float
    p_value: float
    bootstrap_iterations: int
    is_significant: bool


class OverfittingReport(BaseModel):
    """Comprehensive backtest overfitting and data snooping audit report."""

    model_config = ConfigDict(extra="forbid")

    dsr: DeflatedSharpeResult
    pbo: PBOResult | None = None
    wrc: WhiteRealityCheckResult | None = None
    is_overfit: bool
    warnings: list[str]


def calculate_deflated_sharpe_ratio(
    returns: list[float],
    trials_count: int = 1,
    trials_variance: float = 0.0,
    annualization_factor: float = 252.0,
) -> DeflatedSharpeResult:
    """Calculate the Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR)."""
    t = len(returns)
    if t < 4:
        return DeflatedSharpeResult(
            estimated_sharpe=0.0,
            expected_max_sharpe=0.0,
            psr=0.5,
            deflated_sharpe_ratio=0.5,
            skewness=0.0,
            kurtosis=3.0,
            trials_count=trials_count,
            observations_count=t,
        )

    mean_r = sum(returns) / t
    var_r = sum((r - mean_r) ** 2 for r in returns) / (t - 1)
    std_r = math.sqrt(var_r) if var_r > 0 else 1e-8

    # Moments (skewness and kurtosis)
    z_scores = [(r - mean_r) / std_r for r in returns]
    skew = sum(z**3 for z in z_scores) / t
    kurt = sum(z**4 for z in z_scores) / t  # Uncentered kurtosis (Normal = 3.0)

    # Per-period and Annualized Sharpe Ratio
    sr_period = mean_r / std_r
    sr_annual = sr_period * math.sqrt(annualization_factor)

    # Standard error of Sharpe Ratio (Mertens, 2002; Bailey & López de Prado, 2014)
    # sigma_sr_period = sqrt((1 - skew*sr + ((kurt - 1)/4)*sr^2) / (T - 1))
    denom = t - 1
    inner = 1.0 - skew * sr_period + ((kurt - 1.0) / 4.0) * (sr_period**2)
    sigma_sr_period = math.sqrt(max(1e-12, inner / denom))
    sigma_sr_annual = sigma_sr_period * math.sqrt(annualization_factor)

    # PSR with benchmark SR* = 0
    z_psr = sr_annual / sigma_sr_annual if sigma_sr_annual > 0 else 0.0
    psr = _norm_cdf(z_psr)

    # Expected Maximum Sharpe Ratio among N trials under H0: SR_0
    emc = 0.57721566490153286  # Euler-Mascheroni constant
    if trials_count > 1 and trials_variance > 0:
        std_v = math.sqrt(trials_variance)
        q1 = _norm_ppf(1.0 - 1.0 / trials_count)
        q2 = _norm_ppf(1.0 - 1.0 / (trials_count * math.e))
        sr_0 = std_v * ((1.0 - emc) * q1 + emc * q2)
    else:
        sr_0 = 0.0

    # DSR = PSR(SR_0)
    z_dsr = (sr_annual - sr_0) / sigma_sr_annual if sigma_sr_annual > 0 else 0.0
    dsr = _norm_cdf(z_dsr)

    return DeflatedSharpeResult(
        estimated_sharpe=sr_annual,
        expected_max_sharpe=sr_0,
        psr=psr,
        deflated_sharpe_ratio=dsr,
        skewness=skew,
        kurtosis=kurt,
        trials_count=trials_count,
        observations_count=t,
    )


def calculate_pbo(
    matrix_returns: list[list[float]],
    num_slices: int = 16,
) -> PBOResult:
    """Calculate Probability of Backtest Overfitting (PBO) via CSCV."""
    if not matrix_returns or not matrix_returns[0]:
        return PBOResult(
            pbo=0.0,
            combinations_count=0,
            logits=[],
            relative_ranks=[],
        )

    t = len(matrix_returns)  # Number of bars
    n = len(matrix_returns[0])  # Number of strategies

    s = min(num_slices, t)
    if s % 2 != 0:
        s -= 1
    if s < 2:
        return PBOResult(
            pbo=0.0,
            combinations_count=0,
            logits=[],
            relative_ranks=[],
        )

    # Divide rows into S slices
    slice_size = t // s
    slices: list[list[list[float]]] = []
    for i in range(s):
        start_row = i * slice_size
        end_row = (i + 1) * slice_size if i < s - 1 else t
        slices.append(matrix_returns[start_row:end_row])

    # All combinations of S/2 slices for training set J
    comb_indices = list(itertools.combinations(range(s), s // 2))
    all_indices_set = set(range(s))

    logits: list[float] = []
    rel_ranks: list[float] = []
    overfit_count = 0

    for train_comb in comb_indices:
        train_set = set(train_comb)
        test_set = all_indices_set - train_set

        # Compute In-Sample cumulative returns for each strategy
        is_sums = [0.0] * n
        for s_idx in train_set:
            for row in slices[s_idx]:
                for k in range(n):
                    is_sums[k] += row[k]

        # Best strategy in IS
        best_k = max(range(n), key=lambda k: is_sums[k])

        # Compute Out-of-Sample cumulative returns for each strategy
        oos_sums = [0.0] * n
        for s_idx in test_set:
            for row in slices[s_idx]:
                for k in range(n):
                    oos_sums[k] += row[k]

        # Rank of best_k in OOS (1 = best, N = worst)
        sorted_oos = sorted(range(n), key=lambda k: oos_sums[k], reverse=True)
        oos_rank = sorted_oos.index(best_k) + 1  # 1-indexed

        # Relative rank lambda = oos_rank / (N + 1)
        rel_rank = oos_rank / (n + 1.0)
        rel_ranks.append(rel_rank)

        # Logit = ln(lambda / (1 - lambda))
        clamped_rank = max(1e-6, min(1.0 - 1e-6, rel_rank))
        logit = math.log(clamped_rank / (1.0 - clamped_rank))
        logits.append(logit)

        if rel_rank > 0.5:
            overfit_count += 1

    pbo = overfit_count / len(comb_indices) if comb_indices else 0.0

    return PBOResult(
        pbo=pbo,
        combinations_count=len(comb_indices),
        logits=logits,
        relative_ranks=rel_ranks,
    )


def calculate_whites_reality_check(
    strategy_returns: list[list[float]],
    benchmark_returns: list[float] | None = None,
    iterations: int = 1000,
    seed: int = 42,
) -> WhiteRealityCheckResult:
    """Calculate White's Reality Check p-value for multiple strategy trials."""
    if not strategy_returns or not strategy_returns[0]:
        return WhiteRealityCheckResult(
            best_strategy_mean=0.0,
            p_value=1.0,
            bootstrap_iterations=iterations,
            is_significant=False,
        )

    t = len(strategy_returns)
    n = len(strategy_returns[0])
    rng = random.Random(seed)

    # Compute excess returns over benchmark
    excess: list[list[float]] = []
    for i in range(t):
        bench = benchmark_returns[i] if benchmark_returns and i < len(benchmark_returns) else 0.0
        row = [strategy_returns[i][k] - bench for k in range(n)]
        excess.append(row)

    # Strategy sample means
    strat_means = [sum(excess[i][k] for i in range(t)) / t for k in range(n)]
    best_mean = max(strat_means)
    v_obs = math.sqrt(t) * max(0.0, best_mean)

    # Stationary bootstrap centered under H0 (mean = 0)
    count_greater = 0
    for _ in range(iterations):
        boot_means = [0.0] * n
        for _ in range(t):
            sample_row = rng.choice(excess)
            for k in range(n):
                # Centered under null
                boot_means[k] += sample_row[k] - strat_means[k]

        boot_means = [m / t for m in boot_means]
        v_boot = math.sqrt(t) * max(0.0, max(boot_means))
        if v_boot >= v_obs:
            count_greater += 1

    p_val = count_greater / iterations if iterations > 0 else 1.0

    return WhiteRealityCheckResult(
        best_strategy_mean=best_mean,
        p_value=p_val,
        bootstrap_iterations=iterations,
        is_significant=p_val < 0.05,
    )


def generate_overfitting_report(
    selected_returns: list[float],
    candidate_returns_matrix: list[list[float]] | None = None,
    trials_count: int = 1,
    trials_variance: float = 0.0,
) -> OverfittingReport:
    """Produce comprehensive backtest overfitting audit with DSR, PBO, and warnings."""
    warnings: list[str] = []

    dsr = calculate_deflated_sharpe_ratio(
        returns=selected_returns,
        trials_count=trials_count,
        trials_variance=trials_variance,
    )

    if dsr.deflated_sharpe_ratio < 0.95:
        warnings.append(
            f"Deflated Sharpe Ratio ({dsr.deflated_sharpe_ratio:.2%}) is below "
            "95% confidence threshold."
        )

    pbo: PBOResult | None = None
    if candidate_returns_matrix and len(candidate_returns_matrix) >= 16:
        pbo = calculate_pbo(candidate_returns_matrix)
        if pbo.pbo > 0.50:
            warnings.append(
                f"High Probability of Backtest Overfitting (PBO: {pbo.pbo:.2%}) detected via CSCV."
            )

    wrc: WhiteRealityCheckResult | None = None
    if candidate_returns_matrix:
        wrc = calculate_whites_reality_check(candidate_returns_matrix)
        if not wrc.is_significant:
            warnings.append(
                f"White's Reality Check p-value ({wrc.p_value:.3f}) does not reject data snooping."
            )

    is_overfit = bool(warnings)

    return OverfittingReport(
        dsr=dsr,
        pbo=pbo,
        wrc=wrc,
        is_overfit=is_overfit,
        warnings=warnings,
    )
