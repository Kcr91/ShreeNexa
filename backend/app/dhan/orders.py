"""Typed order models, enums, slicing, and correlation ID utilities for DhanHQ v2.5.

NOTICE: Order Placement, Modification, Cancellation, and Slicing APIs require
SEBI-mandated Static IP whitelisting.
"""

from __future__ import annotations

import re
import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionType(StrEnum):
    """Trading side of the order."""

    BUY = "BUY"
    SELL = "SELL"


class ExchangeSegment(StrEnum):
    """Exchange and market segment identifier."""

    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    NSE_COMM = "NSE_COMM"
    BSE_EQ = "BSE_EQ"
    BSE_FNO = "BSE_FNO"
    MCX_COMM = "MCX_COMM"


class ProductType(StrEnum):
    """Product classification for margin and settlement."""

    CNC = "CNC"  # Cash & Carry / Delivery
    INTRADAY = "INTRADAY"  # Day trading
    MARGIN = "MARGIN"  # Derivatives / F&O margin
    MTF = "MTF"  # Margin Trading Facility


class OrderType(StrEnum):
    """Price and trigger execution type."""

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"


class OrderValidity(StrEnum):
    """Time-in-force validity."""

    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel


class OrderStatus(StrEnum):
    """Dhan order execution status."""

    TRANSIT = "TRANSIT"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PART_TRADED = "PART_TRADED"
    TRADED = "TRADED"
    EXPIRED = "EXPIRED"
    MODIFIED = "MODIFIED"
    TRIGGERED = "TRIGGERED"
    INACTIVE = "INACTIVE"
    # Terminal internal status for network uncertainty:
    PENDING_BROKER_CONFIRMATION = "PENDING_BROKER_CONFIRMATION"


class AMOTime(StrEnum):
    """After-market order timing."""

    PRE_OPEN = "PRE_OPEN"
    OPEN = "OPEN"
    OPEN_30 = "OPEN_30"
    OPEN_60 = "OPEN_60"


class LegName(StrEnum):
    """Leg name for Super / Bracket Order modification."""

    ENTRY_LEG = "ENTRY_LEG"
    STOP_LOSS_LEG = "STOP_LOSS_LEG"
    TARGET_LEG = "TARGET_LEG"
    NA = "NA"


# Default exchange freeze limits for major index derivatives (NSE)
EXCHANGE_FREEZE_LIMITS: dict[str, int] = {
    "NIFTY": 1800,
    "BANKNIFTY": 900,
    "FINNIFTY": 1800,
    "MIDCPNIFTY": 4200,
}
DEFAULT_FREEZE_LIMIT: int = 1800


def generate_correlation_id(prefix: str = "NX") -> str:
    """Generate a unique tracking correlation ID conforming to Dhan rules (max 30 chars)."""
    ts = int(time.time())
    suffix = uuid.uuid4().hex[:8]
    cid = f"{prefix}-{ts}-{suffix}"
    return cid[:30]


def calculate_order_slices(
    total_quantity: int,
    freeze_limit: int | None = None,
    lot_size: int = 1,
) -> list[int]:
    """Slice a large order into equal/valid chunks within exchange freeze limits."""
    if total_quantity <= 0:
        raise ValueError(f"Total quantity must be greater than zero, got {total_quantity}")

    max_qty = freeze_limit if (freeze_limit and freeze_limit > 0) else DEFAULT_FREEZE_LIMIT

    if total_quantity <= max_qty:
        return [total_quantity]

    slices: list[int] = []
    remaining = total_quantity
    while remaining > 0:
        chunk = min(remaining, max_qty)
        # Ensure chunk aligns with lot_size if provided
        if lot_size > 1 and chunk < remaining and chunk % lot_size != 0:
            chunk = (chunk // lot_size) * lot_size
            if chunk == 0:
                chunk = min(remaining, lot_size)
        slices.append(chunk)
        remaining -= chunk

    return slices


class DhanOrderRequest(BaseModel):
    """Request payload for POST /v2/orders."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    dhan_client_id: str | None = Field(default=None, alias="dhanClientId")
    correlation_id: str | None = Field(default=None, alias="correlationId")
    transaction_type: TransactionType = Field(alias="transactionType")
    exchange_segment: ExchangeSegment = Field(alias="exchangeSegment")
    product_type: ProductType = Field(default=ProductType.CNC, alias="productType")
    order_type: OrderType = Field(default=OrderType.LIMIT, alias="orderType")
    validity: OrderValidity = Field(default=OrderValidity.DAY, alias="validity")
    security_id: str = Field(alias="securityId")
    quantity: int = Field(gt=0, alias="quantity")
    disclosed_quantity: int = Field(default=0, ge=0, alias="disclosedQuantity")
    price: float = Field(default=0.0, ge=0.0, alias="price")
    trigger_price: float = Field(default=0.0, ge=0.0, alias="triggerPrice")
    after_market_order: bool = Field(default=False, alias="afterMarketOrder")
    amo_time: AMOTime | None = Field(default=None, alias="amoTime")

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) > 30:
                raise ValueError("correlationId must not exceed 30 characters")
            if not re.match(r"^[a-zA-Z0-9_-]+$", clean):
                raise ValueError(
                    "correlationId must contain only alphanumeric, '-', or '_' characters"
                )
            return clean
        return None

    def to_api_payload(self, client_id: str | None = None) -> dict[str, Any]:
        """Format request payload for Dhan v2 REST API."""
        payload = self.model_dump(by_alias=True, exclude_none=True)
        effective_client = self.dhan_client_id or client_id
        if effective_client:
            payload["dhanClientId"] = effective_client
        if not self.correlation_id:
            payload["correlationId"] = generate_correlation_id()
        return payload


class DhanOrderResponse(BaseModel):
    """Response payload for order placement."""

    model_config = ConfigDict(populate_by_name=True)

    order_id: str | None = Field(default=None, alias="orderId")
    order_status: OrderStatus | str | None = Field(default=None, alias="orderStatus")


class DhanOrderModifyRequest(BaseModel):
    """Request payload for PUT /v2/orders/{orderId}."""

    model_config = ConfigDict(populate_by_name=True)

    dhan_client_id: str | None = Field(default=None, alias="dhanClientId")
    order_id: str = Field(alias="orderId")
    order_type: OrderType = Field(alias="orderType")
    quantity: int | None = Field(default=None, gt=0, alias="quantity")
    price: float | None = Field(default=None, ge=0.0, alias="price")
    disclosed_quantity: int = Field(default=0, ge=0, alias="disclosedQuantity")
    trigger_price: float = Field(default=0.0, ge=0.0, alias="triggerPrice")
    validity: OrderValidity = Field(default=OrderValidity.DAY, alias="validity")
    leg_name: LegName = Field(default=LegName.NA, alias="legName")

    def to_api_payload(self, client_id: str | None = None) -> dict[str, Any]:
        payload = self.model_dump(by_alias=True, exclude_none=True)
        effective_client = self.dhan_client_id or client_id
        if effective_client:
            payload["dhanClientId"] = effective_client
        return payload


class DhanOrderCancelResponse(BaseModel):
    """Response payload for DELETE /v2/orders/{order-id}."""

    model_config = ConfigDict(populate_by_name=True)

    order_id: str | None = Field(default=None, alias="orderId")
    order_status: str | None = Field(default=None, alias="orderStatus")


class DhanSliceOrderRequest(BaseModel):
    """Request payload for POST /v2/orders/slicing."""

    model_config = ConfigDict(populate_by_name=True)

    dhan_client_id: str | None = Field(default=None, alias="dhanClientId")
    correlation_id: str | None = Field(default=None, alias="correlationId")
    transaction_type: TransactionType = Field(alias="transactionType")
    exchange_segment: ExchangeSegment = Field(alias="exchangeSegment")
    product_type: ProductType = Field(default=ProductType.CNC, alias="productType")
    order_type: OrderType = Field(default=OrderType.LIMIT, alias="orderType")
    validity: OrderValidity = Field(default=OrderValidity.DAY, alias="validity")
    security_id: str = Field(alias="securityId")
    quantity: int = Field(gt=0, alias="quantity")
    disclosed_quantity: int = Field(default=0, ge=0, alias="disclosedQuantity")
    price: float = Field(default=0.0, ge=0.0, alias="price")
    trigger_price: float = Field(default=0.0, ge=0.0, alias="triggerPrice")
    after_market_order: bool = Field(default=False, alias="afterMarketOrder")
    amo_time: AMOTime | None = Field(default=None, alias="amoTime")

    def to_api_payload(self, client_id: str | None = None) -> dict[str, Any]:
        payload = self.model_dump(by_alias=True, exclude_none=True)
        effective_client = self.dhan_client_id or client_id
        if effective_client:
            payload["dhanClientId"] = effective_client
        if not self.correlation_id:
            payload["correlationId"] = generate_correlation_id("SL")
        return payload


class DhanOrderDetail(BaseModel):
    """Detailed order state returned by GET /v2/orders/{order-id}
    or /orders/external/{correlation-id}.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    dhan_client_id: str | None = Field(default=None, alias="dhanClientId")
    order_id: str = Field(alias="orderId")
    correlation_id: str | None = Field(default=None, alias="correlationId")
    order_status: OrderStatus | str = Field(alias="orderStatus")
    transaction_type: TransactionType | str = Field(alias="transactionType")
    exchange_segment: ExchangeSegment | str = Field(alias="exchangeSegment")
    product_type: ProductType | str = Field(alias="productType")
    order_type: OrderType | str = Field(alias="orderType")
    validity: OrderValidity | str = Field(default=OrderValidity.DAY, alias="validity")
    security_id: str = Field(alias="securityId")
    quantity: int = Field(alias="quantity")
    disclosed_quantity: int = Field(default=0, alias="disclosedQuantity")
    price: float = Field(default=0.0, alias="price")
    trigger_price: float = Field(default=0.0, alias="triggerPrice")
    traded_quantity: int = Field(default=0, alias="tradedQuantity")
    average_traded_price: float = Field(default=0.0, alias="averageTradedPrice")
    create_time: str | None = Field(default=None, alias="createTime")
    update_time: str | None = Field(default=None, alias="updateTime")
    exchange_order_id: str | None = Field(default=None, alias="exchangeOrderId")
    rejection_reason: str | None = Field(default=None, alias="rejectionReason")
