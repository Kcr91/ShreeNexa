"""Unit tests for long-term holdings ledger, lots, and Dhan reconciliation (F10.1).

Verifies FIFO lot depletion, STCG/LTCG classification, corporate action neutrality,
and reconciliation against redacted Dhan account holdings fixtures.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from app.investing.ledger import holdings_ledger
from app.investing.models import (
    CapitalGainsCategory,
    CorporateAction,
    CorporateActionType,
)
from app.investing.reconciliation import (
    import_dhan_holdings_as_initial_lots,
    parse_dhan_holdings_payload,
    reconcile_dhan_holdings,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "dhan_holdings_fixture.json"


@pytest.fixture(autouse=True)
def clean_ledger() -> None:
    holdings_ledger.clear()


def test_fifo_lot_depletion_and_tax_classification() -> None:
    """Proof: Disposals deplete lots in FIFO order, categorizing STCG (<365d) and LTCG (>=365d)."""
    acc = "acc-fifo-test"
    sec_id = "2885"
    isin = "INE002A01018"
    symbol = "RELIANCE-EQ"

    # Lot 1: 100 shares @ 2000 on 2025-01-01 (held > 365 days by 2026-02-01)
    holdings_ledger.add_lot(acc, sec_id, isin, symbol, date(2025, 1, 1), 2000.0, 100)
    # Lot 2: 50 shares @ 2200 on 2025-08-01 (held ~184 days by 2026-02-01)
    holdings_ledger.add_lot(acc, sec_id, isin, symbol, date(2025, 8, 1), 2200.0, 50)
    # Lot 3: 50 shares @ 2500 on 2026-01-15 (held 17 days by 2026-02-01)
    holdings_ledger.add_lot(acc, sec_id, isin, symbol, date(2026, 1, 15), 2500.0, 50)

    # Initial check
    initial_summary = holdings_ledger.get_holding_summary(acc, sec_id)
    assert initial_summary is not None
    assert initial_summary.total_quantity == 200
    # Weighted avg = (100*2000 + 50*2200 + 50*2500) / 200 = 435000 / 200 = 2175.0
    assert initial_summary.weighted_average_cost == 2175.0

    # Sell 120 shares @ 2600 on 2026-02-01 with ₹150 transaction costs
    # Lot 1 depleted completely: 100 shares -> LTCG = (2600 - 2000) * 100 = 60,000
    # Lot 2 depleted partially: 20 shares -> STCG = (2600 - 2200) * 20 = 8,000
    disposal = holdings_ledger.record_disposal(
        account_id=acc,
        security_id=sec_id,
        disposal_date=date(2026, 2, 1),
        disposal_price=2600.0,
        quantity=120,
        transaction_costs=150.0,
    )

    assert disposal.quantity == 120
    assert disposal.gross_realized_pnl == 68_000.0
    assert disposal.net_realized_pnl == 67_850.0
    assert disposal.ltcg_pnl == 60_000.0
    assert disposal.stcg_pnl == 8_000.0
    assert len(disposal.allocations) == 2

    alloc1, alloc2 = disposal.allocations[0], disposal.allocations[1]
    assert alloc1.depleted_quantity == 100
    assert alloc1.gains_category == CapitalGainsCategory.LTCG
    assert alloc2.depleted_quantity == 20
    assert alloc2.gains_category == CapitalGainsCategory.STCG

    # Remaining lots: 30 shares of lot 2 (2200) + 50 shares of lot 3 (2500) = 80 shares
    post_summary = holdings_ledger.get_holding_summary(acc, sec_id)
    assert post_summary is not None
    assert post_summary.total_quantity == 80
    expected_post_cost = round((30 * 2200.0 + 50 * 2500.0) / 80, 4)
    assert post_summary.weighted_average_cost == expected_post_cost


def test_corporate_actions_do_not_masquerade_as_returns() -> None:
    """Proof: Splits and bonus issues preserve invested capital without inflating returns."""
    acc = "acc-corp-act"
    sec_id = "1594"
    isin = "INE009A01021"
    symbol = "INFY-EQ"

    # Buy 100 shares @ 1600 = 160,000 invested capital
    holdings_ledger.add_lot(acc, sec_id, isin, symbol, date(2025, 1, 1), 1600.0, 100)
    pre = holdings_ledger.get_holding_summary(acc, sec_id, current_market_price=1600.0)
    assert pre is not None
    assert pre.total_invested_capital == 160_000.0

    # 1. 2:1 Stock Split (numerator=2, denominator=1)
    split_action = CorporateAction(
        action_id="act-split-1",
        action_type=CorporateActionType.STOCK_SPLIT,
        security_id=sec_id,
        isin=isin,
        effective_date=date(2025, 6, 1),
        ratio_numerator=2,
        ratio_denominator=1,
    )
    holdings_ledger.apply_corporate_action(acc, split_action)

    post_split = holdings_ledger.get_holding_summary(acc, sec_id, current_market_price=800.0)
    assert post_split is not None
    assert post_split.total_quantity == 200
    assert post_split.weighted_average_cost == 800.0
    # Invariant: Total invested capital remains precisely 160,000
    assert post_split.total_invested_capital == 160_000.0
    # With market price halved, unrealized PnL is exactly 0.0 (no masqueraded return)
    assert post_split.unrealized_pnl == 0.0

    # 2. 1:1 Bonus Issue on top of the 200 shares
    bonus_action = CorporateAction(
        action_id="act-bonus-1",
        action_type=CorporateActionType.BONUS_ISSUE,
        security_id=sec_id,
        isin=isin,
        effective_date=date(2025, 9, 1),
        ratio_numerator=1,
        ratio_denominator=1,
    )
    holdings_ledger.apply_corporate_action(acc, bonus_action)

    post_bonus = holdings_ledger.get_holding_summary(acc, sec_id, current_market_price=400.0)
    assert post_bonus is not None
    assert post_bonus.total_quantity == 400
    # Blended average cost = 160,000 / 400 = 400.0
    assert post_bonus.weighted_average_cost == 400.0
    assert post_bonus.total_invested_capital == 160_000.0
    assert post_bonus.unrealized_pnl == 0.0


def test_reconciliation_against_redacted_dhan_fixture() -> None:
    """Proof: Local holdings reconcile cleanly against the redacted Dhan account fixture."""
    acc = "acc-dhan-reconcile"
    fixture_content = FIXTURE_PATH.read_text(encoding="utf-8")
    dhan_items = parse_dhan_holdings_payload(fixture_content)
    assert len(dhan_items) == 3

    # Import fixture items into local ledger
    imported_count = import_dhan_holdings_as_initial_lots(acc, dhan_items, date(2026, 1, 1))
    assert imported_count == 3

    # Reconcile cleanly
    report = reconcile_dhan_holdings(acc, dhan_items)
    assert report.all_matched is True
    assert report.total_items == 3
    assert report.matched_items == 3
    assert report.discrepancy_count == 0

    # Introduce quantity mismatch in security 2885 (Reliance)
    holdings_ledger.record_disposal(acc, "2885", date(2026, 2, 1), 2500.0, 10)
    report_mismatch = reconcile_dhan_holdings(acc, dhan_items)
    assert report_mismatch.all_matched is False
    assert report_mismatch.discrepancy_count == 1

    item_rel = next(it for it in report_mismatch.items if it.security_id == "2885")
    assert item_rel.status == "QUANTITY_MISMATCH"
    assert item_rel.local_quantity == 90
    assert item_rel.broker_quantity == 100


def test_investing_rest_api_end_to_end() -> None:
    """Proof: REST endpoints for lots, disposals, corporate actions, and Dhan reconciliation."""
    acc = "acc-rest-test"

    # 1. POST /api/v1/investing/lots
    lot_resp = client.post(
        "/api/v1/investing/lots",
        json={
            "account_id": acc,
            "security_id": "11536",
            "isin": "INE467B01029",
            "trading_symbol": "TCS-EQ",
            "acquisition_date": "2025-03-10",
            "acquisition_price": 3800.0,
            "quantity": 50,
        },
    )
    assert lot_resp.status_code == 200
    lot_data = lot_resp.json()
    assert lot_data["quantity"] == 50
    assert lot_data["acquisition_price"] == 3800.0

    # 2. GET /api/v1/investing/holdings
    h_resp = client.get(f"/api/v1/investing/holdings?account_id={acc}")
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert len(h_data["holdings"]) == 1
    assert h_data["total_invested"] == 190_000.0

    # 3. POST /api/v1/investing/disposals
    disp_resp = client.post(
        "/api/v1/investing/disposals",
        json={
            "account_id": acc,
            "security_id": "11536",
            "disposal_date": "2026-03-15",
            "disposal_price": 4200.0,
            "quantity": 20,
            "transaction_costs": 100.0,
        },
    )
    assert disp_resp.status_code == 200
    disp_data = disp_resp.json()
    assert disp_data["quantity"] == 20
    assert disp_data["ltcg_pnl"] == 8000.0  # (4200 - 3800) * 20 = 8000 (held > 365 days)
    assert disp_data["net_realized_pnl"] == 7900.0

    # 4. POST /api/v1/investing/reconcile-dhan
    rec_resp = client.post(
        "/api/v1/investing/reconcile-dhan",
        json={
            "account_id": acc,
            "dhan_holdings": [
                {
                    "exchange": "NSE",
                    "tradingSymbol": "TCS-EQ",
                    "securityId": "11536",
                    "isin": "INE467B01029",
                    "totalQty": 30,  # 50 - 20 = 30 remaining
                    "dpQty": 30,
                    "t1Qty": 0,
                    "availableQty": 30,
                    "collateralQty": 0,
                    "avgCostPrice": 3800.0,
                }
            ],
        },
    )
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert rec_data["all_matched"] is True
    assert rec_data["matched_items"] == 1
