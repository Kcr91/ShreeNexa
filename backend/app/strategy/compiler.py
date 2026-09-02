"""Vectorized StrategyIR compiler and batch execution engine."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

import pyarrow as pa

from app.indicators.formula import FormulaCompiler
from app.indicators.registry import extract_series_nullable, registry
from app.strategy.ir import (
    AndNode,
    CompareOp,
    ConstOperand,
    CrossOverNode,
    CrossUnderNode,
    CustomPythonNode,
    FieldOperand,
    IndicatorCompareNode,
    LevelRef,
    NotNode,
    OperandRef,
    OrNode,
    PctChangeNode,
    PersistNode,
    PriceLevelBreakNode,
    RefOperand,
    RegimeNode,
    SequenceNode,
    SignalNode,
    StrategyIR,
    StrategySignalNode,
    TimeWindowNode,
)
from app.strategy.regime import RegimeDetectorRegistry
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


@dataclass
class StrategyEvaluationResult:
    """Output results of vectorized strategy evaluation across historical bars."""

    entry_signals: dict[str, list[bool]] = field(default_factory=dict)
    exit_signals: dict[str, list[bool]] = field(default_factory=dict)
    indicator_values: dict[str, list[Any]] = field(default_factory=dict)
    timestamps: list[datetime] = field(default_factory=list)
    series_length: int = 0


def _parse_time_str(val: str | None) -> time | None:
    if not val:
        return None
    parts = val.strip().split(":")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def _compare_values(a: Any, op: CompareOp | str, b: Any) -> bool:
    if a is None or b is None:
        return False
    op_str = op.value if isinstance(op, CompareOp) else str(op)
    if op_str in (">", "GT"):
        return bool(a > b)
    elif op_str in ("<", "LT"):
        return bool(a < b)
    elif op_str in (">=", "GTE"):
        return bool(a >= b)
    elif op_str in ("<=", "LTE"):
        return bool(a <= b)
    elif op_str in ("==", "EQ"):
        return bool(a == b)
    elif op_str in ("!=", "NEQ"):
        return bool(a != b)
    return False


KNOWN_PRIMITIVES = {
    "rsi",
    "ema",
    "sma",
    "macd",
    "bollinger_bands",
    "supertrend",
    "atr",
    "stoch",
    "roc",
    "vwap",
    "obv",
    "rolling_std",
    "zscore",
}


class CompiledStrategy:
    """Compiled, ready-to-execute strategy graph for vectorized backtesting and screening."""

    def __init__(self, strategy: StrategyIR) -> None:
        self.strategy = strategy
        self._formula_compiler = FormulaCompiler()

    def evaluate(
        self,
        data: pa.Table | dict[str, Any] | list[BarRecord],
        external_signals: Mapping[tuple[str, str], Sequence[bool]] | None = None,
    ) -> StrategyEvaluationResult:
        """Evaluate strategy over historical market dataset."""
        normalized_data, timestamps, length = self._normalize_dataset(data)
        if length == 0:
            return StrategyEvaluationResult(series_length=0)

        # 1. Compute declared indicators
        ind_values: dict[str, list[Any]] = {}
        for name, ind_def in self.strategy.indicators.items():
            fn_name = ind_def.fn.lower()
            if fn_name in KNOWN_PRIMITIVES:
                try:
                    res = registry.compute(fn_name, normalized_data, params=ind_def.params)
                    if isinstance(res, list):
                        ind_values[name] = res
                    elif isinstance(res, dict):
                        for k, v in res.items():
                            ind_values[f"{name}_{k}"] = v
                            if k in ("main", "middle", "macd", "k"):
                                ind_values[name] = v
                except Exception as exc:
                    logger.warning("Failed computing indicator primitive %s: %s", fn_name, exc)
                    ind_values[name] = [None] * length
            elif fn_name in ("opening_range_high", "orh"):
                minutes = ind_def.params.get("minutes", 15)
                ind_values[name] = self._compute_opening_range_high(
                    normalized_data, timestamps, minutes
                )
            elif fn_name in ("opening_range_low", "orl"):
                minutes = ind_def.params.get("minutes", 15)
                ind_values[name] = self._compute_opening_range_low(
                    normalized_data, timestamps, minutes
                )
            else:
                # Custom formula expression or custom indicator
                try:
                    compiled_form = self._formula_compiler.compile(ind_def.fn)
                    ind_values[name] = compiled_form.evaluate(normalized_data)
                except Exception:
                    ind_values[name] = [None] * length

        # 2. Evaluate entry rules
        entry_signals: dict[str, list[bool]] = {}
        for entry in self.strategy.entries:
            mask = self._eval_signal_node(
                entry.when,
                normalized_data,
                ind_values,
                timestamps,
                length,
                external_signals=external_signals,
            )
            entry_signals[entry.id] = mask

        # 3. Evaluate exit rules
        exit_signals: dict[str, list[bool]] = {}
        for exit_rule in self.strategy.exits:
            if exit_rule.type == "signal" and exit_rule.when:
                mask = self._eval_signal_node(
                    exit_rule.when,
                    normalized_data,
                    ind_values,
                    timestamps,
                    length,
                    external_signals=external_signals,
                )
                exit_signals[exit_rule.id] = mask
            elif exit_rule.type == "time" and exit_rule.at:
                exit_time = _parse_time_str(exit_rule.at)
                mask = [False] * length
                if exit_time and timestamps:
                    for i, ts in enumerate(timestamps):
                        if ts.time() >= exit_time:
                            mask[i] = True
                exit_signals[exit_rule.id] = mask
            else:
                exit_signals[exit_rule.id] = [False] * length

        return StrategyEvaluationResult(
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            indicator_values=ind_values,
            timestamps=timestamps,
            series_length=length,
        )

    def _normalize_dataset(
        self, data: pa.Table | dict[str, Any] | list[BarRecord]
    ) -> tuple[dict[str, list[Any]], list[datetime], int]:
        if isinstance(data, list) and data and isinstance(data[0], BarRecord):
            length = len(data)
            timestamps = [b.timestamp for b in data]
            normalized = {
                "open": [b.open for b in data],
                "high": [b.high for b in data],
                "low": [b.low for b in data],
                "close": [b.close for b in data],
                "volume": [float(b.volume) for b in data],
                "open_interest": [float(b.open_interest) for b in data],
            }
            return normalized, timestamps, length

        elif isinstance(data, pa.Table):
            length = data.num_rows
            normalized = {}
            for col in data.column_names:
                normalized[col.lower()] = extract_series_nullable(data, col)
            raw_ts: list[Any] = []
            if "timestamp" in normalized:
                raw_ts = normalized["timestamp"]
            elif "ts" in normalized:
                raw_ts = normalized["ts"]
            timestamps_list = [t for t in raw_ts if isinstance(t, datetime)]
            return normalized, timestamps_list, length

        elif isinstance(data, dict):
            length = len(next(iter(data.values()), []))
            normalized = {k.lower(): list(v) for k, v in data.items()}
            raw_dict_ts = normalized.get("timestamp", normalized.get("ts", []))
            timestamps_list = [t for t in raw_dict_ts if isinstance(t, datetime)]
            return normalized, timestamps_list, length

        return {}, [], 0

    def _compute_opening_range_high(
        self, data: dict[str, list[Any]], timestamps: list[datetime], minutes: int
    ) -> list[float | None]:
        highs = data.get("high", [])
        n = len(highs)
        out: list[float | None] = [None] * n
        if not timestamps or len(timestamps) != n:
            return out

        current_day: Any = None
        session_high: float | None = None
        for i in range(n):
            ts = timestamps[i]
            day = ts.date()
            if day != current_day:
                current_day = day
                session_high = highs[i]
            # Calculate minutes from 09:15 IST market open
            open_dt = ts.replace(hour=9, minute=15, second=0, microsecond=0)
            elapsed_minutes = (ts - open_dt).total_seconds() / 60.0
            if elapsed_minutes <= minutes and highs[i] is not None:
                session_high = max(session_high or highs[i], highs[i])
            out[i] = session_high
        return out

    def _compute_opening_range_low(
        self, data: dict[str, list[Any]], timestamps: list[datetime], minutes: int
    ) -> list[float | None]:
        lows = data.get("low", [])
        n = len(lows)
        out: list[float | None] = [None] * n
        if not timestamps or len(timestamps) != n:
            return out

        current_day: Any = None
        session_low: float | None = None
        for i in range(n):
            ts = timestamps[i]
            day = ts.date()
            if day != current_day:
                current_day = day
                session_low = lows[i]
            open_dt = ts.replace(hour=9, minute=15, second=0, microsecond=0)
            elapsed_minutes = (ts - open_dt).total_seconds() / 60.0
            if elapsed_minutes <= minutes and lows[i] is not None:
                session_low = min(session_low or lows[i], lows[i])
            out[i] = session_low
        return out

    def _eval_operand(
        self,
        operand: OperandRef,
        data: dict[str, list[Any]],
        ind_values: dict[str, list[Any]],
        length: int,
    ) -> list[Any]:
        if isinstance(operand, (int, float, bool, str)):
            if isinstance(operand, str) and operand in data:
                return data[operand]
            if isinstance(operand, str) and operand in ind_values:
                return ind_values[operand]
            return [operand] * length
        elif isinstance(operand, FieldOperand):
            col = operand.field.lower()
            return data.get(col, [None] * length)
        elif isinstance(operand, RefOperand):
            return ind_values.get(operand.ref, [None] * length)
        elif isinstance(operand, ConstOperand):
            return [operand.const] * length
        elif isinstance(operand, dict):
            if "field" in operand:
                return data.get(operand["field"].lower(), [None] * length)
            elif "ref" in operand:
                return ind_values.get(operand["ref"], [None] * length)
            elif "const" in operand:
                return [operand["const"]] * length
        return [None] * length

    def _eval_signal_node(
        self,
        node: SignalNode,
        data: dict[str, list[Any]],
        ind_values: dict[str, list[Any]],
        timestamps: list[datetime],
        length: int,
        external_signals: Mapping[tuple[str, str], Sequence[bool]] | None = None,
    ) -> list[bool]:
        if isinstance(node, AndNode):
            child_masks = [
                self._eval_signal_node(
                    c, data, ind_values, timestamps, length, external_signals=external_signals
                )
                for c in node.children
            ]
            return [all(mask[i] for mask in child_masks) for i in range(length)]

        elif isinstance(node, OrNode):
            child_masks = [
                self._eval_signal_node(
                    c, data, ind_values, timestamps, length, external_signals=external_signals
                )
                for c in node.children
            ]
            return [any(mask[i] for mask in child_masks) for i in range(length)]

        elif isinstance(node, NotNode):
            child_mask = self._eval_signal_node(
                node.child, data, ind_values, timestamps, length, external_signals=external_signals
            )
            return [not child_mask[i] for i in range(length)]

        elif isinstance(node, IndicatorCompareNode):
            left_series = self._eval_operand(node.left, data, ind_values, length)
            right_series = self._eval_operand(node.right, data, ind_values, length)
            return [
                _compare_values(left_series[i], node.op, right_series[i]) for i in range(length)
            ]

        elif isinstance(node, CrossOverNode):
            left_series = self._eval_operand(node.left, data, ind_values, length)
            right_series = self._eval_operand(node.right, data, ind_values, length)
            out = [False] * length
            for i in range(1, length):
                l_cur, r_cur = left_series[i], right_series[i]
                l_prev, r_prev = left_series[i - 1], right_series[i - 1]
                if None not in (l_cur, r_cur, l_prev, r_prev):
                    out[i] = bool(l_cur > r_cur and l_prev <= r_prev)
            return out

        elif isinstance(node, CrossUnderNode):
            left_series = self._eval_operand(node.left, data, ind_values, length)
            right_series = self._eval_operand(node.right, data, ind_values, length)
            out = [False] * length
            for i in range(1, length):
                l_cur, r_cur = left_series[i], right_series[i]
                l_prev, r_prev = left_series[i - 1], right_series[i - 1]
                if None not in (l_cur, r_cur, l_prev, r_prev):
                    out[i] = bool(l_cur < r_cur and l_prev >= r_prev)
            return out

        elif isinstance(node, PriceLevelBreakNode):
            level_series: list[Any] = [None] * length
            if isinstance(node.level, LevelRef) and node.level.ref:
                level_series = ind_values.get(node.level.ref, [None] * length)
            elif isinstance(node.level, dict) and "ref" in node.level:
                level_series = ind_values.get(str(node.level["ref"]), [None] * length)
            elif isinstance(node.level, str):
                level_series = ind_values.get(node.level, data.get(node.level, [None] * length))

            closes = data.get("close", [None] * length)
            highs = data.get("high", [None] * length)
            lows = data.get("low", [None] * length)

            after_mask = [True] * length
            if node.after:
                after_mask = self._eval_signal_node(
                    node.after,
                    data,
                    ind_values,
                    timestamps,
                    length,
                    external_signals=external_signals,
                )

            out = [False] * length
            for i in range(1, length):
                lvl = level_series[i]
                if lvl is None or closes[i] is None or closes[i - 1] is None:
                    continue
                if node.direction == "above":
                    is_break = (closes[i] > lvl and closes[i - 1] <= lvl) or (
                        highs[i] is not None and highs[i] > lvl and closes[i - 1] <= lvl
                    )
                else:
                    is_break = (closes[i] < lvl and closes[i - 1] >= lvl) or (
                        lows[i] is not None and lows[i] < lvl and closes[i - 1] >= lvl
                    )

                out[i] = bool(is_break and after_mask[i])
            return out

        elif isinstance(node, SequenceNode):
            step_masks = [
                self._eval_signal_node(
                    step,
                    data,
                    ind_values,
                    timestamps,
                    length,
                    external_signals=external_signals,
                )
                for step in node.steps
            ]
            out = [False] * length
            within = node.within
            for i in range(length):
                if not step_masks[-1][i]:
                    continue
                curr_idx = i
                matched = True
                for step_idx in range(len(step_masks) - 2, -1, -1):
                    found_bar = -1
                    min_bar = max(0, curr_idx - within)
                    for b in range(curr_idx - 1, min_bar - 1, -1):
                        if step_masks[step_idx][b]:
                            found_bar = b
                            break
                    if found_bar == -1:
                        matched = False
                        break
                    curr_idx = found_bar
                out[i] = matched
            return out

        elif isinstance(node, TimeWindowNode):
            out = [False] * length
            from_t = _parse_time_str(node.from_time)
            to_t = _parse_time_str(node.to_time)

            if node.mode == "clock" and timestamps:
                for i, ts in enumerate(timestamps):
                    t = ts.time()
                    in_from = (t >= from_t) if from_t else True
                    in_to = (t <= to_t) if to_t else True
                    out[i] = in_from and in_to
            elif node.mode == "from_open" and timestamps:
                min_start = float(node.from_time or 0)
                min_end = float(node.to_time or 375)
                for i, ts in enumerate(timestamps):
                    open_dt = ts.replace(hour=9, minute=15, second=0, microsecond=0)
                    elapsed = (ts - open_dt).total_seconds() / 60.0
                    out[i] = bool(min_start <= elapsed <= min_end)
            else:
                out = [True] * length
            return out

        elif isinstance(node, PctChangeNode):
            series = self._eval_operand(node.source, data, ind_values, length)
            lookback = node.lookback
            out = [False] * length
            for i in range(lookback, length):
                cur, prev = series[i], series[i - lookback]
                if cur is not None and prev is not None and prev != 0:
                    pct = ((cur - prev) / abs(prev)) * 100.0
                    out[i] = _compare_values(pct, node.op, node.value)
            return out

        elif isinstance(node, PersistNode):
            child_mask = self._eval_signal_node(
                node.child,
                data,
                ind_values,
                timestamps,
                length,
                external_signals=external_signals,
            )
            bars = node.bars
            out = [False] * length
            for i in range(bars - 1, length):
                out[i] = all(child_mask[j] for j in range(i - bars + 1, i + 1))
            return out

        elif isinstance(node, StrategySignalNode):
            key = (str(node.strategy_id), node.signal)
            if external_signals and key in external_signals:
                sig = external_signals[key]
                if len(sig) >= length:
                    return [bool(x) for x in sig[:length]]
                return [bool(x) for x in sig] + [False] * (length - len(sig))
            return [False] * length

        elif isinstance(node, RegimeNode):
            regime_closes: list[float] = [float(x) for x in data.get("close", [])]
            highs_raw = data.get("high")
            regime_highs: list[float] | None = (
                [float(x) for x in highs_raw] if highs_raw is not None else None
            )
            lows_raw = data.get("low")
            regime_lows: list[float] | None = (
                [float(x) for x in lows_raw] if lows_raw is not None else None
            )
            if not regime_closes:
                return [False] * length
            try:
                detector = RegimeDetectorRegistry.get(node.detector)
                states = detector.evaluate_series(regime_closes, regime_highs, regime_lows)
                return [bool(st == node.state) for st in states]
            except Exception as exc:
                logger.warning("Failed evaluating regime detector %s: %s", node.detector, exc)
                return [False] * length

        elif isinstance(node, CustomPythonNode):
            return [False] * length


class VectorStrategyCompiler:
    """Entry point compiler creating executable CompiledStrategy instances."""

    @classmethod
    def compile(cls, strategy: StrategyIR) -> CompiledStrategy:
        """Compile a StrategyIR definition into an executable vectorized model."""
        return CompiledStrategy(strategy)
