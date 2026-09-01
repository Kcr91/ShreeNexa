"""Volatility indicator primitives: ATR and Bollinger Bands."""

from __future__ import annotations

import math
from typing import Any

import pyarrow as pa

from app.indicators.primitives.trend import compute_sma
from app.indicators.registry import (
    IndicatorFamily,
    VectorIndicator,
    extract_series,
)


def compute_atr(
    high: list[float],
    low: list[float],
    close: list[float],
    period: int = 14,
) -> list[float | None]:
    """Compute Average True Range using Wilder's smoothing."""
    n = len(close)
    atr: list[float | None] = [None] * n
    if n < period or period <= 0:
        return atr

    tr: list[float] = [0.0] * n
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr[period - 1] = round(sum(tr[:period]) / period, 4)
    for i in range(period, n):
        prev = atr[i - 1]
        if prev is not None:
            atr[i] = round((prev * (period - 1) + tr[i]) / period, 4)
    return atr


class ATRIndicator(VectorIndicator):
    """Average True Range."""

    @property
    def name(self) -> str:
        return "atr"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.VOLATILITY

    @property
    def description(self) -> str:
        return "Average True Range volatility indicator."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 14}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 14))

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        p = params or self.default_params
        period = int(p.get("period", 14))

        high = extract_series(data, "high")
        low = extract_series(data, "low")
        close = extract_series(data, "close")
        return compute_atr(high, low, close, period)


class BollingerBandsIndicator(VectorIndicator):
    """Bollinger Bands."""

    @property
    def name(self) -> str:
        return "bollinger_bands"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.VOLATILITY

    @property
    def description(self) -> str:
        return "Bollinger Bands (Upper, Middle, Lower, %B, and Bandwidth)."

    @property
    def output_keys(self) -> list[str]:
        return ["upper", "middle", "lower", "pct_b", "bandwidth"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 20, "std_dev": 2.0, "column": "close"}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 20))

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, list[float | None]]:
        p = params or self.default_params
        period = int(p.get("period", 20))
        num_std = float(p.get("std_dev", 2.0))
        col = str(p.get("column", "close"))

        series = extract_series(data, col)
        n = len(series)

        middle = compute_sma(series, period)
        upper: list[float | None] = [None] * n
        lower: list[float | None] = [None] * n
        pct_b: list[float | None] = [None] * n
        bandwidth: list[float | None] = [None] * n

        for i in range(period - 1, n):
            window = series[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = math.sqrt(variance)
            mid = middle[i]

            if mid is not None:
                u = round(mid + num_std * std, 4)
                low = round(mid - num_std * std, 4)

                upper[i] = u
                lower[i] = low

                band_width = u - low
                if band_width > 0:
                    pct_b[i] = round((series[i] - low) / band_width, 4)
                if mid > 0:
                    bandwidth[i] = round((band_width / mid) * 100.0, 4)

        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "pct_b": pct_b,
            "bandwidth": bandwidth,
        }
