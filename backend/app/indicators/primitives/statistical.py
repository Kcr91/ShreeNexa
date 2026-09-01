"""Statistical indicator primitives: Z-Score and Rolling Standard Deviation."""

from __future__ import annotations

import math
from typing import Any

import pyarrow as pa

from app.indicators.registry import (
    IndicatorFamily,
    VectorIndicator,
    extract_series,
)


class ZScoreIndicator(VectorIndicator):
    """Z-Score standardized distance."""

    @property
    def name(self) -> str:
        return "zscore"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.STATISTICAL

    @property
    def description(self) -> str:
        return "Standardized Z-Score: (price - mean) / std."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 20, "column": "close"}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 20))

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        p = params or self.default_params
        period = int(p.get("period", 20))
        col = str(p.get("column", "close"))

        series = extract_series(data, col)
        n = len(series)
        zscore: list[float | None] = [None] * n

        for i in range(period - 1, n):
            window = series[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = math.sqrt(variance)
            if std > 0:
                zscore[i] = round((series[i] - mean) / std, 4)
            else:
                zscore[i] = 0.0

        return zscore


class RollingStdIndicator(VectorIndicator):
    """Rolling Standard Deviation."""

    @property
    def name(self) -> str:
        return "rolling_std"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.STATISTICAL

    @property
    def description(self) -> str:
        return "Rolling population standard deviation."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 20, "column": "close"}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 20))

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        p = params or self.default_params
        period = int(p.get("period", 20))
        col = str(p.get("column", "close"))

        series = extract_series(data, col)
        n = len(series)
        out: list[float | None] = [None] * n

        for i in range(period - 1, n):
            window = series[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            out[i] = round(math.sqrt(variance), 4)

        return out
