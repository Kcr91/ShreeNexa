"""Incremental streaming implementations for all 12 indicator primitives with G1 parity."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

from app.indicators.incremental import (
    IncrementalIndicator,
    extract_bar_field,
    register_incremental,
)
from app.warehouse.schema import BarRecord


@register_incremental("sma")
class IncrementalSMA(IncrementalIndicator):
    """Incremental Simple Moving Average."""

    def __init__(self, period: int = 14, column: str = "close") -> None:
        self.period = max(1, period)
        self.column = column
        self.window: deque[float] = deque(maxlen=self.period)
        self._sum: float = 0.0

    @property
    def name(self) -> str:
        return "sma"

    @property
    def is_ready(self) -> bool:
        return len(self.window) == self.period

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        val = extract_bar_field(bar, self.column)
        if len(self.window) == self.period:
            self._sum -= self.window[0]

        self.window.append(val)
        self._sum += val

        if not self.is_ready:
            return None
        return round(self._sum / self.period, 6)

    def reset(self) -> None:
        self.window.clear()
        self._sum = 0.0

    @property
    def state(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "column": self.column,
            "window": list(self.window),
            "sum": self._sum,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.column = state["column"]
        self.window = deque(state["window"], maxlen=self.period)
        self._sum = state["sum"]


@register_incremental("ema")
class IncrementalEMA(IncrementalIndicator):
    """Incremental Exponential Moving Average."""

    def __init__(self, period: int = 14, column: str = "close") -> None:
        self.period = max(1, period)
        self.column = column
        self.alpha = 2.0 / (self.period + 1.0)
        self.window: list[float] = []
        self._ema: float | None = None

    @property
    def name(self) -> str:
        return "ema"

    @property
    def is_ready(self) -> bool:
        return self._ema is not None

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        val = extract_bar_field(bar, self.column)
        if self._ema is None:
            self.window.append(val)
            if len(self.window) == self.period:
                self._ema = round(sum(self.window) / self.period, 6)
                return self._ema
            return None
        else:
            self._ema = round(val * self.alpha + self._ema * (1.0 - self.alpha), 6)
            return self._ema

    def reset(self) -> None:
        self.window.clear()
        self._ema = None

    @property
    def state(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "column": self.column,
            "window": list(self.window),
            "ema": self._ema,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.column = state["column"]
        self.alpha = 2.0 / (self.period + 1.0)
        self.window = list(state["window"])
        self._ema = state["ema"]


@register_incremental("macd")
class IncrementalMACD(IncrementalIndicator):
    """Incremental Moving Average Convergence Divergence."""

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = "close",
    ) -> None:
        self.fast_ema = IncrementalEMA(period=fast_period, column=column)
        self.slow_ema = IncrementalEMA(period=slow_period, column=column)
        self.signal_ema = IncrementalEMA(period=signal_period, column="macd")
        self.column = column

    @property
    def name(self) -> str:
        return "macd"

    @property
    def is_ready(self) -> bool:
        return self.signal_ema.is_ready

    def update(self, bar: BarRecord | dict[str, Any]) -> dict[str, float | None] | None:
        f_val = self.fast_ema.update(bar)
        s_val = self.slow_ema.update(bar)

        if f_val is not None and s_val is not None:
            macd_val = round(f_val - s_val, 6)
            sig_val = self.signal_ema.update({"macd": macd_val})
            hist_val = round(macd_val - sig_val, 6) if sig_val is not None else None
            return {"macd": macd_val, "signal": sig_val, "hist": hist_val}
        return None

    def reset(self) -> None:
        self.fast_ema.reset()
        self.slow_ema.reset()
        self.signal_ema.reset()

    @property
    def state(self) -> dict[str, Any]:
        return {
            "fast": self.fast_ema.state,
            "slow": self.slow_ema.state,
            "signal": self.signal_ema.state,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.fast_ema.restore_state(state["fast"])
        self.slow_ema.restore_state(state["slow"])
        self.signal_ema.restore_state(state["signal"])


@register_incremental("supertrend")
class IncrementalSupertrend(IncrementalIndicator):
    """Incremental Supertrend Volatility Trailing Indicator."""

    def __init__(self, period: int = 10, multiplier: float = 3.0) -> None:
        self.period = period
        self.multiplier = multiplier
        self.prev_close: float | None = None
        self.tr_window: list[float] = []
        self.atr: float | None = None
        self.prev_upper: float | None = None
        self.prev_lower: float | None = None
        self.direction: float = 1.0
        self.supertrend: float | None = None

    @property
    def name(self) -> str:
        return "supertrend"

    @property
    def is_ready(self) -> bool:
        return self.supertrend is not None

    def update(self, bar: BarRecord | dict[str, Any]) -> dict[str, float | None] | None:
        high = extract_bar_field(bar, "high")
        low = extract_bar_field(bar, "low")
        close = extract_bar_field(bar, "close")

        if self.prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        self.prev_close = close

        if self.atr is None:
            self.tr_window.append(tr)
            if len(self.tr_window) == self.period:
                self.atr = sum(self.tr_window) / self.period
                hl2 = (high + low) / 2.0
                self.prev_upper = hl2 + self.multiplier * self.atr
                self.prev_lower = hl2 - self.multiplier * self.atr
                self.supertrend = self.prev_upper
                self.direction = 1.0
                return {"supertrend": self.supertrend, "direction": self.direction}
            return None

        self.atr = (self.atr * (self.period - 1) + tr) / self.period
        hl2 = (high + low) / 2.0
        curr_upper = hl2 + self.multiplier * self.atr
        curr_lower = hl2 - self.multiplier * self.atr

        if self.prev_lower is not None:
            cond_l = curr_lower > self.prev_lower or (
                self.prev_close is not None and self.prev_close < self.prev_lower
            )
            if not cond_l:
                curr_lower = self.prev_lower

        if self.prev_upper is not None:
            cond_u = curr_upper < self.prev_upper or (
                self.prev_close is not None and self.prev_close > self.prev_upper
            )
            if not cond_u:
                curr_upper = self.prev_upper

        if self.direction == 1.0:
            if close < curr_lower:
                self.direction = -1.0
                self.supertrend = round(curr_upper, 6)
            else:
                self.direction = 1.0
                self.supertrend = round(curr_lower, 6)
        else:
            if close > curr_upper:
                self.direction = 1.0
                self.supertrend = round(curr_lower, 6)
            else:
                self.direction = -1.0
                self.supertrend = round(curr_upper, 6)

        self.prev_upper = curr_upper
        self.prev_lower = curr_lower
        return {"supertrend": self.supertrend, "direction": self.direction}

    def reset(self) -> None:
        self.prev_close = None
        self.tr_window.clear()
        self.atr = None
        self.prev_upper = None
        self.prev_lower = None
        self.direction = 1.0
        self.supertrend = None

    @property
    def state(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "multiplier": self.multiplier,
            "prev_close": self.prev_close,
            "tr_window": list(self.tr_window),
            "atr": self.atr,
            "prev_upper": self.prev_upper,
            "prev_lower": self.prev_lower,
            "direction": self.direction,
            "supertrend": self.supertrend,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.multiplier = state["multiplier"]
        self.prev_close = state["prev_close"]
        self.tr_window = list(state["tr_window"])
        self.atr = state["atr"]
        self.prev_upper = state["prev_upper"]
        self.prev_lower = state["prev_lower"]
        self.direction = state["direction"]
        self.supertrend = state["supertrend"]


@register_incremental("rsi")
class IncrementalRSI(IncrementalIndicator):
    """Incremental Relative Strength Index."""

    def __init__(self, period: int = 14, column: str = "close") -> None:
        self.period = period
        self.column = column
        self.prev_val: float | None = None
        self.gains: list[float] = []
        self.losses: list[float] = []
        self.avg_gain: float | None = None
        self.avg_loss: float | None = None

    @property
    def name(self) -> str:
        return "rsi"

    @property
    def is_ready(self) -> bool:
        return self.avg_gain is not None and self.avg_loss is not None

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        val = extract_bar_field(bar, self.column)
        if self.prev_val is None:
            self.prev_val = val
            return None

        diff = val - self.prev_val
        self.prev_val = val
        gain = max(0.0, diff)
        loss = max(0.0, -diff)

        if self.avg_gain is None or self.avg_loss is None:
            self.gains.append(gain)
            self.losses.append(loss)
            if len(self.gains) == self.period:
                self.avg_gain = sum(self.gains) / self.period
                self.avg_loss = sum(self.losses) / self.period
                if self.avg_loss == 0.0:
                    return 100.0
                rs = self.avg_gain / self.avg_loss
                return round(100.0 - (100.0 / (1.0 + rs)), 4)
            return None

        self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
        self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period

        if self.avg_loss == 0.0:
            return 100.0
        rs = self.avg_gain / self.avg_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 4)

    def reset(self) -> None:
        self.prev_val = None
        self.gains.clear()
        self.losses.clear()
        self.avg_gain = None
        self.avg_loss = None

    @property
    def state(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "column": self.column,
            "prev_val": self.prev_val,
            "gains": list(self.gains),
            "losses": list(self.losses),
            "avg_gain": self.avg_gain,
            "avg_loss": self.avg_loss,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.column = state["column"]
        self.prev_val = state["prev_val"]
        self.gains = list(state["gains"])
        self.losses = list(state["losses"])
        self.avg_gain = state["avg_gain"]
        self.avg_loss = state["avg_loss"]


@register_incremental("stoch")
class IncrementalStochastic(IncrementalIndicator):
    """Incremental Stochastic Oscillator (%K, %D)."""

    def __init__(self, k_period: int = 14, d_period: int = 3) -> None:
        self.k_period = k_period
        self.d_period = d_period
        self.highs: deque[float] = deque(maxlen=self.k_period)
        self.lows: deque[float] = deque(maxlen=self.k_period)
        self.k_window: deque[float] = deque(maxlen=self.d_period)

    @property
    def name(self) -> str:
        return "stoch"

    @property
    def is_ready(self) -> bool:
        return len(self.k_window) == self.d_period

    def update(self, bar: BarRecord | dict[str, Any]) -> dict[str, float | None] | None:
        high = extract_bar_field(bar, "high")
        low = extract_bar_field(bar, "low")
        close = extract_bar_field(bar, "close")

        self.highs.append(high)
        self.lows.append(low)

        if len(self.highs) < self.k_period:
            return None

        hh = max(self.highs)
        ll = min(self.lows)
        denom = hh - ll
        k_val = round(((close - ll) / denom) * 100.0, 4) if denom > 0 else 50.0
        self.k_window.append(k_val)

        d_val = (
            round(sum(self.k_window) / self.d_period, 4)
            if len(self.k_window) == self.d_period
            else None
        )
        return {"k": k_val, "d": d_val}

    def reset(self) -> None:
        self.highs.clear()
        self.lows.clear()
        self.k_window.clear()

    @property
    def state(self) -> dict[str, Any]:
        return {
            "k_period": self.k_period,
            "d_period": self.d_period,
            "highs": list(self.highs),
            "lows": list(self.lows),
            "k_window": list(self.k_window),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.k_period = state["k_period"]
        self.d_period = state["d_period"]
        self.highs = deque(state["highs"], maxlen=self.k_period)
        self.lows = deque(state["lows"], maxlen=self.k_period)
        self.k_window = deque(state["k_window"], maxlen=self.d_period)


@register_incremental("roc")
class IncrementalROC(IncrementalIndicator):
    """Incremental Rate of Change."""

    def __init__(self, period: int = 10, column: str = "close") -> None:
        self.period = period
        self.column = column
        self.window: deque[float] = deque(maxlen=self.period + 1)

    @property
    def name(self) -> str:
        return "roc"

    @property
    def is_ready(self) -> bool:
        return len(self.window) == self.period + 1

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        val = extract_bar_field(bar, self.column)
        self.window.append(val)
        if not self.is_ready:
            return None
        prev = self.window[0]
        if prev == 0.0:
            return 0.0
        return round(((val - prev) / prev) * 100.0, 4)

    def reset(self) -> None:
        self.window.clear()

    @property
    def state(self) -> dict[str, Any]:
        return {"period": self.period, "column": self.column, "window": list(self.window)}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.column = state["column"]
        self.window = deque(state["window"], maxlen=self.period + 1)


@register_incremental("atr")
class IncrementalATR(IncrementalIndicator):
    """Incremental Average True Range."""

    def __init__(self, period: int = 14) -> None:
        self.period = period
        self.prev_close: float | None = None
        self.tr_window: list[float] = []
        self.atr: float | None = None

    @property
    def name(self) -> str:
        return "atr"

    @property
    def is_ready(self) -> bool:
        return self.atr is not None

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        high = extract_bar_field(bar, "high")
        low = extract_bar_field(bar, "low")
        close = extract_bar_field(bar, "close")

        if self.prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        self.prev_close = close

        if self.atr is None:
            self.tr_window.append(tr)
            if len(self.tr_window) == self.period:
                self.atr = round(sum(self.tr_window) / self.period, 4)
                return self.atr
            return None

        self.atr = round((self.atr * (self.period - 1) + tr) / self.period, 4)
        return self.atr

    def reset(self) -> None:
        self.prev_close = None
        self.tr_window.clear()
        self.atr = None

    @property
    def state(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "prev_close": self.prev_close,
            "tr_window": list(self.tr_window),
            "atr": self.atr,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.prev_close = state["prev_close"]
        self.tr_window = list(state["tr_window"])
        self.atr = state["atr"]


@register_incremental("bollinger_bands")
class IncrementalBollingerBands(IncrementalIndicator):
    """Incremental Bollinger Bands."""

    def __init__(self, period: int = 20, std_dev: float = 2.0, column: str = "close") -> None:
        self.period = period
        self.std_dev = std_dev
        self.column = column
        self.window: deque[float] = deque(maxlen=self.period)

    @property
    def name(self) -> str:
        return "bollinger_bands"

    @property
    def is_ready(self) -> bool:
        return len(self.window) == self.period

    def update(self, bar: BarRecord | dict[str, Any]) -> dict[str, float | None] | None:
        val = extract_bar_field(bar, self.column)
        self.window.append(val)
        if not self.is_ready:
            return None

        mid = round(sum(self.window) / self.period, 4)
        variance = sum((x - mid) ** 2 for x in self.window) / self.period
        std = math.sqrt(variance)

        u = round(mid + self.std_dev * std, 4)
        low = round(mid - self.std_dev * std, 4)
        band_width = u - low
        pct_b = round((val - low) / band_width, 4) if band_width > 0 else 0.0
        bw = round((band_width / mid) * 100.0, 4) if mid > 0 else 0.0

        return {
            "upper": u,
            "middle": mid,
            "lower": low,
            "pct_b": pct_b,
            "bandwidth": bw,
        }

    def reset(self) -> None:
        self.window.clear()

    @property
    def state(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "std_dev": self.std_dev,
            "column": self.column,
            "window": list(self.window),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.std_dev = state["std_dev"]
        self.column = state["column"]
        self.window = deque(state["window"], maxlen=self.period)


@register_incremental("obv")
class IncrementalOBV(IncrementalIndicator):
    """Incremental On-Balance Volume."""

    def __init__(self) -> None:
        self.prev_close: float | None = None
        self.obv: float = 0.0

    @property
    def name(self) -> str:
        return "obv"

    @property
    def is_ready(self) -> bool:
        return self.prev_close is not None

    def update(self, bar: BarRecord | dict[str, Any]) -> float:
        close = extract_bar_field(bar, "close")
        volume = extract_bar_field(bar, "volume")

        if self.prev_close is None:
            self.obv = volume
        elif close > self.prev_close:
            self.obv += volume
        elif close < self.prev_close:
            self.obv -= volume

        self.prev_close = close
        return self.obv

    def reset(self) -> None:
        self.prev_close = None
        self.obv = 0.0

    @property
    def state(self) -> dict[str, Any]:
        return {"prev_close": self.prev_close, "obv": self.obv}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.prev_close = state["prev_close"]
        self.obv = state["obv"]


@register_incremental("vwap")
class IncrementalVWAP(IncrementalIndicator):
    """Incremental Volume Weighted Average Price."""

    def __init__(self) -> None:
        self.cum_pv: float = 0.0
        self.cum_vol: float = 0.0

    @property
    def name(self) -> str:
        return "vwap"

    @property
    def is_ready(self) -> bool:
        return self.cum_vol > 0

    def update(self, bar: BarRecord | dict[str, Any]) -> float:
        high = extract_bar_field(bar, "high")
        low = extract_bar_field(bar, "low")
        close = extract_bar_field(bar, "close")
        volume = extract_bar_field(bar, "volume")

        typical = (high + low + close) / 3.0
        self.cum_pv += typical * volume
        self.cum_vol += volume

        if self.cum_vol > 0:
            return round(self.cum_pv / self.cum_vol, 4)
        return round(typical, 4)

    def reset(self) -> None:
        self.cum_pv = 0.0
        self.cum_vol = 0.0

    @property
    def state(self) -> dict[str, Any]:
        return {"cum_pv": self.cum_pv, "cum_vol": self.cum_vol}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.cum_pv = state["cum_pv"]
        self.cum_vol = state["cum_vol"]


@register_incremental("zscore")
class IncrementalZScore(IncrementalIndicator):
    """Incremental Z-Score."""

    def __init__(self, period: int = 20, column: str = "close") -> None:
        self.period = period
        self.column = column
        self.window: deque[float] = deque(maxlen=self.period)

    @property
    def name(self) -> str:
        return "zscore"

    @property
    def is_ready(self) -> bool:
        return len(self.window) == self.period

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        val = extract_bar_field(bar, self.column)
        self.window.append(val)
        if not self.is_ready:
            return None

        mean = sum(self.window) / self.period
        variance = sum((x - mean) ** 2 for x in self.window) / self.period
        std = math.sqrt(variance)
        if std > 0:
            return round((val - mean) / std, 4)
        return 0.0

    def reset(self) -> None:
        self.window.clear()

    @property
    def state(self) -> dict[str, Any]:
        return {"period": self.period, "column": self.column, "window": list(self.window)}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.column = state["column"]
        self.window = deque(state["window"], maxlen=self.period)


@register_incremental("rolling_std")
class IncrementalRollingStd(IncrementalIndicator):
    """Incremental Rolling Standard Deviation."""

    def __init__(self, period: int = 20, column: str = "close") -> None:
        self.period = period
        self.column = column
        self.window: deque[float] = deque(maxlen=self.period)

    @property
    def name(self) -> str:
        return "rolling_std"

    @property
    def is_ready(self) -> bool:
        return len(self.window) == self.period

    def update(self, bar: BarRecord | dict[str, Any]) -> float | None:
        val = extract_bar_field(bar, self.column)
        self.window.append(val)
        if not self.is_ready:
            return None

        mean = sum(self.window) / self.period
        variance = sum((x - mean) ** 2 for x in self.window) / self.period
        return round(math.sqrt(variance), 4)

    def reset(self) -> None:
        self.window.clear()

    @property
    def state(self) -> dict[str, Any]:
        return {"period": self.period, "column": self.column, "window": list(self.window)}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.period = state["period"]
        self.column = state["column"]
        self.window = deque(state["window"], maxlen=self.period)
