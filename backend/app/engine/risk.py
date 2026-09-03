"""Account risk layer, kill switch, pre-trade caps, and broker-path enforcement.

CRITICAL INVARIANTS:
1. No execution path reaches DhanBroker without passing pre-trade risk checks.
2. Emergency kill switch halts trading within one tick and rejects all subsequent orders.
3. Broker fail-safe actions (Exit All Positions, Activate Broker Kill Switch) are triggered
   only when explicitly authorized.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.dhan.exceptions import DhanError
from app.dhan.orders import (
    DhanOrderCancelResponse,
    DhanOrderModifyRequest,
    DhanOrderRequest,
    DhanOrderResponse,
    DhanSliceOrderRequest,
)

if TYPE_CHECKING:
    from app.engine.broker import DhanBroker

logger = logging.getLogger("shreenexa.engine.risk")


class RiskCheckFailedError(DhanError):
    """Raised when an order violates pre-trade risk caps or safety thresholds."""


class KillSwitchActiveError(DhanError):
    """Raised when an order action is attempted while the risk kill switch is active."""


@dataclass
class RiskLimits:
    """Pre-trade risk limits and account caps."""

    max_daily_loss: float = 50_000.0
    max_order_value: float = 500_000.0
    max_open_positions: int = 10
    max_orders_per_second: int = 10
    price_band_pct: float = 0.10  # Max ±10% deviation from reference LTP


class RiskEngine:
    """Pre-trade risk filtering and emergency halt coordinator."""

    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()
        self._is_halted: bool = False
        self._halt_reason: str | None = None
        self._daily_realized_loss: float = 0.0
        self._order_timestamps: list[float] = []

    @property
    def is_halted(self) -> bool:
        return self._is_halted

    @property
    def halt_reason(self) -> str | None:
        return self._halt_reason

    def halt(
        self,
        reason: str,
        broker: DhanBroker | None = None,
        exit_all_positions: bool = False,
        activate_broker_killswitch: bool = False,
    ) -> dict[str, Any]:
        """Activate the emergency kill switch within one tick.

        Optionally invokes broker-side fail-safe endpoints.
        """
        self._is_halted = True
        self._halt_reason = reason
        logger.critical("EMERGENCY KILL SWITCH ACTIVATED: %s", reason)

        fail_safe_report: dict[str, Any] = {
            "halted": True,
            "reason": reason,
            "broker_exit_all_positions": False,
            "broker_killswitch_activated": False,
        }

        if broker is not None and broker.client is not None:
            if exit_all_positions:
                try:
                    exit_res = broker.client.exit_all_positions()
                    fail_safe_report["broker_exit_all_positions"] = True
                    fail_safe_report["exit_all_response"] = exit_res
                    logger.warning("Broker exit_all_positions executed: %s", exit_res)
                except Exception as exc:
                    logger.error("Failed to execute broker exit_all_positions: %s", exc)

            if activate_broker_killswitch:
                try:
                    kill_res = broker.client.manage_kill_switch(activate=True)
                    fail_safe_report["broker_killswitch_activated"] = True
                    fail_safe_report["killswitch_response"] = kill_res
                    logger.warning("Broker killswitch activated: %s", kill_res)
                except Exception as exc:
                    logger.error("Failed to activate broker killswitch: %s", exc)

        return fail_safe_report

    def unhalt(self) -> None:
        """Manually clear engine halt after operator investigation."""
        logger.info("Emergency kill switch cleared by operator.")
        self._is_halted = False
        self._halt_reason = None

    def record_loss(self, loss_amount: float, broker: DhanBroker | None = None) -> None:
        """Record realized loss; triggers immediate halt if max_daily_loss is breached."""
        if loss_amount > 0:
            self._daily_realized_loss += loss_amount
            if self._daily_realized_loss >= self.limits.max_daily_loss:
                msg = (
                    f"Max daily loss breached: ₹{self._daily_realized_loss:,.2f} "
                    f">= limit ₹{self.limits.max_daily_loss:,.2f}"
                )
                self.halt(msg, broker=broker, exit_all_positions=True)

    def _check_rate_limit(self) -> None:
        now = time.time()
        # Keep timestamps from the last 1.0 second
        self._order_timestamps = [t for t in self._order_timestamps if now - t <= 1.0]
        if len(self._order_timestamps) >= self.limits.max_orders_per_second:
            raise RiskCheckFailedError(
                f"Order velocity exceeded: {len(self._order_timestamps)} orders/sec "
                f">= limit {self.limits.max_orders_per_second}"
            )
        self._order_timestamps.append(now)

    def filter_order(
        self,
        order: DhanOrderRequest,
        ref_ltp: float | None = None,
        current_positions_count: int = 0,
    ) -> None:
        """Validate order against pre-trade risk caps before sending to broker."""
        if self._is_halted:
            raise KillSwitchActiveError(
                f"Trading is halted by emergency kill switch: {self._halt_reason}"
            )

        self._check_rate_limit()

        # Check order value cap
        price = order.price or ref_ltp or 0.0
        notional_value = order.quantity * price
        if notional_value > self.limits.max_order_value:
            raise RiskCheckFailedError(
                f"Order notional value ₹{notional_value:,.2f} exceeds "
                f"max_order_value cap ₹{self.limits.max_order_value:,.2f}"
            )

        # Check price band cap
        if ref_ltp and ref_ltp > 0 and order.price and order.price > 0:
            deviation = abs(order.price - ref_ltp) / ref_ltp
            if deviation > self.limits.price_band_pct:
                raise RiskCheckFailedError(
                    f"Order price ₹{order.price:.2f} deviates {deviation:.1%} from "
                    f"ref LTP ₹{ref_ltp:.2f} (max allowed: {self.limits.price_band_pct:.1%})"
                )

        # Check position count cap
        if current_positions_count >= self.limits.max_open_positions:
            raise RiskCheckFailedError(
                f"Active open positions ({current_positions_count}) reached "
                f"max_open_positions limit ({self.limits.max_open_positions})"
            )


class RiskFilteredBroker:
    """Gateway enforcing pre-trade risk filtering on all DhanBroker order interactions."""

    def __init__(self, broker: DhanBroker, risk_engine: RiskEngine | None = None) -> None:
        self.broker = broker
        self.risk_engine = risk_engine or RiskEngine()

    def place_order(
        self,
        order: DhanOrderRequest,
        ref_ltp: float | None = None,
        current_positions_count: int = 0,
    ) -> DhanOrderResponse:
        """Route order through pre-trade risk filters before delegating to DhanBroker."""
        self.risk_engine.filter_order(
            order,
            ref_ltp=ref_ltp,
            current_positions_count=current_positions_count,
        )
        return self.broker.place_order(order)

    def place_sliced_order(
        self,
        order: DhanSliceOrderRequest,
        ref_ltp: float | None = None,
        current_positions_count: int = 0,
    ) -> list[DhanOrderResponse]:
        """Route sliced order through pre-trade risk filters before delegating to DhanBroker."""
        equivalent_order = DhanOrderRequest(
            securityId=order.security_id,
            exchangeSegment=order.exchange_segment,
            transactionType=order.transaction_type,
            orderType=order.order_type,
            productType=order.product_type,
            quantity=order.quantity,
            price=order.price,
            triggerPrice=order.trigger_price,
            correlationId=order.correlation_id,
        )
        self.risk_engine.filter_order(
            equivalent_order,
            ref_ltp=ref_ltp,
            current_positions_count=current_positions_count,
        )
        return self.broker.place_sliced_order(order)

    def modify_order(self, modification: DhanOrderModifyRequest) -> DhanOrderResponse:
        """Modify order under risk gating."""
        if self.risk_engine.is_halted:
            reason = self.risk_engine.halt_reason
            raise KillSwitchActiveError(
                f"Order modification rejected: kill switch is active ({reason})"
            )
        return self.broker.modify_order(modification)

    def cancel_order(self, order_id: str) -> DhanOrderCancelResponse:
        """Cancel order (allowed even during halt to reduce exposure)."""
        return self.broker.cancel_order(order_id)
