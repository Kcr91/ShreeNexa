"""Slippage models for simulated execution with bar high/low containment invariants."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.engine.contracts import OrderSide
from app.warehouse.schema import BarRecord


@runtime_checkable
class SlippageModel(Protocol):
    """Protocol for estimating execution slippage and fill prices."""

    def compute_fill_price(
        self,
        reference_price: float,
        side: OrderSide,
        bar: BarRecord,
        tick_size: float = 0.05,
    ) -> tuple[float, float]:
        """Compute execution fill price and total slippage cost per share/unit.

        Returns:
            (fill_price, slippage_per_unit) where fill_price is strictly within [bar.low, bar.high].
        """
        ...


class NoSlippageModel:
    """Zero slippage model: fills at exact reference price (clamped to bar range)."""

    def compute_fill_price(
        self,
        reference_price: float,
        side: OrderSide,
        bar: BarRecord,
        tick_size: float = 0.05,
    ) -> tuple[float, float]:
        fill_price = max(bar.low, min(bar.high, reference_price))
        return fill_price, 0.0


class TickSlippageModel:
    """Tick-based slippage model: shifts fill price by N ticks in unfavorable direction."""

    def __init__(self, ticks: int = 1, default_tick_size: float = 0.05) -> None:
        if ticks < 0:
            raise ValueError("Slippage ticks cannot be negative")
        self.ticks = ticks
        self.default_tick_size = default_tick_size

    def compute_fill_price(
        self,
        reference_price: float,
        side: OrderSide,
        bar: BarRecord,
        tick_size: float = 0.05,
    ) -> tuple[float, float]:
        effective_tick = tick_size if tick_size > 0 else self.default_tick_size
        shift = self.ticks * effective_tick

        if side == OrderSide.BUY:
            raw_fill = reference_price + shift
        else:
            raw_fill = reference_price - shift

        # Enforce hard invariant: no fill price falls outside bar high/low range
        fill_price = max(bar.low, min(bar.high, raw_fill))
        slippage = abs(fill_price - reference_price)
        return fill_price, slippage


class PercentageSlippageModel:
    """Percentage-based slippage model: shifts fill price by fixed percentage (e.g. 0.05%)."""

    def __init__(self, percentage: float = 0.0005) -> None:
        if percentage < 0.0:
            raise ValueError("Slippage percentage cannot be negative")
        self.percentage = percentage

    def compute_fill_price(
        self,
        reference_price: float,
        side: OrderSide,
        bar: BarRecord,
        tick_size: float = 0.05,
    ) -> tuple[float, float]:
        if side == OrderSide.BUY:
            raw_fill = reference_price * (1.0 + self.percentage)
        else:
            raw_fill = reference_price * (1.0 - self.percentage)

        # Enforce hard invariant: no fill price falls outside bar high/low range
        fill_price = max(bar.low, min(bar.high, raw_fill))
        slippage = abs(fill_price - reference_price)
        return fill_price, slippage
