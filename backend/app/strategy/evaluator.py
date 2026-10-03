"""Dual-Price Reference Strategy Evaluator (Spot + Option Premium)."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.screener.indicators import (
    calculate_atr,
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
from app.strategy.models import Part2Entry, Part3Stoploss, Part4Exit


class StrategyEvaluator:
    """Evaluates 4-part modular strategy entry and exit conditions."""

    @staticmethod
    def evaluate_entry(
        entry_rules: Part2Entry,
        spot_df: pd.DataFrame,
        option_df: pd.DataFrame | None = None,
    ) -> bool:
        """Evaluate Part 2 entry conditions across Spot and Option Premium."""
        if spot_df is None or len(spot_df) < 2:
            return False

        if not entry_rules.conditions:
            return True

        results: list[bool] = []

        for cond in entry_rules.conditions:
            pref = cond.price_reference
            target_df = option_df if pref == "OPTION_PREMIUM" else spot_df

            if target_df is None or len(target_df) < 2:
                results.append(False)
                continue

            cond_met = StrategyEvaluator._evaluate_single_condition(cond, target_df)
            results.append(cond_met)

        if entry_rules.logic.upper() == "OR":
            return any(results)
        return all(results)

    @staticmethod
    def _evaluate_single_condition(cond: Any, df: pd.DataFrame) -> bool:
        """Evaluate one technical condition on the target DataFrame."""
        if cond.pattern:
            return bool(check_candlestick_pattern(df, str(cond.pattern)))

        if cond.indicator:
            ind_name = str(cond.indicator).upper()
            ind_val: float | None = None

            if ind_name == "RSI":
                s = calculate_rsi(df["close"], period=cond.period or 14)
                ind_val = float(s.iloc[-1])
            elif ind_name == "EMA":
                s = calculate_ema(df["close"], period=cond.period or 20)
                ind_val = float(s.iloc[-1])
            elif ind_name == "SMA":
                s = calculate_sma(df["close"], period=cond.period or 20)
                ind_val = float(s.iloc[-1])
            elif ind_name == "MACD":
                macd_line, _, _ = calculate_macd(
                    df["close"],
                    fast=cond.fast or 12,
                    slow=cond.slow or 26,
                    signal=cond.signal or 9,
                )
                ind_val = float(macd_line.iloc[-1])
            elif ind_name == "BB":
                _, _, lower = calculate_bollinger_bands(
                    df["close"],
                    period=cond.period or 20,
                    std_dev=cond.std_dev or 2.0,
                )
                ind_val = float(lower.iloc[-1])
            elif ind_name == "VWAP":
                s = calculate_vwap(df)
                ind_val = float(s.iloc[-1])
            elif ind_name == "VOLUME_RATIO":
                s = calculate_volume_ratio(df["volume"], avg_period=cond.avg_period or 20)
                ind_val = float(s.iloc[-1])
            elif ind_name == "ATR":
                s = calculate_atr(df, period=cond.period or 14)
                ind_val = float(s.iloc[-1])
            elif ind_name == "SUPERTREND":
                st_line, _ = calculate_supertrend(
                    df,
                    period=cond.period or 10,
                    multiplier=cond.multiplier or 3.0,
                )
                ind_val = float(st_line.iloc[-1])

            if ind_val is None:
                return False

            last_close = float(df["close"].iloc[-1])
            op = cond.operator or ">"
            val = cond.value

            if op == "close_above":
                return bool(last_close > ind_val)
            elif op == "close_below":
                return bool(last_close < ind_val)
            elif op == ">" and isinstance(val, (int, float)):
                return bool(ind_val > float(val))
            elif op == "<" and isinstance(val, (int, float)):
                return bool(ind_val < float(val))
            elif op == ">=" and isinstance(val, (int, float)):
                return bool(ind_val >= float(val))
            elif op == "<=" and isinstance(val, (int, float)):
                return bool(ind_val <= float(val))
            elif op == "=" and isinstance(val, (int, float)):
                return bool(math.isclose(ind_val, float(val), rel_tol=1e-3))

        return True

    @staticmethod
    def calculate_exit_levels(
        entry_price: float,
        direction: str,
        stoploss: Part3Stoploss,
        exit_rules: Part4Exit,
        candle_low: float | None = None,
        candle_high: float | None = None,
    ) -> dict[str, Any]:
        """Calculate Stop-Loss and multi-stage Target prices."""
        is_long = direction.upper() == "LONG"

        # Calculate Stop-loss
        sl_price = entry_price
        if stoploss.sl_type == "PERCENTAGE" and stoploss.percentage_val:
            pct = stoploss.percentage_val / 100.0
            sl_price = entry_price * (1.0 - pct) if is_long else entry_price * (1.0 + pct)
        elif stoploss.sl_type == "POINTS" and stoploss.points_val:
            pts = stoploss.points_val
            sl_price = (entry_price - pts) if is_long else (entry_price + pts)
        elif stoploss.sl_type == "CANDLE_LOW" and candle_low is not None:
            buf = (stoploss.buffer_percentage or 0.0) / 100.0
            sl_price = candle_low * (1.0 - buf)
        elif stoploss.sl_type == "CANDLE_HIGH" and candle_high is not None:
            buf = (stoploss.buffer_percentage or 0.0) / 100.0
            sl_price = candle_high * (1.0 + buf)

        risk = abs(entry_price - sl_price)

        # Calculate Targets
        targets_output: list[dict[str, Any]] = []
        for t in exit_rules.targets:
            t_price = entry_price
            if t.reward_risk_ratio is not None and risk > 0:
                t_price = (
                    entry_price + (risk * t.reward_risk_ratio)
                    if is_long
                    else entry_price - (risk * t.reward_risk_ratio)
                )
            elif t.percentage_gain is not None:
                pct = t.percentage_gain / 100.0
                t_price = entry_price * (1.0 + pct) if is_long else entry_price * (1.0 - pct)
            elif t.points_gain is not None:
                pts = t.points_gain
                t_price = (entry_price + pts) if is_long else (entry_price - pts)

            targets_output.append(
                {
                    "target_number": t.target_number,
                    "target_price": round(t_price, 4),
                    "exit_lots_percentage": t.exit_lots_percentage,
                }
            )

        return {
            "entry_price": round(entry_price, 4),
            "stop_loss_price": round(sl_price, 4),
            "risk_per_unit": round(risk, 4),
            "targets": targets_output,
            "trailing_sl": exit_rules.trailing_sl.model_dump(),
        }
