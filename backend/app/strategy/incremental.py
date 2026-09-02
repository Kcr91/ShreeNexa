"""Incremental StrategyIR compiler and streaming execution engine."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import app.indicators.incremental_primitives  # noqa: F401 - ensure registrations
from app.indicators.incremental import IncrementalIndicator, create_incremental_indicator
from app.strategy.compiler import _compare_values, _parse_time_str
from app.strategy.ir import (
    AndNode,
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
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)

BAR_LEVEL_PRIMITIVES = {"supertrend", "atr", "stoch", "stochastic", "vwap", "obv"}


@dataclass
class StrategyEvaluationStep:
    """Evaluation result for a single streaming bar update."""

    entry_signals: dict[str, bool] = field(default_factory=dict)
    exit_signals: dict[str, bool] = field(default_factory=dict)
    indicator_values: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.min)


class IncrementalStrategyEngine:
    """Stateful, real-time bar-by-bar strategy evaluation engine."""

    def __init__(self, strategy: StrategyIR) -> None:
        self.strategy = strategy
        self._indicators: dict[str, IncrementalIndicator] = {}
        self._indicator_sources: dict[str, str] = {}
        self._special_indicators: set[str] = set()

        # Initialize indicators
        for name, ind_def in self.strategy.indicators.items():
            fn_name = ind_def.fn.lower()
            if fn_name in (
                "rsi",
                "ema",
                "sma",
                "macd",
                "bollinger_bands",
                "supertrend",
                "atr",
                "stoch",
                "stochastic",
                "roc",
                "vwap",
                "obv",
                "rolling_std",
                "zscore",
            ):
                params = dict(ind_def.params)
                if ind_def.source and "column" not in params:
                    params["column"] = ind_def.source
                self._indicators[name] = create_incremental_indicator(fn_name, params)
            elif fn_name in ("opening_range_high", "orh", "opening_range_low", "orl"):
                self._special_indicators.add(name)

        self._prev_bar: BarRecord | None = None
        self._bar_count: int = 0
        self._current_day: Any = None
        self._orh_val: dict[str, float | None] = {}
        self._orl_val: dict[str, float | None] = {}
        self._node_states: dict[str, Any] = {}

    def update(
        self, bar: BarRecord, external_signals: Mapping[tuple[str, str], bool] | None = None
    ) -> StrategyEvaluationStep:
        """Process a single incoming bar in real-time O(1) time."""
        self._bar_count += 1
        day = bar.timestamp.date()
        if day != self._current_day:
            self._current_day = day
            self._orh_val = {}
            self._orl_val = {}

        # 1. Update streaming indicators
        ind_values: dict[str, Any] = {}
        for name, ind in self._indicators.items():
            val = ind.update(bar)
            ind_values[name] = val
            if isinstance(val, dict):
                for k, v in val.items():
                    ind_values[f"{name}_{k}"] = v
                    if k in ("main", "middle", "macd", "k"):
                        ind_values[name] = v

        # 2. Update special indicators (ORH/ORL)
        for name in self._special_indicators:
            ind_def = self.strategy.indicators[name]
            fn_name = ind_def.fn.lower()
            minutes = ind_def.params.get("minutes", 15)
            open_dt = bar.timestamp.replace(hour=9, minute=15, second=0, microsecond=0)
            elapsed = (bar.timestamp - open_dt).total_seconds() / 60.0

            if fn_name in ("opening_range_high", "orh"):
                curr_h = self._orh_val.get(name)
                if elapsed <= minutes:
                    curr_h = max(curr_h or bar.high, bar.high)
                self._orh_val[name] = curr_h
                ind_values[name] = curr_h
            elif fn_name in ("opening_range_low", "orl"):
                curr_l = self._orl_val.get(name)
                if elapsed <= minutes:
                    curr_l = min(curr_l or bar.low, bar.low)
                self._orl_val[name] = curr_l
                ind_values[name] = curr_l

        # 3. Evaluate entry rules
        entry_signals: dict[str, bool] = {}
        for entry in self.strategy.entries:
            path = f"entry_{entry.id}"
            sig = self._eval_node(
                entry.when, bar, ind_values, path, external_signals=external_signals
            )
            entry_signals[entry.id] = sig

        # 4. Evaluate exit rules
        exit_signals: dict[str, bool] = {}
        for exit_rule in self.strategy.exits:
            path = f"exit_{exit_rule.id}"
            if exit_rule.type == "signal" and exit_rule.when:
                sig = self._eval_node(
                    exit_rule.when, bar, ind_values, path, external_signals=external_signals
                )
                exit_signals[exit_rule.id] = sig
            elif exit_rule.type == "time" and exit_rule.at:
                exit_time = _parse_time_str(exit_rule.at)
                exit_signals[exit_rule.id] = bool(exit_time and bar.timestamp.time() >= exit_time)
            else:
                exit_signals[exit_rule.id] = False

        self._prev_bar = bar
        return StrategyEvaluationStep(
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            indicator_values=ind_values,
            timestamp=bar.timestamp,
        )

    def _get_operand_val(
        self, operand: OperandRef, bar: BarRecord, ind_values: dict[str, Any]
    ) -> Any:
        if isinstance(operand, (int, float, bool)):
            return operand
        elif isinstance(operand, str):
            if operand.lower() in ("close", "open", "high", "low", "volume", "oi", "open_interest"):
                return getattr(bar, operand.lower(), None)
            return ind_values.get(operand, None)
        elif isinstance(operand, FieldOperand):
            return getattr(bar, operand.field.lower(), None)
        elif isinstance(operand, RefOperand):
            return ind_values.get(operand.ref, None)
        elif isinstance(operand, ConstOperand):
            return operand.const
        elif isinstance(operand, dict):
            if "field" in operand:
                return getattr(bar, str(operand["field"]).lower(), None)
            elif "ref" in operand:
                return ind_values.get(str(operand["ref"]), None)
            elif "const" in operand:
                return operand["const"]
        return None

    def _eval_node(
        self,
        node: SignalNode,
        bar: BarRecord,
        ind_values: dict[str, Any],
        path: str,
        external_signals: Mapping[tuple[str, str], bool] | None = None,
    ) -> bool:
        if isinstance(node, AndNode):
            return all(
                self._eval_node(
                    c, bar, ind_values, f"{path}_{i}", external_signals=external_signals
                )
                for i, c in enumerate(node.children)
            )

        elif isinstance(node, OrNode):
            return any(
                self._eval_node(
                    c, bar, ind_values, f"{path}_{i}", external_signals=external_signals
                )
                for i, c in enumerate(node.children)
            )

        elif isinstance(node, NotNode):
            return not self._eval_node(
                node.child, bar, ind_values, f"{path}_child", external_signals=external_signals
            )

        elif isinstance(node, IndicatorCompareNode):
            l_val = self._get_operand_val(node.left, bar, ind_values)
            r_val = self._get_operand_val(node.right, bar, ind_values)
            return _compare_values(l_val, node.op, r_val)

        elif isinstance(node, CrossOverNode):
            l_val = self._get_operand_val(node.left, bar, ind_values)
            r_val = self._get_operand_val(node.right, bar, ind_values)
            prev_pair = self._node_states.get(path, (None, None))
            l_prev, r_prev = prev_pair
            self._node_states[path] = (l_val, r_val)
            if None not in (l_val, r_val, l_prev, r_prev):
                return bool(l_val > r_val and l_prev <= r_prev)
            return False

        elif isinstance(node, CrossUnderNode):
            l_val = self._get_operand_val(node.left, bar, ind_values)
            r_val = self._get_operand_val(node.right, bar, ind_values)
            prev_pair = self._node_states.get(path, (None, None))
            l_prev, r_prev = prev_pair
            self._node_states[path] = (l_val, r_val)
            if None not in (l_val, r_val, l_prev, r_prev):
                return bool(l_val < r_val and l_prev >= r_prev)
            return False

        elif isinstance(node, PriceLevelBreakNode):
            lvl: Any = None
            if isinstance(node.level, LevelRef) and node.level.ref:
                lvl = ind_values.get(node.level.ref)
            elif isinstance(node.level, dict) and "ref" in node.level:
                lvl = ind_values.get(str(node.level["ref"]))
            elif isinstance(node.level, str):
                lvl = ind_values.get(node.level, getattr(bar, node.level, None))

            prev_close = self._prev_bar.close if self._prev_bar else None
            is_break = False
            if lvl is not None and prev_close is not None:
                if node.direction == "above":
                    is_break = (bar.close > lvl and prev_close <= lvl) or (
                        bar.high > lvl and prev_close <= lvl
                    )
                else:
                    is_break = (bar.close < lvl and prev_close >= lvl) or (
                        bar.low < lvl and prev_close >= lvl
                    )

            after_sig = True
            if node.after:
                after_sig = self._eval_node(
                    node.after, bar, ind_values, f"{path}_after", external_signals=external_signals
                )

            return bool(is_break and after_sig)

        elif isinstance(node, SequenceNode):
            # Track history deque of triggered steps: [(bar_index, step_index)]
            step_history: deque[tuple[int, int]] = self._node_states.setdefault(
                path, deque(maxlen=node.within * 2)
            )

            # Check which steps trigger on this bar
            for s_idx, step in enumerate(node.steps):
                if self._eval_node(
                    step, bar, ind_values, f"{path}_s{s_idx}", external_signals=external_signals
                ):
                    step_history.append((self._bar_count, s_idx))

            # Check if sequence is satisfied terminating on current bar
            if not step_history or step_history[-1][1] != len(node.steps) - 1:
                return False
            if step_history[-1][0] != self._bar_count:
                return False

            curr_idx = self._bar_count
            matched = True
            for step_idx in range(len(node.steps) - 2, -1, -1):
                found_bar = -1
                min_bar = max(0, curr_idx - node.within)
                for b_num, s_num in reversed(step_history):
                    if s_num == step_idx and min_bar <= b_num < curr_idx:
                        found_bar = b_num
                        break
                if found_bar == -1:
                    matched = False
                    break
                curr_idx = found_bar
            return matched

        elif isinstance(node, TimeWindowNode):
            from_t = _parse_time_str(node.from_time)
            to_t = _parse_time_str(node.to_time)
            t = bar.timestamp.time()
            if node.mode == "clock":
                in_from = (t >= from_t) if from_t else True
                in_to = (t <= to_t) if to_t else True
                return in_from and in_to
            elif node.mode == "from_open":
                open_dt = bar.timestamp.replace(hour=9, minute=15, second=0, microsecond=0)
                elapsed = (bar.timestamp - open_dt).total_seconds() / 60.0
                min_start = float(node.from_time or 0)
                min_end = float(node.to_time or 375)
                return bool(min_start <= elapsed <= min_end)
            return True

        elif isinstance(node, PctChangeNode):
            src_val = self._get_operand_val(node.source, bar, ind_values)
            buf: deque[float] = self._node_states.setdefault(path, deque(maxlen=node.lookback + 1))
            if src_val is not None:
                buf.append(float(src_val))
            if len(buf) == node.lookback + 1:
                prev_val = buf[0]
                cur_val = buf[-1]
                if prev_val != 0:
                    pct = ((cur_val - prev_val) / abs(prev_val)) * 100.0
                    return _compare_values(pct, node.op, node.value)
            return False

        elif isinstance(node, PersistNode):
            child_sig = self._eval_node(
                node.child, bar, ind_values, f"{path}_child", external_signals=external_signals
            )
            consecutive: int = self._node_states.get(path, 0)
            if child_sig:
                consecutive += 1
            else:
                consecutive = 0
            self._node_states[path] = consecutive
            return consecutive >= node.bars

        elif isinstance(node, StrategySignalNode):
            key = (str(node.strategy_id), node.signal)
            if external_signals and key in external_signals:
                return bool(external_signals[key])
            return False

        elif isinstance(node, (RegimeNode, CustomPythonNode)):
            return False

        return False

    def get_state(self) -> dict[str, Any]:
        """Serialize complete engine state for checkpointing and failover recovery."""
        ind_states: dict[str, Any] = {}
        for name, ind in self._indicators.items():
            ind_states[name] = ind.state

        # Make node states JSON-serializable
        serializable_nodes: dict[str, Any] = {}
        for k, v in self._node_states.items():
            if isinstance(v, deque):
                serializable_nodes[k] = list(v)
            else:
                serializable_nodes[k] = v

        return {
            "bar_count": self._bar_count,
            "prev_bar": self._prev_bar.model_dump() if self._prev_bar else None,
            "current_day": str(self._current_day) if self._current_day else None,
            "indicators": ind_states,
            "orh_val": self._orh_val,
            "orl_val": self._orl_val,
            "node_states": serializable_nodes,
        }

    def restore_state(self, checkpoint: dict[str, Any]) -> None:
        """Restore engine state from checkpoint dictionary."""
        self._bar_count = checkpoint.get("bar_count", 0)
        prev_bar_dict = checkpoint.get("prev_bar")
        self._prev_bar = BarRecord.model_validate(prev_bar_dict) if prev_bar_dict else None
        day_str = checkpoint.get("current_day")
        self._current_day = datetime.fromisoformat(day_str).date() if day_str else None
        self._orh_val = checkpoint.get("orh_val", {})
        self._orl_val = checkpoint.get("orl_val", {})

        # Restore indicator states
        ind_states = checkpoint.get("indicators", {})
        for name, state in ind_states.items():
            if name in self._indicators:
                self._indicators[name].restore_state(state)

        # Restore node states
        raw_nodes = checkpoint.get("node_states", {})
        self._node_states = {}
        for k, v in raw_nodes.items():
            if isinstance(v, list):
                self._node_states[k] = deque(v)
            else:
                self._node_states[k] = v

    def reset(self) -> None:
        """Reset all internal indicator buffers, bar counters, and signal states."""
        for ind in self._indicators.values():
            ind.reset()
        self._prev_bar = None
        self._bar_count = 0
        self._current_day = None
        self._orh_val = {}
        self._orl_val = {}
        self._node_states = {}


class IncrementalStrategyCompiler:
    """Factory compiling a StrategyIR into an IncrementalStrategyEngine."""

    @classmethod
    def compile(cls, strategy: StrategyIR) -> IncrementalStrategyEngine:
        """Compile a StrategyIR definition into an incremental streaming engine."""
        return IncrementalStrategyEngine(strategy)
