"""engine process entry point.

Owns paper/live deployment event loops, broker boundary, portfolio/risk
evaluation, orders, fills, positions, checkpoint/recovery (per ADR-0002).
None of that exists yet -- this is the F0.3 skeleton: prove the process is
independent and its liveness is durable. Real strategy execution arrives
with F3.1+.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.contracts.process_loop import main_for

if TYPE_CHECKING:
    from app.dhan.order_stream import DhanOrderStreamClient
    from app.engine.audit import AuditLedger
    from app.engine.order_reconciler import OrderReconciler

PROCESS_NAME = "engine"


def create_engine_order_stream(
    *,
    ws_url: str | None = None,
    reconciler: OrderReconciler | None = None,
    audit_ledger: AuditLedger | None = None,
) -> DhanOrderStreamClient:
    """Create and configure a DhanOrderStreamClient wired to an OrderReconciler and AuditLedger."""
    from app.dhan.order_stream import DhanOrderStreamClient
    from app.engine.audit import get_audit_ledger
    from app.engine.order_reconciler import OrderReconciler

    ledger = audit_ledger or get_audit_ledger()
    rec = reconciler or OrderReconciler(audit_ledger=ledger)
    kwargs: dict[str, Any] = {"reconciler": rec}
    if ws_url is not None:
        kwargs["ws_url"] = ws_url
    return DhanOrderStreamClient(**kwargs)


def run() -> None:
    main_for(PROCESS_NAME)


if __name__ == "__main__":
    run()
