"""Live Order Update WebSocket client and Postback models for DhanHQ v2.5.

WebSocket endpoint: wss://api-order-update.dhan.co
Authorisation handshake: MsgCode 42
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("shreenexa.dhan.order_stream")

ORDER_UPDATE_WS_URL = "wss://api-order-update.dhan.co"


def build_order_stream_auth_message(client_id: str, access_token: str) -> dict[str, Any]:
    """Build the JSON authorization handshake message for the Dhan Order Update WebSocket."""
    return {
        "LoginReq": {
            "MsgCode": 42,
            "ClientId": client_id.strip(),
            "Token": access_token.strip(),
        },
        "UserType": "SELF",
    }


class DhanOrderUpdateData(BaseModel):
    """Payload data inside an order_alert WebSocket message."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    exchange: str | None = Field(default=None, alias="Exchange")
    segment: str | None = Field(default=None, alias="Segment")
    security_id: str | None = Field(default=None, alias="SecurityId")
    client_id: str | None = Field(default=None, alias="ClientId")
    exch_order_no: str | None = Field(default=None, alias="ExchOrderNo")
    order_no: str = Field(alias="OrderNo")
    product: str | None = Field(default=None, alias="Product")
    txn_type: str | None = Field(default=None, alias="TxnType")
    order_type: str | None = Field(default=None, alias="OrderType")
    validity: str | None = Field(default=None, alias="Validity")
    quantity: int = Field(default=0, alias="Quantity")
    traded_qty: int = Field(default=0, alias="TradedQty")
    remaining_quantity: int = Field(default=0, alias="RemainingQuantity")
    price: float = Field(default=0.0, alias="Price")
    trigger_price: float = Field(default=0.0, alias="TriggerPrice")
    traded_price: float = Field(default=0.0, alias="TradedPrice")
    avg_traded_price: float = Field(default=0.0, alias="AvgTradedPrice")
    status: str = Field(alias="Status")
    order_date_time: str | None = Field(default=None, alias="OrderDateTime")
    last_updated_time: str | None = Field(default=None, alias="LastUpdatedTime")
    correlation_id: str | None = Field(default=None, alias="CorrelationId")
    symbol: str | None = Field(default=None, alias="Symbol")
    remarks: str | None = Field(default=None, alias="Remarks")
    reason_description: str | None = Field(default=None, alias="ReasonDescription")


class DhanOrderUpdateEvent(BaseModel):
    """WebSocket packet received from wss://api-order-update.dhan.co."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_type: str = Field(alias="Type")
    data: DhanOrderUpdateData = Field(alias="Data")

    @classmethod
    def from_raw_json(cls, raw: str | bytes) -> DhanOrderUpdateEvent:
        """Parse raw WebSocket frame into typed update event."""
        doc = json.loads(raw)
        return cls.model_validate(doc)


class DhanPostbackPayload(BaseModel):
    """HTTP Postback payload structure pushed by Dhan webhook on order status changes."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    order_id: str = Field(alias="orderId")
    correlation_id: str | None = Field(default=None, alias="correlationId")
    order_status: str = Field(alias="orderStatus")
    transaction_type: str | None = Field(default=None, alias="transactionType")
    exchange_segment: str | None = Field(default=None, alias="exchangeSegment")
    product_type: str | None = Field(default=None, alias="productType")
    order_type: str | None = Field(default=None, alias="orderType")
    security_id: str | None = Field(default=None, alias="securityId")
    quantity: int = Field(default=0, alias="quantity")
    traded_quantity: int = Field(default=0, alias="tradedQuantity")
    price: float = Field(default=0.0, alias="price")
    average_price: float = Field(default=0.0, alias="averagePrice")
    update_time: str | None = Field(default=None, alias="updateTime")

    def to_unified_update(self) -> DhanOrderUpdateData:
        """Convert HTTP Postback into unified DhanOrderUpdateData."""
        return DhanOrderUpdateData(
            OrderNo=self.order_id,
            CorrelationId=self.correlation_id,
            Status=self.order_status,
            TxnType=self.transaction_type,
            Segment=self.exchange_segment,
            Product=self.product_type,
            OrderType=self.order_type,
            SecurityId=self.security_id,
            Quantity=self.quantity,
            TradedQty=self.traded_quantity,
            Price=self.price,
            AvgTradedPrice=self.average_price,
            LastUpdatedTime=self.update_time,
        )


class DhanOrderStreamHandler:
    """Dispatches raw or parsed Dhan order updates to registered consumers."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[DhanOrderUpdateData], None]] = []

    def subscribe(self, callback: Callable[[DhanOrderUpdateData], None]) -> None:
        """Register a callback for incoming order update data."""
        self._listeners.append(callback)

    def handle_raw_frame(self, raw_frame: str | bytes) -> DhanOrderUpdateData | None:
        """Parse raw incoming frame and dispatch to listeners."""
        try:
            event = DhanOrderUpdateEvent.from_raw_json(raw_frame)
            if event.event_type == "order_alert":
                self.dispatch(event.data)
                return event.data
        except Exception as exc:
            logger.warning("Failed to parse incoming order update frame: %s", exc)
        return None

    def handle_postback(self, postback: DhanPostbackPayload) -> DhanOrderUpdateData:
        """Handle incoming webhook postback."""
        update = postback.to_unified_update()
        self.dispatch(update)
        return update

    def dispatch(self, update: DhanOrderUpdateData) -> None:
        for listener in self._listeners:
            try:
                listener(update)
            except Exception as exc:
                logger.error("Error in order update listener callback: %s", exc)
