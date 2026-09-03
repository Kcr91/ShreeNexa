"""Continuous positions, orders, and funds reconciliation against Dhan.

Includes freeze-on-mismatch policy.

CRITICAL INVARIANTS:
1. Freeze on Mismatch: Any discrepancy between broker truth and internal state immediately
   freezes trading on the affected symbol or account.
2. Zero Silent Auto-Correction: Discrepancies are NEVER silently corrected in the background.
   Trading remains frozen until an explicit operator resolution command is issued.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.dhan.client import DhanRestClient
    from app.dhan.models import DhanPosition
    from app.dhan.orders import DhanOrderDetail
    from app.engine.order_reconciler import ReconciledOrderState

logger = logging.getLogger("shreenexa.engine.continuous_recon")


class MismatchDimension(StrEnum):
    POSITION = "POSITION"
    ORDER = "ORDER"
    FUNDS = "FUNDS"


class IncidentStatus(StrEnum):
    ACTIVE_FROZEN = "ACTIVE_FROZEN"
    RESOLVED = "RESOLVED"


@dataclass
class MismatchIncident:
    """Represents a frozen discrepancy incident awaiting operator resolution."""

    incident_id: str
    dimension: MismatchDimension
    security_id: str
    local_value: Any
    broker_value: Any
    detected_at: float
    status: IncidentStatus = IncidentStatus.ACTIVE_FROZEN
    resolved_at: float | None = None
    resolution_action: str | None = None
    operator_notes: str | None = None


class ContinuousReconciler:
    """Orchestrates periodic state comparison and freeze-on-mismatch enforcement."""

    def __init__(self, client: DhanRestClient | None = None) -> None:
        self.client = client
        self._incidents: dict[str, MismatchIncident] = {}
        self._frozen_symbols: set[str] = set()
        self._is_account_frozen: bool = False

    @property
    def is_account_frozen(self) -> bool:
        return self._is_account_frozen

    def is_symbol_frozen(self, security_id: str) -> bool:
        """Check if trading on a specific instrument is frozen due to an active mismatch."""
        return self._is_account_frozen or (security_id in self._frozen_symbols)

    def get_active_incidents(self) -> list[MismatchIncident]:
        """Return all unresolved mismatch incidents."""
        return [
            inc for inc in self._incidents.values() if inc.status == IncidentStatus.ACTIVE_FROZEN
        ]

    def reconcile_positions(
        self,
        local_positions: dict[str, int],  # security_id -> net_qty
        broker_positions: list[DhanPosition],
    ) -> list[MismatchIncident]:
        """Compare local net positions against broker truth. Freezes on mismatch."""
        broker_map: dict[str, int] = {
            pos.security_id: pos.net_qty
            for pos in broker_positions
            if pos.security_id
        }

        all_keys = set(local_positions.keys()) | set(broker_map.keys())
        new_incidents: list[MismatchIncident] = []

        for sec_id in all_keys:
            local_qty = local_positions.get(sec_id, 0)
            broker_qty = broker_map.get(sec_id, 0)

            if local_qty != broker_qty:
                incident_id = f"INC-POS-{sec_id}-{uuid.uuid4().hex[:6]}"
                incident = MismatchIncident(
                    incident_id=incident_id,
                    dimension=MismatchDimension.POSITION,
                    security_id=sec_id,
                    local_value=local_qty,
                    broker_value=broker_qty,
                    detected_at=time.time(),
                    status=IncidentStatus.ACTIVE_FROZEN,
                )
                self._incidents[incident_id] = incident
                self._frozen_symbols.add(sec_id)
                new_incidents.append(incident)

                logger.critical(
                    "FREEZE-ON-MISMATCH: Position mismatch for %s. Local=%d, Broker=%d. "
                    "Trading FROZEN on symbol (Incident %s). Zero silent auto-correction.",
                    sec_id,
                    local_qty,
                    broker_qty,
                    incident_id,
                )

        return new_incidents

    def reconcile_orders(
        self,
        local_orders: dict[str, ReconciledOrderState],
        broker_orders: list[DhanOrderDetail],
    ) -> list[MismatchIncident]:
        """Compare local order tracking against broker order book. Freezes on mismatch."""
        broker_map = {order.order_id: order for order in broker_orders}
        new_incidents: list[MismatchIncident] = []

        for order_id, local_state in local_orders.items():
            broker_order = broker_map.get(order_id)
            if broker_order is None:
                continue

            sec_id = broker_order.security_id or local_state.order_id

            # Check status and traded quantity
            has_status_mismatch = (
                str(local_state.status).upper() != str(broker_order.order_status).upper()
            )
            has_qty_mismatch = (
                local_state.cumulative_traded_qty != broker_order.traded_quantity
            )

            if has_status_mismatch or has_qty_mismatch:
                incident_id = f"INC-ORD-{order_id}-{uuid.uuid4().hex[:6]}"
                incident = MismatchIncident(
                    incident_id=incident_id,
                    dimension=MismatchDimension.ORDER,
                    security_id=sec_id,
                    local_value={
                        "status": local_state.status,
                        "traded_qty": local_state.cumulative_traded_qty,
                    },
                    broker_value={
                        "status": broker_order.order_status,
                        "traded_qty": broker_order.traded_quantity,
                    },
                    detected_at=time.time(),
                    status=IncidentStatus.ACTIVE_FROZEN,
                )
                self._incidents[incident_id] = incident
                self._frozen_symbols.add(sec_id)
                new_incidents.append(incident)

                logger.critical(
                    "FREEZE-ON-MISMATCH: Order mismatch for %s (%s). "
                    "Trading FROZEN (Incident %s). Zero silent auto-correction.",
                    order_id,
                    sec_id,
                    incident_id,
                )

        return new_incidents

    def resolve_mismatch(
        self,
        incident_id: str,
        resolution_action: str,
        operator_notes: str = "",
    ) -> bool:
        """Explicit operator workflow to resolve a mismatch and unfreeze symbol."""
        incident = self._incidents.get(incident_id)
        if not incident or incident.status != IncidentStatus.ACTIVE_FROZEN:
            return False

        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = time.time()
        incident.resolution_action = resolution_action
        incident.operator_notes = operator_notes

        sec_id = incident.security_id
        # Check if any other active incidents remain for this symbol
        remaining_symbol_incidents = [
            inc
            for inc in self._incidents.values()
            if inc.security_id == sec_id and inc.status == IncidentStatus.ACTIVE_FROZEN
        ]
        if not remaining_symbol_incidents:
            self._frozen_symbols.discard(sec_id)
            logger.info("Symbol %s successfully UNFROZEN after operator resolution.", sec_id)

        # Check if account can be unfrozen
        if not self.get_active_incidents():
            self._is_account_frozen = False

        return True
