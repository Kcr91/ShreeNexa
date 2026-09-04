"""Order ticket endpoints for estimation, validation, placement, and status tracking."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.dhan.exceptions import DhanTimeoutError
from app.dhan.margin_adapter import dhan_margin_adapter
from app.dhan.orders import (
    DhanOrderRequest,
    ExchangeSegment,
    OrderStatus,
    OrderType,
    ProductType,
    TransactionType,
)
from app.engine.audit import AuditEventType, get_audit_ledger
from app.engine.broker import (
    LiveTradingDisabledError,
    StaticIPMismatchError,
)
from app.engine.contracts import OrderSide
from app.engine.costs import ProductType as CostProductType
from app.engine.costs import cost_calculator
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
    security_id: str | None = None
    trigger_price: float | None = None
    instrument_type: str | None = None
    trade_date: date | None = None
    broker_response_override: dict[str, Any] | None = None


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
    required_margin: float | None = None
    is_margin_available: bool = True
    margin_unavailable_reason: str | None = None
    cost_schedule_id: str | None = None


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
    """Calculate regulatory taxes, exchange fees, broker commissions, and margin for an order.

    CRITICAL PARITY INVARIANT (QA-21 / F3.3 / F8.6 / F9.4):
    1. Statutory taxes and broker fees are calculated solely through the unified
       effective-dated IndianCostCalculator (app/engine/costs.py).
    2. Margin requirements are computed via the DhanMarginAdapter (app/dhan/margin_adapter.py).
       Unavailable margin is returned as explicit None with is_margin_available=False,
       NEVER fabricated with an invented leverage percentage or zero.
    """
    fno_segments = (
        ExchangeSegment.NSE_FNO,
        ExchangeSegment.BSE_FNO,
        ExchangeSegment.MCX_COMM,
    )
    if req.exchange_segment in fno_segments:
        sym = req.symbol.upper()
        inst = (req.instrument_type or "").upper()
        if inst.startswith("FUT") or "FUT" in sym:
            cost_prod = CostProductType.FUTURES
        else:
            cost_prod = CostProductType.OPTIONS
    elif req.product_type == ProductType.CNC:
        cost_prod = CostProductType.DELIVERY
    else:
        cost_prod = CostProductType.INTRADAY

    # 2. Map side
    order_side = OrderSide.BUY if req.transaction_type == TransactionType.BUY else OrderSide.SELL

    # 3. Resolve effective trade timestamp
    if req.trade_date:
        trade_ts = datetime.combine(req.trade_date, datetime.min.time(), tzinfo=UTC)
    else:
        trade_ts = datetime.now(UTC)

    # 4. Delegate to unified cost calculator (F3.3)
    breakdown = cost_calculator.calculate_cost(
        product_type=cost_prod,
        side=order_side,
        quantity=req.quantity,
        price=req.price,
        timestamp=trade_ts,
    )
    turnover = round(req.quantity * req.price, 2)

    # 5. Delegate margin to DhanMarginAdapter (F8.6)
    margin_res = dhan_margin_adapter.calculate_order_margin(
        symbol=req.symbol,
        exchange_segment=str(req.exchange_segment),
        transaction_type=str(req.transaction_type),
        product_type=str(req.product_type),
        quantity=req.quantity,
        price=req.price,
        security_id=req.security_id,
        trigger_price=req.trigger_price or 0.0,
        broker_response_override=req.broker_response_override,
    )

    return OrderChargesEstimateResponse(
        turnover=turnover,
        brokerage=round(breakdown.brokerage, 2),
        stt_ctt=round(breakdown.stt_ctt, 2),
        exchange_turnover_charges=round(breakdown.exchange_txn_charge, 2),
        sebi_charges=round(breakdown.sebi_fee, 2),
        stamp_duty=round(breakdown.stamp_duty, 2),
        gst=round(breakdown.gst, 2),
        total_charges=round(breakdown.total_cost, 2),
        required_margin=margin_res.required_margin,
        is_margin_available=margin_res.is_available,
        margin_unavailable_reason=margin_res.unreliable_reason,
        cost_schedule_id=breakdown.schedule_id,
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
    audit = get_audit_ledger()
    audit.record_event(
        AuditEventType.ORDER_SUBMITTED,
        correlation_id=correlation_id,
        order_id=paper_order.order_id,
        payload={
            "mode": "PAPER",
            "security_id": req.security_id,
            "quantity": req.quantity,
            "side": side.value,
        },
    )

    _ = paper_broker.submit_orders([paper_order])

    if paper_order.status == PaperOrderStatus.REJECTED:
        audit.record_event(
            AuditEventType.ORDER_RESPONSE,
            correlation_id=correlation_id,
            order_id=paper_order.order_id,
            payload={"status": "REJECTED", "reject_reason": paper_order.reject_reason},
        )
        return TicketPlaceOrderResponse(
            success=False,
            mode=req.mode,
            order_id=paper_order.order_id,
            correlation_id=correlation_id,
            order_status=paper_order.status.value,
            message=paper_order.reject_reason or "Order rejected by paper broker.",
        )

    audit.record_event(
        AuditEventType.ORDER_RESPONSE,
        correlation_id=correlation_id,
        order_id=paper_order.order_id,
        payload={"status": "PENDING"},
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

