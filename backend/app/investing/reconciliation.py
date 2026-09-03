"""Reconciliation between local holdings ledger and broker (Dhan) statements."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from app.investing.ledger import HoldingsLedger, holdings_ledger
from app.investing.models import (
    DhanHoldingItem,
    HoldingReconciliationItem,
    ReconciliationReport,
)


def parse_dhan_holdings_payload(payload: str | list[dict[str, Any]]) -> list[DhanHoldingItem]:
    """Parse Dhan /holdings API response into structured DhanHoldingItem list."""
    raw_list: list[dict[str, Any]]
    if isinstance(payload, str):
        raw_list = json.loads(payload)
    else:
        raw_list = payload

    items: list[DhanHoldingItem] = []
    for entry in raw_list:
        items.append(DhanHoldingItem.model_validate(entry))
    return items


def reconcile_dhan_holdings(
        account_id: str,
        dhan_items: list[DhanHoldingItem],
        ledger: HoldingsLedger = holdings_ledger,
        cost_tolerance: float = 0.01,
) -> ReconciliationReport:
    """Reconcile local holdings ledger against a list of Dhan holdings."""
    report = ledger.generate_portfolio_report(account_id)
    local_by_sec_id = {h.security_id: h for h in report.holdings}
    broker_by_sec_id = {b.securityId: b for b in dhan_items}

    items: list[HoldingReconciliationItem] = []
    matched_count = 0
    discrepancy_count = 0

    # Process all broker items
    for sec_id, broker in broker_by_sec_id.items():
        local = local_by_sec_id.get(sec_id)
        if local is None:
            items.append(
                HoldingReconciliationItem(
                    security_id=broker.securityId,
                    isin=broker.isin,
                    trading_symbol=broker.tradingSymbol,
                    local_quantity=0,
                    broker_quantity=broker.totalQty,
                    quantity_matched=False,
                    local_average_cost=0.0,
                    broker_average_cost=round(broker.avgCostPrice, 4),
                    cost_matched=False,
                    cost_diff=round(broker.avgCostPrice, 4),
                    status="MISSING_LOCAL",
                    notes="Present in broker statement but missing in local ledger",
                )
            )
            discrepancy_count += 1
            continue

        qty_matched = local.total_quantity == broker.totalQty
        cost_diff = round(abs(local.weighted_average_cost - broker.avgCostPrice), 4)
        cost_matched = cost_diff <= cost_tolerance

        if qty_matched and cost_matched:
            status = "MATCHED"
            notes = "Quantity and weighted-average cost match"
            matched_count += 1
        elif not qty_matched:
            status = "QUANTITY_MISMATCH"
            notes = f"Quantity mismatch: local={local.total_quantity}, broker={broker.totalQty}"
            discrepancy_count += 1
        else:
            status = "COST_DRIFT"
            notes = (
                f"Cost drift > {cost_tolerance}: local={local.weighted_average_cost}, "
                f"broker={broker.avgCostPrice} (diff={cost_diff})"
            )
            discrepancy_count += 1

        items.append(
            HoldingReconciliationItem(
                security_id=sec_id,
                isin=broker.isin,
                trading_symbol=broker.tradingSymbol,
                local_quantity=local.total_quantity,
                broker_quantity=broker.totalQty,
                quantity_matched=qty_matched,
                local_average_cost=local.weighted_average_cost,
                broker_average_cost=round(broker.avgCostPrice, 4),
                cost_matched=cost_matched,
                cost_diff=cost_diff,
                status=status,
                notes=notes,
            )
        )

    # Process local items that were not reported by broker
    for sec_id, local in local_by_sec_id.items():
        if sec_id not in broker_by_sec_id:
            items.append(
                HoldingReconciliationItem(
                    security_id=local.security_id,
                    isin=local.isin,
                    trading_symbol=local.trading_symbol,
                    local_quantity=local.total_quantity,
                    broker_quantity=0,
                    quantity_matched=False,
                    local_average_cost=local.weighted_average_cost,
                    broker_average_cost=0.0,
                    cost_matched=False,
                    cost_diff=local.weighted_average_cost,
                    status="MISSING_BROKER",
                    notes="Present in local ledger but missing in broker statement",
                )
            )
            discrepancy_count += 1

    all_matched = discrepancy_count == 0

    return ReconciliationReport(
        account_id=account_id,
        reconciled_at=datetime.now(),
        all_matched=all_matched,
        total_items=len(items),
        matched_items=matched_count,
        discrepancy_count=discrepancy_count,
        items=items,
    )


def import_dhan_holdings_as_initial_lots(
    account_id: str,
    dhan_items: list[DhanHoldingItem],
    acquisition_date: date | None = None,
    ledger: HoldingsLedger = holdings_ledger,
) -> int:
    """Import Dhan holdings list as baseline initial lots in the ledger."""
    acq_date = acquisition_date or date.today()
    imported = 0
    for item in dhan_items:
        if item.totalQty > 0:
            ledger.add_lot(
                account_id=account_id,
                security_id=item.securityId,
                isin=item.isin,
                trading_symbol=item.tradingSymbol,
                acquisition_date=acq_date,
                acquisition_price=item.avgCostPrice,
                quantity=item.totalQty,
            )
            imported += 1
    return imported
