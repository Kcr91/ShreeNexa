"""Risk-filtered broker gateway factory ensuring DhanBroker is never unshielded.

CRITICAL INVARIANTS:
1. No execution path reaches DhanBroker without passing pre-trade risk checks.
2. Direct instantiation of DhanBroker outside this gateway is prohibited.
"""

from __future__ import annotations

import time
from typing import Any

from app.dhan.orders import DhanOrderRequest, DhanOrderResponse
from app.engine.audit import AuditEventType, AuditLedger, get_audit_ledger
from app.engine.broker import DhanBroker
from app.engine.risk import RiskEngine, RiskFilteredBroker, RiskLimits


class AuditedRiskFilteredBroker(RiskFilteredBroker):
    """RiskFilteredBroker variant that automatically records all pre-trade evaluations,

    risk decisions, order submissions, and broker responses into the AuditLedger.
    """

    def __init__(
        self,
        broker: DhanBroker,
        risk_engine: RiskEngine | None = None,
        audit_ledger: AuditLedger | None = None,
    ) -> None:
        super().__init__(broker=broker, risk_engine=risk_engine)
        self.audit_ledger = audit_ledger or get_audit_ledger()

    def place_order(
        self,
        order: DhanOrderRequest,
        ref_ltp: float | None = None,
        current_positions_count: int = 0,
    ) -> DhanOrderResponse:
        cid = order.correlation_id or f"NX-{int(time.time())}"

        self.audit_ledger.record_event(
            AuditEventType.RISK_FILTER_EVALUATED,
            correlation_id=cid,
            payload={
                "security_id": order.security_id,
                "quantity": order.quantity,
                "price": order.price,
                "transaction_type": str(order.transaction_type),
            },
        )

        try:
            self.risk_engine.filter_order(
                order,
                ref_ltp=ref_ltp,
                current_positions_count=current_positions_count,
            )
            self.audit_ledger.record_event(
                AuditEventType.RISK_DECISION,
                correlation_id=cid,
                payload={"decision": "APPROVED"},
            )
        except Exception as exc:
            self.audit_ledger.record_event(
                AuditEventType.RISK_DECISION,
                correlation_id=cid,
                payload={"decision": "REJECTED", "reason": str(exc)},
            )
            raise

        self.audit_ledger.record_event(
            AuditEventType.ORDER_SUBMITTED,
            correlation_id=cid,
            payload={"order_request": order.model_dump(by_alias=True)},
        )

        try:
            resp = super().place_order(
                order,
                ref_ltp=ref_ltp,
                current_positions_count=current_positions_count,
            )
            self.audit_ledger.record_event(
                AuditEventType.ORDER_RESPONSE,
                correlation_id=cid,
                order_id=resp.order_id,
                payload={"order_response": resp.model_dump(by_alias=True)},
            )
            return resp
        except Exception as exc:
            self.audit_ledger.record_event(
                AuditEventType.ORDER_RESPONSE,
                correlation_id=cid,
                payload={"error": str(exc)},
            )
            raise

    def place_order_with_slicing(
        self,
        order: DhanOrderRequest,
        freeze_limit: int | None = None,
        lot_size: int = 1,
        strategy_id: str | None = None,
        ref_ltp: float | None = None,
        current_positions_count: int = 0,
    ) -> list[DhanOrderResponse]:
        """Filter order through pre-trade risk and delegate sliced execution to DhanBroker."""
        cid = order.correlation_id or f"NX-{int(time.time())}"

        self.audit_ledger.record_event(
            AuditEventType.RISK_FILTER_EVALUATED,
            correlation_id=cid,
            payload={
                "security_id": order.security_id,
                "quantity": order.quantity,
                "price": order.price,
                "transaction_type": str(order.transaction_type),
                "is_sliced": True,
            },
        )

        try:
            self.risk_engine.filter_order(
                order,
                ref_ltp=ref_ltp,
                current_positions_count=current_positions_count,
            )
            self.audit_ledger.record_event(
                AuditEventType.RISK_DECISION,
                correlation_id=cid,
                payload={"decision": "APPROVED", "is_sliced": True},
            )
        except Exception as exc:
            self.audit_ledger.record_event(
                AuditEventType.RISK_DECISION,
                correlation_id=cid,
                payload={"decision": "REJECTED", "reason": str(exc), "is_sliced": True},
            )
            raise

        self.audit_ledger.record_event(
            AuditEventType.ORDER_SUBMITTED,
            correlation_id=cid,
            payload={"order_request": order.model_dump(by_alias=True), "is_sliced": True},
        )

        try:
            responses = self.broker.place_order_with_slicing(
                request=order,
                freeze_limit=freeze_limit,
                lot_size=lot_size,
                strategy_id=strategy_id,
            )
            for resp in responses:
                self.audit_ledger.record_event(
                    AuditEventType.ORDER_RESPONSE,
                    correlation_id=cid,
                    order_id=resp.order_id,
                    payload={"order_response": resp.model_dump(by_alias=True)},
                )
            return responses
        except Exception as exc:
            self.audit_ledger.record_event(
                AuditEventType.ORDER_RESPONSE,
                correlation_id=cid,
                payload={"error": str(exc), "is_sliced": True},
            )
            raise


def get_risk_filtered_broker(
    limits: RiskLimits | None = None,
    risk_engine: RiskEngine | None = None,
    audit_ledger: AuditLedger | None = None,
    broker: DhanBroker | None = None,
    **broker_kwargs: Any,
) -> AuditedRiskFilteredBroker:
    """Construct a DhanBroker exclusively shielded by RiskFilteredBroker and AuditLedger.

    Any orders placed through the returned broker instance are unconditionally
    validated against account risk caps, velocity limits, price bands, and
    the emergency kill switch before dispatching to the live Dhan API, and
    each lifecycle boundary is immutably hashed into the audit ledger.
    """
    resolved_broker = broker or DhanBroker(**broker_kwargs)
    engine = risk_engine or RiskEngine(limits=limits)
    return AuditedRiskFilteredBroker(
        broker=resolved_broker,
        risk_engine=engine,
        audit_ledger=audit_ledger,
    )
