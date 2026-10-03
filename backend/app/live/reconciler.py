"""Live Position Reconciliation Engine between Local DB and Dhan API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class BrokerPositionReconciler:
    """Reconciles internal DB open positions with Dhan broker API positions."""

    def reconcile_positions(
        self,
        local_positions: list[dict[str, Any]],
        broker_positions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Perform 1-to-1 position reconciliation and identify drifts or mismatches."""
        now = datetime.now(UTC)
        drift_details: list[dict[str, Any]] = []

        local_by_symbol = {pos["symbol"]: pos for pos in local_positions}
        broker_by_symbol = {pos["symbol"]: pos for pos in broker_positions}

        # 1. Check local positions against broker
        for sym, l_pos in local_by_symbol.items():
            if sym not in broker_by_symbol:
                drift_details.append(
                    {
                        "symbol": sym,
                        "issue_type": "MISSING_ON_BROKER",
                        "local_qty": l_pos.get("quantity", 0),
                        "broker_qty": 0,
                        "description": f"Position {sym} exists locally but not on Dhan broker.",
                    }
                )
            else:
                b_pos = broker_by_symbol[sym]
                if l_pos.get("quantity") != b_pos.get("quantity"):
                    drift_details.append(
                        {
                            "symbol": sym,
                            "issue_type": "QUANTITY_MISMATCH",
                            "local_qty": l_pos.get("quantity", 0),
                            "broker_qty": b_pos.get("quantity", 0),
                            "description": (
                                f"Quantity mismatch on {sym}: local={l_pos.get('quantity')}, "
                                f"broker={b_pos.get('quantity')}."
                            ),
                        }
                    )

        # 2. Check broker positions against local
        for sym, b_pos in broker_by_symbol.items():
            if sym not in local_by_symbol:
                drift_details.append(
                    {
                        "symbol": sym,
                        "issue_type": "UNTRACKED_ON_LOCAL",
                        "local_qty": 0,
                        "broker_qty": b_pos.get("quantity", 0),
                        "description": (
                            f"Position {sym} exists on Dhan broker but was not recorded locally "
                            "(manual broker order detected)."
                        ),
                    }
                )

        mismatch_detected = len(drift_details) > 0
        status = "WARNING_MISMATCH" if mismatch_detected else "SYNCHRONIZED"
        msg = (
            f"⚠️ Found {len(drift_details)} position discrepancies with Dhan broker."
            if mismatch_detected
            else "✅ All positions are 100% synchronized with Dhan broker."
        )

        return {
            "reconciled_at": now,
            "broker_positions_count": len(broker_positions),
            "local_positions_count": len(local_positions),
            "mismatch_detected": mismatch_detected,
            "drift_details": drift_details,
            "status": status,
            "message": msg,
        }
