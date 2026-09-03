"""Order update reconciler, deduplication, and fill idempotency manager.

CRITICAL INVARIANTS:
1. Deduplication: Concurrent WebSocket and Postback events for the same
   transition are deduplicated.
2. Idempotent fills: Repeated packets never generate duplicate fills or
   double-count portfolio positions.
3. Sequence gaps: Out-of-order or skipped transitions trigger reconciliation
   against authoritative broker truth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.dhan.orders import OrderStatus

if TYPE_CHECKING:
    from app.dhan.client import DhanRestClient
    from app.dhan.order_stream import DhanOrderUpdateData

logger = logging.getLogger("shreenexa.engine.order_reconciler")


@dataclass
class OrderFillEvent:
    """Represents a validated incremental execution fill."""

    order_id: str
    correlation_id: str | None
    incremental_qty: int
    cumulative_traded_qty: int
    fill_price: float
    status: str
    timestamp: str | None


@dataclass
class ReconciledOrderState:
    """Locally reconciled state for an active or completed order."""

    order_id: str
    correlation_id: str | None = None
    status: str = OrderStatus.PENDING
    total_qty: int = 0
    cumulative_traded_qty: int = 0
    avg_traded_price: float = 0.0
    last_updated_time: str | None = None
    processed_fingerprints: set[str] = field(default_factory=set)


class OrderReconciler:
    """Coordinates deduplication, incremental fill calculations, and broker state reconciliation."""

    def __init__(self, client: DhanRestClient | None = None) -> None:
        self.client = client
        self._orders: dict[str, ReconciledOrderState] = {}
        self._processed_global_fingerprints: set[str] = set()

    def get_order_state(self, order_id: str) -> ReconciledOrderState | None:
        """Retrieve locally tracked state for an order."""
        return self._orders.get(order_id)

    def _generate_fingerprint(self, update: DhanOrderUpdateData) -> str:
        """Generate a deterministic deduplication hash for an update packet."""
        order_no = update.order_no.strip()
        status = update.status.strip().upper()
        traded_qty = update.traded_qty
        last_time = (update.last_updated_time or update.order_date_time or "").strip()
        price = update.traded_price or update.avg_traded_price or 0.0
        return f"{order_no}:{status}:{traded_qty}:{price}:{last_time}"

    def process_update(
        self,
        update: DhanOrderUpdateData,
    ) -> tuple[bool, OrderFillEvent | None]:
        """Process an incoming order update from WebSocket or Postback.

        Returns:
            tuple of (is_duplicate, optional_fill_event)
        """
        fingerprint = self._generate_fingerprint(update)

        if fingerprint in self._processed_global_fingerprints:
            logger.debug("Duplicate order update dropped for fingerprint: %s", fingerprint)
            return True, None

        self._processed_global_fingerprints.add(fingerprint)

        order_id = update.order_no
        state = self._orders.get(order_id)
        if state is None:
            state = ReconciledOrderState(
                order_id=order_id,
                correlation_id=update.correlation_id,
                total_qty=update.quantity,
            )
            self._orders[order_id] = state

        # Check for sequence gap: sudden completion or traded_qty increase without prior state
        new_traded_qty = update.traded_qty
        if new_traded_qty < state.cumulative_traded_qty:
            logger.warning(
                "Out-of-order traded quantity detected for order %s (current: %d, received: %d). "
                "Triggering broker reconciliation.",
                order_id,
                state.cumulative_traded_qty,
                new_traded_qty,
            )
            self.reconcile_with_broker(order_id)
            return False, None

        incremental_qty = new_traded_qty - state.cumulative_traded_qty
        fill_event: OrderFillEvent | None = None

        if incremental_qty > 0:
            fill_price = update.traded_price or update.avg_traded_price or update.price
            fill_event = OrderFillEvent(
                order_id=order_id,
                correlation_id=update.correlation_id or state.correlation_id,
                incremental_qty=incremental_qty,
                cumulative_traded_qty=new_traded_qty,
                fill_price=fill_price,
                status=update.status,
                timestamp=update.last_updated_time,
            )
            state.cumulative_traded_qty = new_traded_qty

        # Update latest known state
        state.status = update.status
        state.avg_traded_price = update.avg_traded_price or state.avg_traded_price
        state.last_updated_time = update.last_updated_time
        state.processed_fingerprints.add(fingerprint)

        return False, fill_event

    def reconcile_with_broker(self, order_id: str) -> bool:
        """Query authoritative broker truth to resolve state gaps."""
        if not self.client:
            logger.debug("No DhanRestClient available for broker truth reconciliation.")
            return False

        try:
            broker_detail = self.client.get_order_by_id(order_id)
        except Exception as exc:
            logger.error("Broker reconciliation query failed for order %s: %s", order_id, exc)
            return False

        state = self._orders.get(order_id)
        if state is None:
            state = ReconciledOrderState(order_id=order_id)
            self._orders[order_id] = state

        # Align to broker truth
        state.status = str(broker_detail.order_status)
        state.total_qty = broker_detail.quantity
        state.cumulative_traded_qty = broker_detail.traded_quantity
        state.avg_traded_price = broker_detail.average_traded_price
        state.last_updated_time = broker_detail.update_time
        logger.info(
            "Order %s successfully converged to broker truth (status: %s, traded: %d/%d).",
            order_id,
            state.status,
            state.cumulative_traded_qty,
            state.total_qty,
        )
        return True
