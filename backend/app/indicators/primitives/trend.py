"""Trend indicator primitives: SMA, EMA, MACD, and Supertrend."""

from __future__ import annotations

from typing import Any

import pyarrow as pa

from app.indicators.registry import (
    IndicatorFamily,
    VectorIndicator,
    extract_series,
)


def compute_sma(values: list[float], period: int) -> list[float | None]:
    """Compute simple moving average with strict None warm-up."""
    n = len(values)
    out: list[float | None] = [None] * n
    if n < period or period <= 0:
        return out

    window_sum = sum(values[:period])
    out[period - 1] = round(window_sum / period, 6)

    for i in range(period, n):
        window_sum += values[i] - values[i - period]
        out[i] = round(window_sum / period, 6)
    return out


def compute_ema(values: list[float], period: int) -> list[float | None]:
    """Compute exponential moving average seeded with SMA at index period-1."""
    n = len(values)
    out: list[float | None] = [None] * n
    if n < period or period <= 0:
        return out

    # Seed with SMA
    seed = sum(values[:period]) / period
    out[period - 1] = round(seed, 6)
    alpha = 2.0 / (period + 1.0)

    for i in range(period, n):
        prev = out[i - 1]
        if prev is not None:
            val = values[i] * alpha + prev * (1.0 - alpha)
            out[i] = round(val, 6)
    return out


class SMAIndicator(VectorIndicator):
    """Simple Moving Average."""

    @property
    def name(self) -> str:
        return "sma"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.TREND

    @property
    def description(self) -> str:
        return "Simple Moving Average over specified rolling period."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 14, "column": "close"}

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
        col = str(p.get("column", "close"))
        series = extract_series(data, col)
        return compute_sma(series, period)


class EMAIndicator(VectorIndicator):
    """Exponential Moving Average."""

    @property
    def name(self) -> str:
        return "ema"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.TREND

    @property
    def description(self) -> str:
        return "Exponential Moving Average with SMA seed."

    @property
    def output_keys(self) -> list[str]:
        return ["value"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 14, "column": "close"}

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
        col = str(p.get("column", "close"))
        series = extract_series(data, col)
        return compute_ema(series, period)


class MACDIndicator(VectorIndicator):
    """Moving Average Convergence Divergence."""

    @property
    def name(self) -> str:
        return "macd"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.TREND

    @property
    def description(self) -> str:
        return "MACD line, Signal line, and Histogram."

    @property
    def output_keys(self) -> list[str]:
        return ["macd", "signal", "hist"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"fast_period": 12, "slow_period": 26, "signal_period": 9, "column": "close"}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        slow = int(p.get("slow_period", 26))
        sig = int(p.get("signal_period", 9))
        return slow + sig - 1

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, list[float | None]]:
        p = params or self.default_params
        fast = int(p.get("fast_period", 12))
        slow = int(p.get("slow_period", 26))
        sig = int(p.get("signal_period", 9))
        col = str(p.get("column", "close"))

        series = extract_series(data, col)
        fast_ema = compute_ema(series, fast)
        slow_ema = compute_ema(series, slow)

        n = len(series)
        macd_line: list[float | None] = [None] * n
        valid_macd_vals: list[float] = []
        valid_indices: list[int] = []

        for i in range(n):
            f_val = fast_ema[i]
            s_val = slow_ema[i]
            if f_val is not None and s_val is not None:
                diff = round(f_val - s_val, 6)
                macd_line[i] = diff
                valid_macd_vals.append(diff)
                valid_indices.append(i)

        # Compute signal line as EMA over valid MACD values
        signal_line: list[float | None] = [None] * n
        hist: list[float | None] = [None] * n

        if len(valid_macd_vals) >= sig:
            sig_ema = compute_ema(valid_macd_vals, sig)
            for idx_in_valid, orig_idx in enumerate(valid_indices):
                s_val = sig_ema[idx_in_valid]
                signal_line[orig_idx] = s_val
                m_val = macd_line[orig_idx]
                if m_val is not None and s_val is not None:
                    hist[orig_idx] = round(m_val - s_val, 6)

        return {"macd": macd_line, "signal": signal_line, "hist": hist}


class SupertrendIndicator(VectorIndicator):
    """Supertrend Volatility-Trailing Indicator."""

    @property
    def name(self) -> str:
        return "supertrend"

    @property
    def family(self) -> IndicatorFamily:
        return IndicatorFamily.TREND

    @property
    def description(self) -> str:
        return "Supertrend trailing stop and trend direction (+1 bullish, -1 bearish)."

    @property
    def output_keys(self) -> list[str]:
        return ["supertrend", "direction"]

    @property
    def default_params(self) -> dict[str, Any]:
        return {"period": 10, "multiplier": 3.0}

    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        p = params or self.default_params
        return int(p.get("period", 10))

    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, list[float | None]]:
        p = params or self.default_params
        period = int(p.get("period", 10))
        multiplier = float(p.get("multiplier", 3.0))

        high = extract_series(data, "high")
        low = extract_series(data, "low")
        close = extract_series(data, "close")
        n = len(close)

        # Compute True Range
        tr: list[float] = [0.0] * n
        if n > 0:
            tr[0] = high[0] - low[0]
            for i in range(1, n):
                tr[i] = max(
                    high[i] - low[i],
                    abs(high[i] - close[i - 1]),
                    abs(low[i] - close[i - 1]),
                )

        # Compute ATR with Wilder's Smoothing
        atr: list[float | None] = [None] * n
        if n >= period:
            atr[period - 1] = sum(tr[:period]) / period
            for i in range(period, n):
                prev_atr = atr[i - 1]
                if prev_atr is not None:
                    atr[i] = (prev_atr * (period - 1) + tr[i]) / period

        upper_band: list[float | None] = [None] * n
        lower_band: list[float | None] = [None] * n
        supertrend: list[float | None] = [None] * n
        direction: list[float | None] = [None] * n

        for i in range(n):
            atr_val = atr[i]
            if atr_val is not None:
                hl2 = (high[i] + low[i]) / 2.0
                upper_band[i] = hl2 + multiplier * atr_val
                lower_band[i] = hl2 - multiplier * atr_val

        if n >= period and upper_band[period - 1] is not None:
            supertrend[period - 1] = upper_band[period - 1]
            direction[period - 1] = 1.0

            for i in range(period, n):
                curr_lower = lower_band[i]
                prev_lower = lower_band[i - 1]
                if curr_lower is not None and prev_lower is not None:
                    if curr_lower > prev_lower or close[i - 1] < prev_lower:
                        pass
                    else:
                        lower_band[i] = prev_lower

                curr_upper = upper_band[i]
                prev_upper = upper_band[i - 1]
                if curr_upper is not None and prev_upper is not None:
                    if curr_upper < prev_upper or close[i - 1] > prev_upper:
                        pass
                    else:
                        upper_band[i] = prev_upper

                # Direction switch logic
                prev_dir = direction[i - 1]
                curr_ub = upper_band[i]
                curr_lb = lower_band[i]

                if prev_dir == 1.0 and curr_lb is not None and curr_ub is not None:
                    if close[i] < curr_lb:
                        direction[i] = -1.0
                        supertrend[i] = round(curr_ub, 6)
                    else:
                        direction[i] = 1.0
                        supertrend[i] = round(curr_lb, 6)
                elif curr_lb is not None and curr_ub is not None:
                    if close[i] > curr_ub:
                        direction[i] = 1.0
                        supertrend[i] = round(curr_lb, 6)
                    else:
                        direction[i] = -1.0
                        supertrend[i] = round(curr_ub, 6)

        return {"supertrend": supertrend, "direction": direction}
