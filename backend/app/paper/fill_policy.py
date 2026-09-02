"""Realistic order matching policy and transaction cost estimation for Paper Trading."""

from __future__ import annotations

from datetime import UTC, datetime

from app.engine.contracts import OrderSide
from app.engine.slippage import NoSlippageModel, SlippageModel
from app.paper.models import (
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)
from app.warehouse.schema import BarRecord


def calculate_indian_statutory_costs(
    side: PaperOrderSide,
    quantity: int,
    price: float,
    segment: str = "NSE_EQ",
) -> float:
    """Compute exact Indian statutory charges (STT, Exchange, SEBI, Stamp Duty, GST)."""
    trade_value = quantity * price
    if trade_value <= 0:
        return 0.0

    brokerage = min(20.0, trade_value * 0.0003)
    # STT: 0.1% on delivery (BUY & SELL)
    stt = trade_value * 0.001
    # Exchange turnover charge (0.00345%)
    exchange_turnover = trade_value * 0.0000345
    # SEBI turnover charge (₹10 / crore = 0.0001%)
    sebi_charges = trade_value * 0.000001
    # Stamp duty: 0.015% on BUY only
    stamp_duty = trade_value * 0.00015 if side == PaperOrderSide.BUY else 0.0
    # GST: 18% on (Brokerage + Exchange charges + SEBI charges)
    gst = (brokerage + exchange_turnover + sebi_charges) * 0.18

    total_cost = brokerage + stt + exchange_turnover + sebi_charges + stamp_duty + gst
    return round(total_cost, 2)


class PaperFillPolicy:
    """Realistic execution simulator with limit queues, slippage, and stop triggers."""

    def __init__(self, slippage_model: SlippageModel | None = None) -> None:
        self.slippage_model: SlippageModel = slippage_model or NoSlippageModel()

    def match_order(
        self,
        order: PaperOrder,
        current_price: float,
        high_price: float | None = None,
        low_price: float | None = None,
        timestamp: datetime | None = None,
    ) -> PaperFill | None:
        """Attempt to fill an active paper order against incoming price action."""
        if order.status not in (PaperOrderStatus.ACCEPTED, PaperOrderStatus.PARTIALLY_FILLED):
            return None

        now = timestamp or datetime.now(tz=UTC)
        high = high_price if high_price is not None else current_price
        low = low_price if low_price is not None else current_price
        rem_qty = order.quantity - order.filled_quantity
        if rem_qty <= 0:
            return None

        bar = BarRecord(
            symbol=order.symbol,
            security_id=order.security_id,
            exchange_segment=order.segment,
            timestamp=now,
            open=current_price,
            high=high,
            low=low,
            close=current_price,
            volume=10000,
        )
        side_contract = OrderSide.BUY if order.side == PaperOrderSide.BUY else OrderSide.SELL

        # 1. Market Order
        if order.order_type == PaperOrderType.MARKET:
            exec_price, slippage = self.slippage_model.compute_fill_price(
                reference_price=current_price,
                side=side_contract,
                bar=bar,
            )
            cost = calculate_indian_statutory_costs(order.side, rem_qty, exec_price, order.segment)

            return PaperFill(
                fill_id=f"fill-{order.order_id}-{now.timestamp()}",
                order_id=order.order_id,
                account_id=order.account_id,
                symbol=order.symbol,
                segment=order.segment,
                security_id=order.security_id,
                side=order.side,
                quantity=rem_qty,
                price=round(exec_price, 2),
                slippage=round(slippage, 4),
                transaction_cost=cost,
                timestamp=now,
            )

        # 2. Limit Order
        elif order.order_type == PaperOrderType.LIMIT:
            if order.price is None:
                return None

            limit_price = order.price
            if order.side == PaperOrderSide.BUY:
                if low <= limit_price:
                    exec_price = min(current_price, limit_price)
                    cost = calculate_indian_statutory_costs(
                        order.side, rem_qty, exec_price, order.segment
                    )
                    return PaperFill(
                        fill_id=f"fill-{order.order_id}-{now.timestamp()}",
                        order_id=order.order_id,
                        account_id=order.account_id,
                        symbol=order.symbol,
                        segment=order.segment,
                        security_id=order.security_id,
                        side=order.side,
                        quantity=rem_qty,
                        price=round(exec_price, 2),
                        slippage=0.0,
                        transaction_cost=cost,
                        timestamp=now,
                    )
            else:  # SELL
                if high >= limit_price:
                    exec_price = max(current_price, limit_price)
                    cost = calculate_indian_statutory_costs(
                        order.side, rem_qty, exec_price, order.segment
                    )
                    return PaperFill(
                        fill_id=f"fill-{order.order_id}-{now.timestamp()}",
                        order_id=order.order_id,
                        account_id=order.account_id,
                        symbol=order.symbol,
                        segment=order.segment,
                        security_id=order.security_id,
                        side=order.side,
                        quantity=rem_qty,
                        price=round(exec_price, 2),
                        slippage=0.0,
                        transaction_cost=cost,
                        timestamp=now,
                    )

        # 3. Stop Loss Market
        elif order.order_type == PaperOrderType.STOP_LOSS_MARKET:
            if order.trigger_price is None:
                return None

            trigger = order.trigger_price
            triggered = (high >= trigger) if order.side == PaperOrderSide.BUY else (low <= trigger)
            if triggered:
                exec_price, slippage = self.slippage_model.compute_fill_price(
                    reference_price=current_price,
                    side=side_contract,
                    bar=bar,
                )
                cost = calculate_indian_statutory_costs(
                    order.side, rem_qty, exec_price, order.segment
                )
                return PaperFill(
                    fill_id=f"fill-{order.order_id}-{now.timestamp()}",
                    order_id=order.order_id,
                    account_id=order.account_id,
                    symbol=order.symbol,
                    segment=order.segment,
                    security_id=order.security_id,
                    side=order.side,
                    quantity=rem_qty,
                    price=round(exec_price, 2),
                    slippage=round(slippage, 4),
                    transaction_cost=cost,
                    timestamp=now,
                )

        # 4. Stop Loss Limit
        elif order.order_type == PaperOrderType.STOP_LOSS_LIMIT:
            if order.trigger_price is None or order.price is None:
                return None

            trigger = order.trigger_price
            limit_price = order.price
            triggered = (high >= trigger) if order.side == PaperOrderSide.BUY else (low <= trigger)
            if triggered:
                # Once triggered, check if limit can be satisfied
                can_fill = (
                    (low <= limit_price)
                    if order.side == PaperOrderSide.BUY
                    else (high >= limit_price)
                )
                if can_fill:
                    exec_price = (
                        min(current_price, limit_price)
                        if order.side == PaperOrderSide.BUY
                        else max(current_price, limit_price)
                    )
                    cost = calculate_indian_statutory_costs(
                        order.side, rem_qty, exec_price, order.segment
                    )
                    return PaperFill(
                        fill_id=f"fill-{order.order_id}-{now.timestamp()}",
                        order_id=order.order_id,
                        account_id=order.account_id,
                        symbol=order.symbol,
                        segment=order.segment,
                        security_id=order.security_id,
                        side=order.side,
                        quantity=rem_qty,
                        price=round(exec_price, 2),
                        slippage=0.0,
                        transaction_cost=cost,
                        timestamp=now,
                    )

        return None
