"""Order ticket endpoints for estimation, validation, placement, and status tracking."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.dhan.orders import (
    ExchangeSegment,
    OrderStatus,
    OrderType,
    ProductType,
    TransactionType,
)
from app.engine.broker import DhanBroker, LiveTradingDisabledError

logger = logging.getLogger("shreenexa.api.orders")

router = APIRouter(prefix="/api/v1/orders/ticket", tags=["Order Ticket"])

# In-memory tracking of correlation IDs and orders with uncertain status to block blind retries
_uncertain_orders: dict[str, str] = {}


class ExecutionMode(StrEnum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class OrderChargesEstimateRequest(BaseModel):
    """Payload to estimate statutory charges, taxes, and margin requirements."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    exchange_segment: ExchangeSegment = ExchangeSegment.NSE_EQ
    transaction_type: TransactionType = TransactionType.BUY
    product_type: ProductType = ProductType.INTRADAY
    order_type: OrderType = OrderType.LIMIT
    quantity: int = Field(gt=0)
    price: float = Field(gt=0.0)


class OrderChargesEstimateResponse(BaseModel):
    """Breakdown of calculated statutory charges, brokerage, and net margin."""

    turnover: float
    brokerage: float
    stt_ctt: float
    exchange_turnover_charges: float
    sebi_charges: float
    stamp_duty: float
    gst: float
    total_charges: float
    required_margin: float


class TicketPlaceOrderRequest(BaseModel):
    """Order placement request from interactive order ticket."""

    model_config = ConfigDict(populate_by_name=True)

    mode: ExecutionMode = ExecutionMode.PAPER
    confirmation_acknowledged: bool = Field(
        default=False,
        description="Must be True for LIVE execution mode to confirm intent.",
    )
    symbol: str
    security_id: str
    exchange_segment: ExchangeSegment = ExchangeSegment.NSE_EQ
    transaction_type: TransactionType
    order_type: OrderType
    product_type: ProductType
    quantity: int = Field(gt=0)
    price: float | None = None
    trigger_price: float | None = None
    correlation_id: str | None = None


class TicketPlaceOrderResponse(BaseModel):
    """Result of order ticket placement."""

    success: bool
    mode: ExecutionMode
    order_id: str | None = None
    correlation_id: str | None = None
    order_status: str
    message: str


@router.post("/estimate", response_model=OrderChargesEstimateResponse)
def estimate_order_charges(req: OrderChargesEstimateRequest) -> OrderChargesEstimateResponse:
    """Calculate regulatory taxes, exchange fees, broker commissions, and margin for an order."""
    turnover = req.quantity * req.price

    # Brokerage
    if req.exchange_segment in (ExchangeSegment.NSE_FNO, ExchangeSegment.BSE_FNO):
        brokerage = 20.0  # Flat ₹20 per derivative order
    elif req.product_type == ProductType.CNC:
        brokerage = 0.0  # Zero brokerage on delivery
    else:
        brokerage = min(20.0, turnover * 0.0003)

    # STT / CTT
    if req.product_type == ProductType.CNC:
        stt_ctt = turnover * 0.001  # 0.1% on delivery
    elif req.transaction_type == TransactionType.SELL:
        stt_ctt = turnover * 0.00025  # 0.025% on intraday sell
    else:
        stt_ctt = 0.0

    # Exchange transaction charges
    if req.exchange_segment in (ExchangeSegment.NSE_FNO, ExchangeSegment.BSE_FNO):
        exchange_charges = turnover * 0.0005
    else:
        exchange_charges = turnover * 0.0000297

    # SEBI turnover fees (₹10 / crore)
    sebi_charges = turnover * 0.000001

    # Stamp duty (applicable on buy leg)
    if req.transaction_type == TransactionType.BUY:
        stamp_duty = (
            turnover * 0.00015 if req.product_type == ProductType.CNC else turnover * 0.00003
        )
    else:
        stamp_duty = 0.0

    # GST (18% on brokerage + exchange charges + SEBI charges)
    gst = (brokerage + exchange_charges + sebi_charges) * 0.18

    total_charges = round(
        brokerage + stt_ctt + exchange_charges + sebi_charges + stamp_duty + gst,
        2,
    )

    # Margin calculation
    if req.product_type == ProductType.INTRADAY:
        required_margin = round(turnover * 0.20 + total_charges, 2)  # Approx 5x MIS leverage
    else:
        required_margin = round(turnover + total_charges, 2)

    return OrderChargesEstimateResponse(
        turnover=round(turnover, 2),
        brokerage=round(brokerage, 2),
        stt_ctt=round(stt_ctt, 2),
        exchange_turnover_charges=round(exchange_charges, 2),
        sebi_charges=round(sebi_charges, 2),
        stamp_duty=round(stamp_duty, 2),
        gst=round(gst, 2),
        total_charges=total_charges,
        required_margin=required_margin,
    )


@router.post("/place", response_model=TicketPlaceOrderResponse)
def place_ticket_order(req: TicketPlaceOrderRequest) -> TicketPlaceOrderResponse:
    """Submit an order from order ticket with explicit mode validation and confirmation."""
    correlation_id = req.correlation_id or f"TICKET-{req.security_id}"

    # Check for status uncertainty to block blind retry
    if correlation_id in _uncertain_orders:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Order with correlation ID '{correlation_id}' is in status "
                "PENDING_BROKER_CONFIRMATION. Blind retry is blocked until broker state converges."
            ),
        )

    if req.mode == ExecutionMode.LIVE:
        # Check confirmation gate
        if not req.confirmation_acknowledged:
            raise HTTPException(
                status_code=400,
                detail="Live order requires explicit confirmation_acknowledged=True",
            )

        # Attempt broker live execution (feature-gated)
        broker = DhanBroker(enable_live_trading=False)  # Default disabled
        try:
            # If broker live trading is disabled, this raises LiveTradingDisabledError
            _ = broker
            raise LiveTradingDisabledError(
                "Live trading is disabled. Explicit operator approval is required."
            )
        except LiveTradingDisabledError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    # Paper mode execution
    simulated_order_id = f"ORD-PAPER-{req.security_id}-{req.quantity}"
    return TicketPlaceOrderResponse(
        success=True,
        mode=req.mode,
        order_id=simulated_order_id,
        correlation_id=correlation_id,
        order_status=OrderStatus.PENDING,
        message=f"Paper order {simulated_order_id} placed successfully.",
    )


@router.get("/status/{order_id}")
def get_ticket_order_status(order_id: str) -> dict[str, Any]:
    """Retrieve order status and report if it is in an uncertain state."""
    is_uncertain = order_id in _uncertain_orders.values()
    status = OrderStatus.PENDING_BROKER_CONFIRMATION if is_uncertain else OrderStatus.PENDING
    return {
        "order_id": order_id,
        "status": status,
        "is_uncertain": is_uncertain,
        "retry_allowed": not is_uncertain,
    }
