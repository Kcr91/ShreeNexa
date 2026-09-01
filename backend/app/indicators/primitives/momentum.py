"""Momentum indicator primitives: RSI, Stochastic, and ROC."""

from __future__ import annotations

from typing import Any

import pyarrow as pa

from app.indicators.primitives.trend import compute_sma
from app.indicators.registry import (
    IndicatorFamily,
    VectorIndicator,
    extract_series,
)


def compute_rsi(values: list[float], period: int = 14) -> list[float | None]:
    """Compute Relative Strength Index with Wilder's smoothing."""
    n = len(values)
    rsi: list[float | None] = [None] * n
    if n <= period or period <= 0:
        return rsi

    deltas = [values[i] - values[i - 1] for i in range(1, n)]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]

    # Initial average gain and loss (SMA over first `period` changes)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0.0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = round(100.0 - (100.0 / (1.0 + rs)), 4)

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        idx = i + 1

        if avg_loss == 0.0:
            rsi[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[idx] = round(100.0 - (100.0 / (1.0 + rs)), 4)

    return rsi


class RSIIndicator(VectorIndicator):
    """Relative Strength Index."""

    @property
    def name(self) -> str:
        return "rsi"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.MOMENTUM

    @property
    def description(self) -> str:
        return "Relative Strength Index oscillator bounded [0, 100]."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 14, "column": "close"}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 14)) + 1

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        p = params or self.default_params
        period = int(p.get("period", 14))
        col = str(p.get("column", "close"))
        series = extract_series(data, col)
        return compute_rsi(series, period)


class StochasticIndicator(VectorIndicator):
    """Stochastic Oscillator (%K, %D)."""

    @property
    def name(self) -> str:
        return "stoch"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.MOMENTUM

    @property
    def description(self) -> str:
        return "Stochastic Oscillator (%K line and %D smoothed signal)."

    @property
    def output_keys(self) -> list[str]:
        return ["k", "d"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"k_period": 14, "d_period": 3}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        k = int(p.get("k_period", 14))
        d = int(p.get("d_period", 3))
        return k + d - 1

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, list[float | None]]:
        p = params or self.default_params
        k_period = int(p.get("k_period", 14))
        d_period = int(p.get("d_period", 3))

        high = extract_series(data, "high")
        low = extract_series(data, "low")
        close = extract_series(data, "close")
        n = len(close)

        k_line: list[float | None] = [None] * n
        valid_k_vals: list[float] = []
        valid_indices: list[int] = []

        for i in range(k_period - 1, n):
            highest_h = max(high[i - k_period + 1 : i + 1])
            lowest_l = min(low[i - k_period + 1 : i + 1])
            denom = highest_h - lowest_l
            if denom > 0:
                val = round(((close[i] - lowest_l) / denom) * 100.0, 4)
            else:
                val = 50.0
            k_line[i] = val
            valid_k_vals.append(val)
            valid_indices.append(i)

        d_line: list[float | None] = [None] * n
        if len(valid_k_vals) >= d_period:
            d_sma = compute_sma(valid_k_vals, d_period)
            for idx_in_valid, orig_idx in enumerate(valid_indices):
                d_line[orig_idx] = d_sma[idx_in_valid]

        return {"k": k_line, "d": d_line}


class ROCIndicator(VectorIndicator):
    """Rate of Change."""

    @property
    def name(self) -> str:
        return "roc"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.MOMENTUM

    @property
    def description(self) -> str:
        return "Rate of Change percentage over specified lookback."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 10, "column": "close"}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 10)) + 1

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        p = params or self.default_params
        period = int(p.get("period", 10))
        col = str(p.get("column", "close"))
        series = extract_series(data, col)

        n = len(series)
        out: list[float | None] = [None] * n
        if n > period:
            for i in range(period, n):
                prev = series[i - period]
                if prev != 0.0:
                    out[i] = round(((series[i] - prev) / prev) * 100.0, 4)
        return out
