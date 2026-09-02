"""Simulated broker execution engine with explicit fill timing and slippage models."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

from app.engine.contracts import (
    FillEvent,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
)
from app.engine.slippage import NoSlippageModel, SlippageModel
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class FillTiming(StrEnum):
    """Execution timing model relative to signal generation bar."""

    NEXT_BAR_OPEN = "NEXT_BAR_OPEN"
    SIGNAL_BAR_CLOSE = "SIGNAL_BAR_CLOSE"


class SimBroker:
    """Simulated execution broker matching orders against historical bar OHLC."""

    def __init__(
        self,
        slippage_model: SlippageModel | None = None,
        fill_timing: FillTiming = FillTiming.NEXT_BAR_OPEN,
        initial_cash: float = 1_000_000.0,
    ) -> None:
        self.slippage_model: SlippageModel = slippage_model or NoSlippageModel()
        self.fill_timing = fill_timing
        self.portfolio = Portfolio.create(initial_cash=initial_cash)
        self._pending_orders: dict[str, OrderRequest] = {}
        self._order_statuses: dict[str, OrderStatus] = {}

    def submit(self, orders: list[OrderRequest]) -> list[OrderResult]:
        """Accept order requests for simulated execution."""
        results: list[OrderResult] = []
        now = datetime.now(tz=UTC)
        for order in orders:
            if order.quantity <= 0:
                results.append(
                    OrderResult(
                        order_id=order.order_id,
                        status=OrderStatus.REJECTED,
                        reason="Order quantity must be positive",
                        submitted_at=now,
                    )
                )
                continue

            self._pending_orders[order.order_id] = order
            self._order_statuses[order.order_id] = OrderStatus.ACCEPTED
            results.append(
                OrderResult(
                    order_id=order.order_id,
                    status=OrderStatus.ACCEPTED,
                    submitted_at=now,
                )
            )
        return results

    def cancel(self, order_id: str) -> bool:
        """Cancel an active pending order."""
        if order_id in self._pending_orders:
            del self._pending_orders[order_id]
            self._order_statuses[order_id] = OrderStatus.CANCELLED
            return True
        return False

    def process_bar(self, bar: BarRecord) -> list[FillEvent]:
        """Match pending orders against incoming bar price action."""
        fills: list[FillEvent] = []
        matching_order_ids = [
            oid
            for oid, o in self._pending_orders.items()
            if o.security_id == bar.security_id and o.exchange_segment == bar.exchange_segment
        ]

        for oid in matching_order_ids:
            order = self._pending_orders.get(oid)
            if not order:
                continue

            fill = self._match_order(order, bar)
            if fill is not None:
                fills.append(fill)
                self.portfolio.apply_fill(fill)
                del self._pending_orders[oid]
                self._order_statuses[oid] = OrderStatus.FILLED

        return fills

    def _match_order(self, order: OrderRequest, bar: BarRecord) -> FillEvent | None:
        """Match single order against bar OHLC according to order type and fill timing."""
        ref_price: float | None = None

        if order.order_type == OrderType.MARKET:
            if self.fill_timing == FillTiming.NEXT_BAR_OPEN:
                ref_price = bar.open
            else:
                ref_price = bar.close

        elif order.order_type == OrderType.LIMIT:
            if order.price is None:
                return None
            if order.side == OrderSide.BUY:
                if bar.low <= order.price:
                    ref_price = min(bar.open, order.price)
            else:  # SELL
                if bar.high >= order.price:
                    ref_price = max(bar.open, order.price)

        elif order.order_type == OrderType.SL_M:
            if order.trigger_price is None:
                return None
            if order.side == OrderSide.BUY:
                if bar.high >= order.trigger_price:
                    ref_price = max(bar.open, order.trigger_price)
            else:  # SELL
                if bar.low <= order.trigger_price:
                    ref_price = min(bar.open, order.trigger_price)

        elif order.order_type == OrderType.SL:
            if order.trigger_price is None or order.price is None:
                return None
            if order.side == OrderSide.BUY:
                if bar.high >= order.trigger_price and bar.low <= order.price:
                    ref_price = min(max(bar.open, order.trigger_price), order.price)
            else:  # SELL
                if bar.low <= order.trigger_price and bar.high >= order.price:
                    ref_price = max(min(bar.open, order.trigger_price), order.price)

        if ref_price is None:
            return None

        # Compute fill price and slippage from model
        fill_price, unit_slippage = self.slippage_model.compute_fill_price(
            reference_price=ref_price,
            side=order.side,
            bar=bar,
        )
        total_slippage = unit_slippage * order.quantity

        return FillEvent(
            order_id=order.order_id,
            security_id=order.security_id,
            exchange_segment=order.exchange_segment,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            timestamp=bar.timestamp,
            brokerage=0.0,
            taxes=0.0,
            slippage=total_slippage,
        )

    def get_positions(self) -> dict[str, Position]:
        """Return active portfolio positions."""
        return self.portfolio.positions

    def get_account_balance(self) -> float:
        """Return available cash balance."""
        return self.portfolio.cash
