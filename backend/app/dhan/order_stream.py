"""Live Order Update WebSocket client and Postback models for DhanHQ v2.5.

WebSocket endpoint: wss://api-order-update.dhan.co
Authorisation handshake: MsgCode 42
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.dhan.credentials import resolve_dhan_credentials

if TYPE_CHECKING:
    from app.engine.order_reconciler import OrderReconciler

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
            if isinstance(raw_frame, bytes):
                text = raw_frame.decode("utf-8")
            else:
                text = raw_frame
            doc = json.loads(text)
            if not isinstance(doc, dict):
                return None

            # Handle Dhan auth confirmation or status responses (MsgCode 43 / LoginRsp)
            if "LoginRsp" in doc or doc.get("MsgCode") == 43:
                logger.info("Order update stream authentication confirmed: %s", doc)
                return None

            if doc.get("Type") == "order_alert" and "Data" in doc:
                event = DhanOrderUpdateEvent.model_validate(doc)
                self.dispatch(event.data)
                return event.data
            elif "OrderNo" in doc:
                data = DhanOrderUpdateData.model_validate(doc)
                self.dispatch(data)
                return data
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


class DhanOrderStreamClient:
    """Async WebSocket client transport for DhanHQ Live Order Updates (MsgCode 42).

    Maintains a persistent connection to wss://api-order-update.dhan.co, performs the MsgCode 42
    handshake, handles ping/pong keepalives, reconnects on disconnection with exponential backoff,
    and feeds incoming frames into DhanOrderStreamHandler and OrderReconciler.
    """

    def __init__(
        self,
        ws_url: str = ORDER_UPDATE_WS_URL,
        client_id: str | None = None,
        access_token: str | None = None,
        handler: DhanOrderStreamHandler | None = None,
        reconciler: OrderReconciler | None = None,
        on_update: Callable[[DhanOrderUpdateData], None] | None = None,
        ping_interval: float = 20.0,
        ping_timeout: float = 10.0,
        initial_reconnect_delay: float = 0.5,
        max_reconnect_delay: float = 30.0,
        backoff_multiplier: float = 1.5,
        max_reconnect_attempts: int | None = None,
    ) -> None:
        self.ws_url = ws_url
        self.client_id = client_id
        self.access_token = access_token
        self.handler = handler or DhanOrderStreamHandler()
        self.reconciler = reconciler
        if self.reconciler is not None:
            self.handler.subscribe(self._dispatch_to_reconciler)
        if on_update is not None:
            self.handler.subscribe(on_update)

        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.initial_reconnect_delay = initial_reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_reconnect_attempts = max_reconnect_attempts

        self._running: bool = False
        self._task: asyncio.Task[None] | None = None
        self._ws: ClientConnection | None = None
        self._is_connected: bool = False
        self._reconnect_count: int = 0
        self._processed_frames: int = 0
        self._last_received_time: float | None = None

    def _dispatch_to_reconciler(self, update: DhanOrderUpdateData) -> None:
        if self.reconciler is not None:
            try:
                self.reconciler.process_update(update)
            except Exception as exc:
                logger.error("Error dispatching update to OrderReconciler: %s", exc)

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket client is currently connected and authenticated."""
        return self._is_connected

    @property
    def is_running(self) -> bool:
        """Whether the background transport loop is active."""
        return self._running

    @property
    def reconnect_count(self) -> int:
        """Total number of reconnection attempts made."""
        return self._reconnect_count

    @property
    def processed_frames(self) -> int:
        """Total number of order update frames processed."""
        return self._processed_frames

    @property
    def last_received_time(self) -> float | None:
        """Timestamp of the most recently received frame."""
        return self._last_received_time

    def subscribe(self, callback: Callable[[DhanOrderUpdateData], None]) -> None:
        """Register an additional callback for order updates."""
        self.handler.subscribe(callback)

    def _resolve_credentials(self) -> tuple[str, str]:
        cid = self.client_id
        tok = self.access_token
        if not cid or not tok:
            creds = resolve_dhan_credentials()
            if creds:
                cid = cid or creds.client_id
                tok = tok or creds.get_token_value()
                self.client_id = cid
                self.access_token = tok
        if not cid or not tok:
            raise ValueError(
                "Dhan client_id and access_token are required for live order update stream."
            )
        return cid, tok

    async def _connect_and_listen(self) -> None:
        client_id, access_token = self._resolve_credentials()
        redacted = f"{access_token[:4]}***" if len(access_token) >= 4 else "***"
        logger.info(
            "Connecting to Dhan Order Update WebSocket at %s (client_id=%s, token=%s)",
            self.ws_url,
            client_id,
            redacted,
        )

        async with connect(
            self.ws_url,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
        ) as ws:
            self._ws = ws
            # Send MsgCode 42 auth handshake
            auth_msg = build_order_stream_auth_message(client_id, access_token)
            await ws.send(json.dumps(auth_msg))
            self._is_connected = True
            logger.info("Sent MsgCode 42 handshake to Dhan order update stream.")

            async for message in ws:
                if not self._running:
                    break
                self._last_received_time = time.time()
                self._processed_frames += 1
                self.handler.handle_raw_frame(message)

    async def connect_and_run(self) -> None:
        """Main execution loop: connects, authenticates, listens, and reconnects on error."""
        self._running = True
        delay = self.initial_reconnect_delay
        attempt = 0

        while self._running:
            if self.max_reconnect_attempts is not None and attempt >= self.max_reconnect_attempts:
                logger.info(
                    "Order update stream reached max reconnect attempts (%d). Exiting loop.",
                    self.max_reconnect_attempts,
                )
                break

            try:
                attempt += 1
                await self._connect_and_listen()
                if not self._running:
                    break
                # If connection closed without exception while still running, reconnect
                self._is_connected = False
                self._reconnect_count += 1
                logger.warning(
                    "Order update stream closed by server. Reconnecting in %.2fs (attempt %d)...",
                    delay,
                    self._reconnect_count,
                )
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
                delay = min(self.max_reconnect_delay, delay * self.backoff_multiplier)
            except asyncio.CancelledError:
                logger.info("Order update stream transport cancelled.")
                break
            except (ConnectionClosed, WebSocketException, OSError, Exception) as exc:
                if not self._running:
                    break
                self._is_connected = False
                self._reconnect_count += 1
                logger.warning(
                    "Order update stream disconnected: %s. Reconnecting in %.2fs (attempt %d)...",
                    exc,
                    delay,
                    self._reconnect_count,
                )
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
                delay = min(self.max_reconnect_delay, delay * self.backoff_multiplier)
            finally:
                self._is_connected = False

    def start(self) -> asyncio.Task[None]:
        """Start the order stream client as a background asyncio Task."""
        if self._task is None or self._task.done():
            self._running = True
            self._task = asyncio.create_task(self.connect_and_run())
        return self._task

    async def stop(self) -> None:
        """Stop the order stream client and cleanly terminate active connections."""
        self._running = False
        self._is_connected = False
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
