"""Recursive AND / OR condition tree walker for the Dynamic Screener Engine."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.screener.indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_supertrend,
    calculate_volume_ratio,
    calculate_vwap,
    check_candlestick_pattern,
)

logger = logging.getLogger(__name__)


def evaluate_leaf_condition(
    node: dict[str, Any],
    timeframe_dfs: dict[str, pd.DataFrame],
    results_collector: dict[str, Any] | None = None,
    matched_conditions: list[str] | None = None,
) -> bool:
    """Evaluate a single leaf condition against aggregated timeframe DataFrames."""
    indicator_raw = node.get("indicator", "").upper()
    tf = node.get("timeframe", "daily").lower()
    op = node.get("operator", "").lower()
    target_val = node.get("value")

    df = timeframe_dfs.get(tf)
    if df is None or df.empty:
        return False

    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else last_close

    # Candlestick patterns
    if indicator_raw in [
        "OPEN_EQ_HIGH",
        "OPEN_EQ_LOW",
        "INSIDE_BAR",
        "BULLISH_ENGULFING",
        "BEARISH_ENGULFING",
    ]:
        passed = check_candlestick_pattern(df, indicator_raw)
        if passed and matched_conditions is not None:
            matched_conditions.append(f"{indicator_raw} on {tf} ✓")
        return passed

    # 1. RSI
    if indicator_raw == "RSI":
        period = int(node.get("period", 14))
        rsi_series = calculate_rsi(df["close"], period=period)
        val = float(rsi_series.iloc[-1])
        key = f"RSI_{period}_{tf}"
        if results_collector is not None:
            results_collector[key] = round(val, 2)
        passed = _compare_numeric(val, op, target_val)
        if passed and matched_conditions is not None:
            matched_conditions.append(f"{key} ({val:.1f}) {op} {target_val} ✓")
        return passed

    # 2. EMA
    if indicator_raw == "EMA":
        period = int(node.get("period", 20))
        ema_series = calculate_ema(df["close"], period=period)
        val = float(ema_series.iloc[-1])
        prev_ema = float(ema_series.iloc[-2]) if len(ema_series) >= 2 else val
        key = f"EMA_{period}_{tf}"
        if results_collector is not None:
            results_collector[key] = round(val, 2)

        if op == "close_above":
            passed = last_close > val
        elif op == "close_below":
            passed = last_close < val
        elif op == "crosses_above":
            passed = (prev_close <= prev_ema) and (last_close > val)
        elif op == "crosses_below":
            passed = (prev_close >= prev_ema) and (last_close < val)
        else:
            passed = _compare_numeric(val, op, target_val)

        if passed and matched_conditions is not None:
            matched_conditions.append(f"Close ({last_close:.1f}) {op} {key} ({val:.1f}) ✓")
        return passed

    # 3. SMA
    if indicator_raw == "SMA":
        period = int(node.get("period", 20))
        sma_series = calculate_sma(df["close"], period=period)
        val = float(sma_series.iloc[-1])
        prev_sma = float(sma_series.iloc[-2]) if len(sma_series) >= 2 else val
        key = f"SMA_{period}_{tf}"
        if results_collector is not None:
            results_collector[key] = round(val, 2)

        if op == "close_above":
            passed = last_close > val
        elif op == "close_below":
            passed = last_close < val
        elif op == "crosses_above":
            passed = (prev_close <= prev_sma) and (last_close > val)
        elif op == "crosses_below":
            passed = (prev_close >= prev_sma) and (last_close < val)
        else:
            passed = _compare_numeric(val, op, target_val)

        if passed and matched_conditions is not None:
            matched_conditions.append(f"Close ({last_close:.1f}) {op} {key} ({val:.1f}) ✓")
        return passed

    # 4. MACD
    if indicator_raw == "MACD":
        fast = int(node.get("fast", 12))
        slow = int(node.get("slow", 26))
        sig = int(node.get("signal", 9))
        macd_line, sig_line, _ = calculate_macd(df["close"], fast=fast, slow=slow, signal=sig)
        curr_m, curr_s = float(macd_line.iloc[-1]), float(sig_line.iloc[-1])
        prev_m = float(macd_line.iloc[-2]) if len(macd_line) >= 2 else curr_m
        prev_s = float(sig_line.iloc[-2]) if len(sig_line) >= 2 else curr_s

        if results_collector is not None:
            results_collector[f"MACD_{tf}"] = round(curr_m, 2)
            results_collector[f"MACD_Signal_{tf}"] = round(curr_s, 2)

        if op == "crosses_above":
            passed = (prev_m <= prev_s) and (curr_m > curr_s)
        elif op == "crosses_below":
            passed = (prev_m >= prev_s) and (curr_m < curr_s)
        else:
            passed = _compare_numeric(curr_m, op, target_val)

        if passed and matched_conditions is not None:
            matched_conditions.append(f"MACD {op} Signal on {tf} ✓")
        return passed

    # 5. Bollinger Bands
    if indicator_raw in ["BOLLINGER", "BOLLINGER_BANDS"]:
        period = int(node.get("period", 20))
        std_dev = float(node.get("std_dev", 2.0))
        _mid, upper, lower = calculate_bollinger_bands(df["close"], period=period, std_dev=std_dev)
        curr_u, curr_l = float(upper.iloc[-1]), float(lower.iloc[-1])
        if results_collector is not None:
            results_collector[f"BB_Upper_{tf}"] = round(curr_u, 2)
            results_collector[f"BB_Lower_{tf}"] = round(curr_l, 2)

        if op == "close_above":
            passed = last_close > curr_u
        elif op == "close_below":
            passed = last_close < curr_l
        else:
            passed = True

        if passed and matched_conditions is not None:
            matched_conditions.append(f"BB {op} on {tf} ✓")
        return passed

    # 6. VWAP
    if indicator_raw == "VWAP":
        vwap_series = calculate_vwap(df)
        val = float(vwap_series.iloc[-1])
        if results_collector is not None:
            results_collector[f"VWAP_{tf}"] = round(val, 2)
        if op == "close_above":
            passed = last_close > val
        elif op == "close_below":
            passed = last_close < val
        else:
            passed = _compare_numeric(val, op, target_val)
        if passed and matched_conditions is not None:
            matched_conditions.append(f"Close {op} VWAP ({val:.1f}) on {tf} ✓")
        return passed

    # 7. Volume Ratio
    if indicator_raw == "VOLUME_RATIO":
        avg_p = int(node.get("avg_period", 20))
        vr_series = calculate_volume_ratio(df["volume"], avg_period=avg_p)
        val = float(vr_series.iloc[-1])
        if results_collector is not None:
            results_collector[f"Volume_Ratio_{tf}"] = round(val, 2)
        passed = _compare_numeric(val, op, target_val)
        if passed and matched_conditions is not None:
            matched_conditions.append(f"Volume Ratio ({val:.2f}x) {op} {target_val} ✓")
        return passed

    # 8. Supertrend
    if indicator_raw == "SUPERTREND":
        period = int(node.get("period", 10))
        mult = float(node.get("multiplier", 3.0))
        _, is_bullish = calculate_supertrend(df, period=period, multiplier=mult)
        bullish = bool(is_bullish.iloc[-1])
        if results_collector is not None:
            results_collector[f"Supertrend_{tf}"] = "BULLISH" if bullish else "BEARISH"
        passed = bullish if op == "is_bullish" else (not bullish if op == "is_bearish" else True)
        if passed and matched_conditions is not None:
            matched_conditions.append(f"Supertrend {op} on {tf} ✓")
        return passed

    return False


def _compare_numeric(val: float, op: str, target: Any) -> bool:
    """Evaluate numeric comparison operator."""
    if op == ">":
        return bool(val > float(target))
    if op == "<":
        return bool(val < float(target))
    if op == ">=":
        return bool(val >= float(target))
    if op == "<=":
        return bool(val <= float(target))
    if op == "=":
        return bool(abs(val - float(target)) < 1e-4)
    if op == "between" and isinstance(target, (list, tuple)) and len(target) == 2:
        return bool(float(target[0]) <= val <= float(target[1]))
    return False


def evaluate_condition_tree(
    tree: dict[str, Any],
    timeframe_dfs: dict[str, pd.DataFrame],
    results_collector: dict[str, Any] | None = None,
    matched_conditions: list[str] | None = None,
) -> bool:
    """Recursively walk and evaluate the AND / OR condition tree."""
    if "logic" in tree:
        logic = str(tree["logic"]).upper()
        conditions = tree.get("conditions", [])
        if not conditions:
            return True

        sub_results = [
            evaluate_condition_tree(
                c,
                timeframe_dfs,
                results_collector=results_collector,
                matched_conditions=matched_conditions,
            )
            for c in conditions
        ]

        return all(sub_results) if logic == "AND" else any(sub_results)

    # Leaf node
    return evaluate_leaf_condition(
        tree,
        timeframe_dfs,
        results_collector=results_collector,
        matched_conditions=matched_conditions,
    )
