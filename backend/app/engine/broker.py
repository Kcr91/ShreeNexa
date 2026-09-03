"""DhanBroker adapter and safety enforcement layer.

CRITICAL INVARIANTS:
1. Live execution disabled by default (paper trading only).
2. Live orders require explicit opt-in (SHREENEXA_ENABLE_LIVE_TRADING=true).
3. SEBI Static IP preflight validation required prior to order dispatch.
4. Timeouts during placement trigger PENDING_BROKER_CONFIRMATION; NEVER blind retry.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from app.dhan.client import DhanRestClient
from app.dhan.exceptions import DhanError, DhanTimeoutError
from app.dhan.ip import validate_static_ip_preflight
from app.dhan.orders import (
    DhanOrderCancelResponse,
    DhanOrderDetail,
    DhanOrderModifyRequest,
    DhanOrderRequest,
    DhanOrderResponse,
    DhanSliceOrderRequest,
    OrderStatus,
)

if TYPE_CHECKING:
    from app.dhan.credentials import DhanCredentials

logger = logging.getLogger("shreenexa.engine.broker")


class LiveTradingDisabledError(DhanError):
    """Raised when an attempt is made to execute real orders while live trading is disabled."""

    def __init__(
        self,
        message: str = "Live trading is disabled by default. System is in Paper Trading mode.",
    ) -> None:
        super().__init__(message)


class StaticIPMismatchError(DhanError):
    """Raised when host outbound public IP does not match whitelisted Dhan static IPs."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DhanBroker:
    """Production broker adapter for DhanHQ with safety gating and IP enforcement."""

    def __init__(
        self,
        client: DhanRestClient | None = None,
        credentials: DhanCredentials | None = None,
        *,
        enable_live_trading: bool | None = None,
        enforce_static_ip: bool = True,
        override_public_ip: str | None = None,
    ) -> None:
        self.client = client or DhanRestClient(credentials=credentials)
        self.override_public_ip = override_public_ip
        self.enforce_static_ip = enforce_static_ip

        # Hard safety invariant: live trading disabled by default unless explicitly configured
        if enable_live_trading is not None:
            self._is_live_enabled = enable_live_trading
        else:
            env_flag = os.environ.get("SHREENEXA_ENABLE_LIVE_TRADING", "false").strip().lower()
            self._is_live_enabled = env_flag in ("true", "1", "yes")

    @property
    def is_live_enabled(self) -> bool:
        """Report whether live order placement is authorized."""
        return self._is_live_enabled

    def _verify_preflight_safety(self) -> None:
        """Verify that live execution is authorized and host IP is whitelisted."""
        if not self._is_live_enabled:
            raise LiveTradingDisabledError()

        if self.enforce_static_ip:
            is_valid, msg = validate_static_ip_preflight(
                self.client, current_public_ip=self.override_public_ip
            )
            if not is_valid:
                logger.error("Dhan Static IP preflight check failed: %s", msg)
                raise StaticIPMismatchError(msg)

    def place_order(self, request: DhanOrderRequest) -> DhanOrderResponse:
        """Place an order with safety validation and timeout handling."""
        self._verify_preflight_safety()

        try:
            return self.client.place_order(request)
        except DhanTimeoutError as exc:
            # Critical invariant: NEVER blindly retry on timeout
            correlation_id = request.correlation_id or "UNKNOWN"
            logger.warning(
                "Order placement timed out for correlation_id=%s. "
                "State marked PENDING_BROKER_CONFIRMATION: %s",
                correlation_id,
                exc,
            )
            return DhanOrderResponse(
                orderId=None,
                orderStatus=OrderStatus.PENDING_BROKER_CONFIRMATION,
            )

    def place_sliced_order(self, request: DhanSliceOrderRequest) -> list[DhanOrderResponse]:
        """Place sliced order chunks across exchange freeze limits."""
        self._verify_preflight_safety()

        try:
            return self.client.place_sliced_order(request)
        except DhanTimeoutError as exc:
            correlation_id = request.correlation_id or "UNKNOWN"
            logger.warning(
                "Sliced order placement timed out for correlation_id=%s. "
                "Marking PENDING_BROKER_CONFIRMATION: %s",
                correlation_id,
                exc,
            )
            return [
                DhanOrderResponse(
                    orderId=None,
                    orderStatus=OrderStatus.PENDING_BROKER_CONFIRMATION,
                )
            ]

    def modify_order(self, modification: DhanOrderModifyRequest) -> DhanOrderResponse:
        """Modify an existing open order with safety validation."""
        self._verify_preflight_safety()
        return self.client.modify_order(modification)

    def cancel_order(self, order_id: str) -> DhanOrderCancelResponse:
        """Cancel an open order with safety validation."""
        self._verify_preflight_safety()
        return self.client.cancel_order(order_id)

    def get_order_by_id(self, order_id: str) -> DhanOrderDetail:
        """Fetch order details (read-only; authorized in all modes)."""
        return self.client.get_order_by_id(order_id)

    def get_order_by_correlation_id(self, correlation_id: str) -> DhanOrderDetail:
        """Fetch order details by correlation ID (read-only; authorized in all modes)."""
        return self.client.get_order_by_correlation_id(correlation_id)

    def reconcile_pending_order(self, correlation_id: str) -> DhanOrderDetail | None:
        """Query broker state for an order in uncertain/timeout state."""
        try:
            return self.client.get_order_by_correlation_id(correlation_id)
        except DhanError as exc:
            logger.warning("Failed to reconcile order correlation_id=%s: %s", correlation_id, exc)
            return None
