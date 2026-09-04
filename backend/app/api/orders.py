"""Order ticket endpoints for estimation, validation, placement, and status tracking."""

from __future__ import annotations

import logging
import uuid
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.dhan.exceptions import DhanTimeoutError
from app.dhan.orders import (
    DhanOrderRequest,
    ExchangeSegment,
    OrderStatus,
    OrderType,
    ProductType,
    TransactionType,
)
from app.engine.broker import (
    LiveTradingDisabledError,
    StaticIPMismatchError,
)
from app.engine.gateway import get_risk_filtered_broker
from app.engine.risk import (
    KillSwitchActiveError,
    RiskCheckFailedError,
)
from app.paper.broker import paper_broker
from app.paper.models import (
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)

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

        # Route through pre-trade risk-filtered broker gateway
        risk_filtered = get_risk_filtered_broker()
        dhan_req = DhanOrderRequest(
            securityId=req.security_id,
            exchangeSegment=req.exchange_segment,
            transactionType=req.transaction_type,
            orderType=req.order_type,
            productType=req.product_type,
            quantity=req.quantity,
            price=req.price or 0.0,
            triggerPrice=req.trigger_price or 0.0,
            correlationId=correlation_id,
        )
        try:
            order_resp = risk_filtered.place_order(dhan_req)
            order_id = order_resp.order_id or ""
            if isinstance(order_resp.order_status, OrderStatus):
                status_val = order_resp.order_status.value
            elif order_resp.order_status is not None:
                status_val = str(order_resp.order_status)
            else:
                status_val = "PENDING"
            return TicketPlaceOrderResponse(
                success=True,
                mode=req.mode,
                order_id=order_id,
                correlation_id=correlation_id,
                order_status=status_val,
                message=f"Live order {order_id} submitted successfully.",
            )
        except (
            LiveTradingDisabledError,
            StaticIPMismatchError,
            RiskCheckFailedError,
            KillSwitchActiveError,
        ) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except DhanTimeoutError as exc:
            uncertain_id = f"UNCERTAIN-{correlation_id}"
            _uncertain_orders[correlation_id] = uncertain_id
            raise HTTPException(
                status_code=504,
                detail=(
                    f"Broker transport timed out for correlation ID '{correlation_id}'. "
                    "Order state is PENDING_BROKER_CONFIRMATION; blind retry is blocked."
                ),
            ) from exc

    # Paper mode execution delegated to PaperBroker
    side = (
        PaperOrderSide.BUY
        if req.transaction_type == TransactionType.BUY
        else PaperOrderSide.SELL
    )
    if req.order_type == OrderType.MARKET:
        order_type = PaperOrderType.MARKET
    elif req.order_type == OrderType.LIMIT:
        order_type = PaperOrderType.LIMIT
    elif req.order_type == OrderType.STOP_LOSS:
        order_type = PaperOrderType.STOP_LOSS_LIMIT
    elif req.order_type == OrderType.STOP_LOSS_MARKET:
        order_type = PaperOrderType.STOP_LOSS_MARKET
    else:
        order_type = PaperOrderType.LIMIT

    order_id = f"ORD-PAPER-{uuid.uuid4().hex[:8].upper()}"
    paper_order = PaperOrder(
        order_id=order_id,
        account_id="default",
        symbol=req.symbol,
        segment=req.exchange_segment.value,
        security_id=req.security_id,
        side=side,
        order_type=order_type,
        quantity=req.quantity,
        price=req.price,
        trigger_price=req.trigger_price,
    )
    _ = paper_broker.submit_orders([paper_order])

    if paper_order.status == PaperOrderStatus.REJECTED:
        return TicketPlaceOrderResponse(
            success=False,
            mode=req.mode,
            order_id=paper_order.order_id,
            correlation_id=correlation_id,
            order_status=paper_order.status.value,
            message=paper_order.reject_reason or "Order rejected by paper broker.",
        )

    return TicketPlaceOrderResponse(
        success=True,
        mode=req.mode,
        order_id=paper_order.order_id,
        correlation_id=correlation_id,
        order_status=OrderStatus.PENDING.value,
        message=f"Paper order {paper_order.order_id} placed successfully.",
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

