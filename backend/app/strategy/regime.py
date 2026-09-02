"""Versioned regime detectors, look-ahead prevention, and walk-forward verification."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from app.backtest.walk_forward import WalkForwardResult
from app.strategy.ir import (
    AndNode,
    NotNode,
    OrNode,
    PersistNode,
    PriceLevelBreakNode,
    RegimeNode,
    SequenceNode,
    SignalNode,
    StrategyIR,
)


class WalkForwardEvidenceRequiredError(ValueError):
    """Raised when headline metrics requested for regime strategy without evidence."""


class UnknownRegimeDetectorError(KeyError):
    """Raised when a StrategyIR references an unregistered regime detector model."""


class RegimeDetector(ABC):
    """Abstract base class for point-in-time versioned regime detectors."""

    name: ClassVar[str]
    version: ClassVar[str]
    supported_states: ClassVar[list[str]]

    @abstractmethod
    def evaluate_series(
        self,
        closes: Sequence[float],
        highs: Sequence[float] | None = None,
        lows: Sequence[float] | None = None,
    ) -> list[str]:
        """Compute point-in-time regime state for each bar using strictly no look-ahead."""

    @abstractmethod
    def update_bar(
        self,
        close: float,
        high: float | None = None,
        low: float | None = None,
    ) -> str:
        """Incrementally update detector state with a single incoming bar."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal streaming state."""


class VolRegimeDetector_v1(RegimeDetector):
    """Version 1 volatility regime detector: categorizes into low_vol, normal_vol, high_vol."""

    name = "vol_v1"
    version = "1.0.0"
    supported_states: ClassVar[list[str]] = ["low_vol", "normal_vol", "high_vol"]

    def __init__(self, window: int = 10) -> None:
        self.window = window
        self.reset()

    def reset(self) -> None:
        self._closes: deque[float] = deque(maxlen=self.window + 1)
        self._vol_history: deque[float] = deque(maxlen=self.window * 2)

    def update_bar(
        self,
        close: float,
        high: float | None = None,
        low: float | None = None,
    ) -> str:
        self._closes.append(close)
        if len(self._closes) < 3:
            return "normal_vol"

        # Point-in-time realized vol of percentage returns
        rets = [
            (self._closes[i] - self._closes[i - 1]) / self._closes[i - 1]
            for i in range(1, len(self._closes))
        ]
        m = sum(rets) / len(rets)
        var = sum((r - m) ** 2 for r in rets) / len(rets)
        curr_vol = math.sqrt(var)
        self._vol_history.append(curr_vol)

        if len(self._vol_history) < self.window:
            return "normal_vol"

        avg_vol = sum(self._vol_history) / len(self._vol_history)
        if avg_vol <= 1e-8:
            return "normal_vol"

        if curr_vol > avg_vol * 1.25:
            return "high_vol"
        elif curr_vol < avg_vol * 0.75:
            return "low_vol"
        return "normal_vol"

    def evaluate_series(
        self,
        closes: Sequence[float],
        highs: Sequence[float] | None = None,
        lows: Sequence[float] | None = None,
    ) -> list[str]:
        # Clean detector instance guarantees point-in-time calculation
        det = VolRegimeDetector_v1(window=self.window)
        return [det.update_bar(c) for c in closes]


class TrendRegimeDetector_v1(RegimeDetector):
    """Version 1 trend regime detector: categorizes into trending_up, trending_down, ranging."""

    name = "trend_v1"
    version = "1.0.0"
    supported_states: ClassVar[list[str]] = ["trending_up", "trending_down", "ranging"]

    def __init__(self, fast_period: int = 5, slow_period: int = 15) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.reset()

    def reset(self) -> None:
        self._closes: deque[float] = deque(maxlen=self.slow_period)

    def update_bar(
        self,
        close: float,
        high: float | None = None,
        low: float | None = None,
    ) -> str:
        self._closes.append(close)
        if len(self._closes) < self.slow_period:
            return "ranging"

        # Point-in-time fast SMA and slow SMA
        fast_closes = list(self._closes)[-self.fast_period:]
        fast_sma = sum(fast_closes) / self.fast_period
        slow_sma = sum(self._closes) / self.slow_period

        if slow_sma <= 1e-8:
            return "ranging"

        diff_pct = (fast_sma - slow_sma) / slow_sma
        if diff_pct > 0.005:
            return "trending_up"
        elif diff_pct < -0.005:
            return "trending_down"
        return "ranging"

    def evaluate_series(
        self,
        closes: Sequence[float],
        highs: Sequence[float] | None = None,
        lows: Sequence[float] | None = None,
    ) -> list[str]:
        det = TrendRegimeDetector_v1(
            fast_period=self.fast_period, slow_period=self.slow_period
        )
        return [det.update_bar(c) for c in closes]


class RegimeDetectorRegistry:
    """Registry maintaining active and historical versioned regime detector models."""

    _detectors: ClassVar[dict[str, type[RegimeDetector]]] = {}

    @classmethod
    def register(cls, detector_cls: type[RegimeDetector]) -> None:
        """Register a versioned detector implementation."""
        cls._detectors[detector_cls.name] = detector_cls

    @classmethod
    def get(cls, name: str) -> RegimeDetector:
        """Retrieve a fresh instance of a registered regime detector."""
        if name not in cls._detectors:
            raise UnknownRegimeDetectorError(f"Regime detector '{name}' is not registered")
        return cls._detectors[name]()

    @classmethod
    def list_detectors(cls) -> list[str]:
        return sorted(cls._detectors.keys())


# Register canonical versioned detectors
RegimeDetectorRegistry.register(VolRegimeDetector_v1)
RegimeDetectorRegistry.register(TrendRegimeDetector_v1)


def has_regime_conditioning(strategy: StrategyIR) -> bool:
    """Check whether a strategy definition contains any RegimeNode conditions."""
    found = False

    def _walk(node: SignalNode | None) -> None:
        nonlocal found
        if node is None or found:
            return
        if isinstance(node, RegimeNode):
            found = True
            return
        elif isinstance(node, (AndNode, OrNode)):
            for child in node.children:
                _walk(child)
        elif isinstance(node, (NotNode, PersistNode)):
            _walk(node.child)
        elif isinstance(node, SequenceNode):
            for step in node.steps:
                _walk(step)
        elif isinstance(node, PriceLevelBreakNode):
            if node.after:
                _walk(node.after)

    for entry in strategy.entries:
        _walk(entry.when)
    for exit_rule in strategy.exits:
        if exit_rule.when:
            _walk(exit_rule.when)

    return found


def validate_headline_metrics_evidence(
    strategy: StrategyIR,
    walk_forward_evidence: WalkForwardResult | Any | None = None,
) -> None:
    """Refuse headline backtest metrics for regime strategies without walk-forward proof."""
    if not has_regime_conditioning(strategy):
        return  # Strategies without regime conditioning do not require walk-forward proof

    if walk_forward_evidence is None:
        raise WalkForwardEvidenceRequiredError(
            "Headline metrics refused: strategy utilizes regime conditioning (RegimeNode) "
            "but no walk-forward analysis evidence was provided."
        )

    mean_wfe = getattr(walk_forward_evidence, "mean_walk_forward_efficiency", None)
    if mean_wfe is None or mean_wfe <= 0.0:
        val_str = f"{mean_wfe:.2f}" if isinstance(mean_wfe, (int, float)) else str(mean_wfe)
        raise WalkForwardEvidenceRequiredError(
            f"Headline metrics refused: mean walk-forward efficiency "
            f"({val_str}) must be positive to validate "
            f"regime-conditioned strategy robustness."
        )
