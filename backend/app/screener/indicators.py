"""Technical indicator calculators and candlestick pattern evaluators for screening."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_rsi(
    series: pd.Series[float] | np.ndarray[Any, Any], period: int = 14
) -> pd.Series[float]:
    """Calculate Relative Strength Index (RSI)."""
    s = pd.Series(series, dtype=float)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_ema(
    series: pd.Series[float] | np.ndarray[Any, Any], period: int = 20
) -> pd.Series[float]:
    """Calculate Exponential Moving Average (EMA)."""
    s = pd.Series(series, dtype=float)
    return s.ewm(span=period, adjust=False).mean()


def calculate_sma(
    series: pd.Series[float] | np.ndarray[Any, Any], period: int = 20
) -> pd.Series[float]:
    """Calculate Simple Moving Average (SMA)."""
    s = pd.Series(series, dtype=float)
    return s.rolling(window=period, min_periods=1).mean()


def calculate_macd(
    close: pd.Series[float] | np.ndarray[Any, Any],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series[float], pd.Series[float], pd.Series[float]]:
    """Calculate MACD line, signal line, and histogram."""
    s = pd.Series(close, dtype=float)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calculate_bollinger_bands(
    close: pd.Series[float] | np.ndarray[Any, Any],
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series[float], pd.Series[float], pd.Series[float]]:
    """Calculate Bollinger Bands (middle, upper, lower)."""
    s = pd.Series(close, dtype=float)
    middle = s.rolling(window=period, min_periods=1).mean()
    std = s.rolling(window=period, min_periods=1).std().fillna(0.0)
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return middle, upper, lower


def calculate_vwap(df: pd.DataFrame) -> pd.Series[float]:
    """Calculate Volume Weighted Average Price (VWAP)."""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_tp_vol = (typical_price * df["volume"]).cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan).fillna(1.0)


def calculate_volume_ratio(
    volume: pd.Series[float] | pd.Series[int], avg_period: int = 20
) -> pd.Series[float]:
    """Calculate current volume / average volume ratio."""
    v = pd.Series(volume, dtype=float)
    avg_v = v.rolling(window=avg_period, min_periods=1).mean()
    return v / avg_v.replace(0, np.nan).fillna(1.0)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series[float]:
    """Calculate Average True Range (ATR)."""
    high = df["high"]
    low = df["low"]
    close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=1).mean()


def calculate_supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series[float], pd.Series[bool]]:
    """Calculate Supertrend line and bullish state (True = Bullish, False = Bearish)."""
    atr = calculate_atr(df, period=period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upper_basic = hl2 + (multiplier * atr)
    lower_basic = hl2 - (multiplier * atr)

    n = len(df)
    upper_band = upper_basic.copy()
    lower_band = lower_basic.copy()
    trend = pd.Series(True, index=df.index)

    close = df["close"].values
    for i in range(1, n):
        if close[i - 1] > lower_band.iloc[i - 1]:
            lower_band.iloc[i] = max(lower_basic.iloc[i], lower_band.iloc[i - 1])
        else:
            lower_band.iloc[i] = lower_basic.iloc[i]

        if close[i - 1] < upper_band.iloc[i - 1]:
            upper_band.iloc[i] = min(upper_basic.iloc[i], upper_band.iloc[i - 1])
        else:
            upper_band.iloc[i] = upper_basic.iloc[i]

        if close[i] > upper_band.iloc[i - 1]:
            trend.iloc[i] = True
        elif close[i] < lower_band.iloc[i - 1]:
            trend.iloc[i] = False
        else:
            trend.iloc[i] = trend.iloc[i - 1]

    st_line = pd.Series(np.where(trend, lower_band, upper_band), index=df.index)
    return st_line, trend


def check_candlestick_pattern(df: pd.DataFrame, pattern_code: str) -> bool:
    """Evaluate candlestick pattern on the most recent bar(s)."""
    if df.empty:
        return False

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None

    code = pattern_code.upper()
    if code == "OPEN_EQ_HIGH":
        # Open equals High (tolerance 0.05%)
        return bool(abs(last["open"] - last["high"]) <= (last["open"] * 0.0005))

    if code == "OPEN_EQ_LOW":
        # Open equals Low (tolerance 0.05%)
        return bool(abs(last["open"] - last["low"]) <= (last["open"] * 0.0005))

    if code == "INSIDE_BAR" and prev is not None:
        return bool(last["high"] < prev["high"] and last["low"] > prev["low"])

    if code == "BULLISH_ENGULFING" and prev is not None:
        prev_bearish = prev["close"] < prev["open"]
        curr_bullish = last["close"] > last["open"]
        engulfs = (last["open"] <= prev["close"]) and (last["close"] >= prev["open"])
        return bool(prev_bearish and curr_bullish and engulfs)

    if code == "BEARISH_ENGULFING" and prev is not None:
        prev_bullish = prev["close"] > prev["open"]
        curr_bearish = last["close"] < last["open"]
        engulfs = (last["open"] >= prev["close"]) and (last["close"] <= prev["open"])
        return bool(prev_bullish and curr_bearish and engulfs)

    return False
