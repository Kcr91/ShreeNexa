"""Volume indicator primitives: OBV and VWAP."""

from __future__ import annotations

from typing import Any

import pyarrow as pa

from app.indicators.registry import (
    IndicatorFamily,
    VectorIndicator,
    extract_series,
)


class OBVIndicator(VectorIndicator):
    """On-Balance Volume."""

    @property
    def name(self) -> str:
        return "obv"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.VOLUME

    @property
    def description(self) -> str:
        return "On-Balance Volume measuring cumulative volume flow."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        return 1

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        close = extract_series(data, "close")
        volume = extract_series(data, "volume")
        n = len(close)

        obv: list[float | None] = [0.0] * n
        if n == 0:
            return obv

        obv[0] = volume[0]
        for i in range(1, n):
            prev = obv[i - 1] or 0.0
            if close[i] > close[i - 1]:
                obv[i] = prev + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = prev - volume[i]
            else:
                obv[i] = prev
        return obv


class VWAPIndicator(VectorIndicator):
    """Volume Weighted Average Price."""

    @property
    def name(self) -> str:
        return "vwap"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.VOLUME

    @property
    def description(self) -> str:
        return "Volume Weighted Average Price over typical price."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        return 1

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None]:
        high = extract_series(data, "high")
        low = extract_series(data, "low")
        close = extract_series(data, "close")
        volume = extract_series(data, "volume")
        n = len(close)

        vwap: list[float | None] = [None] * n
        if n == 0:
            return vwap

        cum_pv = 0.0
        cum_vol = 0.0

        for i in range(n):
            typical_price = (high[i] + low[i] + close[i]) / 3.0
            cum_pv += typical_price * volume[i]
            cum_vol += volume[i]

            if cum_vol > 0:
                vwap[i] = round(cum_pv / cum_vol, 4)
            else:
                vwap[i] = round(typical_price, 4)
        return vwap
