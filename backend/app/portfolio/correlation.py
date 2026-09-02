"""Cross-strategy return and signal correlation matrices with missing-period policies."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date

from app.portfolio.models import CorrelationMatrix, MissingPeriodPolicy


def compute_series_correlation(
    x: Sequence[float],
    y: Sequence[float],
    min_periods: int = 2,
) -> tuple[float, str | None]:
    """Calculate Pearson correlation coefficient between two aligned vectors.

    Returns:
        tuple of (correlation_coefficient, warning_message)
    """
    n = len(x)
    if n != len(y):
        raise ValueError(f"Series lengths must match, got len(x)={len(x)}, len(y)={len(y)}")

    if n < min_periods:
        return 0.0, f"Short series: {n} observations is fewer than min_periods={min_periods}"

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    s_xx = sum((val - mean_x) ** 2 for val in x)
    s_yy = sum((val - mean_y) ** 2 for val in y)
    s_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))

    # Constant series edge case: zero variance
    if s_xx <= 1e-12 or s_yy <= 1e-12:
        return 0.0, "Constant series: zero variance detected in at least one series"

    r = s_xy / math.sqrt(s_xx * s_yy)

    # Numerical safety clamp to [-1.0, 1.0]
    r = max(-1.0, min(1.0, r))
    return round(r, 6), None


def align_pairwise_series(
    series_a: Mapping[date, float],
    series_b: Mapping[date, float],
    policy: MissingPeriodPolicy = MissingPeriodPolicy.DROP_COMMON,
) -> tuple[list[float], list[float]]:
    """Align two date-keyed time series according to the missing-period policy."""
    if policy == MissingPeriodPolicy.DROP_COMMON:
        common_dates = sorted(set(series_a.keys()) & set(series_b.keys()))
        return [series_a[d] for d in common_dates], [series_b[d] for d in common_dates]

    elif policy == MissingPeriodPolicy.FILL_ZERO:
        all_dates = sorted(set(series_a.keys()) | set(series_b.keys()))
        return [series_a.get(d, 0.0) for d in all_dates], [series_b.get(d, 0.0) for d in all_dates]

    elif policy == MissingPeriodPolicy.FORWARD_FILL:
        all_dates = sorted(set(series_a.keys()) | set(series_b.keys()))
        out_a: list[float] = []
        out_b: list[float] = []

        last_a = 0.0
        last_b = 0.0

        for d in all_dates:
            if d in series_a:
                last_a = series_a[d]
            if d in series_b:
                last_b = series_b[d]
            out_a.append(last_a)
            out_b.append(last_b)

        return out_a, out_b

    else:
        raise ValueError(f"Unsupported MissingPeriodPolicy: {policy}")


def compute_correlation_matrix(
    series_map: Mapping[str, Mapping[date, float] | Sequence[float]],
    policy: MissingPeriodPolicy = MissingPeriodPolicy.DROP_COMMON,
    min_periods: int = 2,
) -> CorrelationMatrix:
    """Compute pairwise Pearson correlation matrix across strategies."""
    labels = list(series_map.keys())
    n = len(labels)

    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    sample_counts: list[list[int]] = [[0] * n for _ in range(n)]
    warnings: list[str] = []

    for i in range(n):
        for j in range(i, n):
            label_i = labels[i]
            label_j = labels[j]

            raw_i = series_map[label_i]
            raw_j = series_map[label_j]

            if i == j:
                # Diagonal: self-correlation is always strictly 1.0
                matrix[i][j] = 1.0
                count = len(raw_i)
                sample_counts[i][j] = count
                continue

            # Align inputs
            if isinstance(raw_i, dict) and isinstance(raw_j, dict):
                vec_i, vec_j = align_pairwise_series(raw_i, raw_j, policy=policy)
            elif isinstance(raw_i, list) and isinstance(raw_j, list):
                min_len = min(len(raw_i), len(raw_j))
                vec_i = raw_i[:min_len]
                vec_j = raw_j[:min_len]
            else:
                # Mixed types
                warnings.append(f"Mismatched series formats between '{label_i}' and '{label_j}'")
                vec_i, vec_j = [], []

            count = len(vec_i)
            sample_counts[i][j] = count
            sample_counts[j][i] = count

            coeff, warn = compute_series_correlation(vec_i, vec_j, min_periods=min_periods)
            if warn:
                warnings.append(f"Pair ({label_i}, {label_j}): {warn}")

            matrix[i][j] = coeff
            matrix[j][i] = coeff  # Symmetry

    return CorrelationMatrix(
        labels=labels,
        matrix=matrix,
        sample_counts=sample_counts,
        policy=policy,
        warnings=warnings,
    )


def compute_signal_correlation_matrix(
    signals_map: Mapping[str, Mapping[date, float]],
    policy: MissingPeriodPolicy = MissingPeriodPolicy.FILL_ZERO,
    min_periods: int = 2,
) -> CorrelationMatrix:
    """Compute pairwise correlation across discrete trading signal vectors (e.g. +1, 0, -1)."""
    return compute_correlation_matrix(
        series_map=signals_map,
        policy=policy,
        min_periods=min_periods,
    )
