"""Unit tests for dividend ledger, matching engine, withholding tax, and income views (F10.3).

Proof requirement: Recorded/hand fixtures; unmatched payment is reported rather than
assigned to the wrong holding.
"""

from __future__ import annotations

from datetime import date

from app.investing.dividends import (
    DividendLedger,
    DividendPaymentImportItem,
    DividendRecord,
    DividendStatus,
)
from app.investing.ledger import HoldingsLedger
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_dividend_matching_against_active_holdings() -> None:
    """Proof: Hand fixtures match accurately against active lots on record date."""
    h_ledger = HoldingsLedger()
    d_ledger = DividendLedger()
    acc = "acc_div_match"

    # Holding: 100 TCS shares acquired on 2024-01-01 @ 3500
    h_ledger.add_lot(
        account_id=acc,
        security_id="TCS",
        isin="INE467B01029",
        trading_symbol="TCS",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=3500.0,
        quantity=100,
        lot_id="tcs_lot_1",
    )

    # Dividend payment: TCS Rs 28/share, gross Rs 2800, 10% TDS (Rs 280), net Rs 2520 on 2024-05-15
    payment_items = [
        DividendPaymentImportItem(
            isin="INE467B01029",
            trading_symbol="TCS",
            payment_date=date(2024, 5, 15),
            net_amount=2520.0,
            tds_deducted=280.0,
            gross_amount=2800.0,
            rate_per_share=28.0,
            description="TCS Final Dividend FY24",
        )
    ]

    res = d_ledger.match_dividend_payments(acc, payment_items, ledger=h_ledger)
    assert len(res.matched_records) == 1
    assert len(res.unmatched_items) == 0
    assert res.total_matched_gross == 2800.0
    assert res.total_matched_net == 2520.0
    assert res.total_tds_deducted == 280.0

    matched = res.matched_records[0]
    assert matched.trading_symbol == "TCS"
    assert matched.eligible_quantity == 100
    assert matched.rate_per_share == 28.0
    assert matched.status == DividendStatus.MATCHED


def test_unmatched_payment_is_reported_never_assigned_to_wrong_holding() -> None:
    """Proof invariant: Unmatched payment is reported rather than assigned to wrong holding."""
    h_ledger = HoldingsLedger()
    d_ledger = DividendLedger()
    acc = "acc_div_unmatched"

    # Account holds only RELIANCE (100 shares)
    h_ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=2500.0,
        quantity=100,
        lot_id="rel_lot_1",
    )

    # Payment received for INFY (ISIN: INE009A01021), which is NOT held in this account
    unheld_payment = DividendPaymentImportItem(
        isin="INE009A01021",
        trading_symbol="INFY",
        payment_date=date(2024, 6, 1),
        net_amount=1500.0,
        tds_deducted=0.0,
        gross_amount=1500.0,
        description="Infosys Dividend for unheld stock",
    )

    res = d_ledger.match_dividend_payments(acc, [unheld_payment], ledger=h_ledger)

    # Critical verification: Must be isolated in unmatched_items and NEVER assigned to RELIANCE
    assert len(res.matched_records) == 0
    assert len(res.unmatched_items) == 1
    assert res.unmatched_items[0].trading_symbol == "INFY"
    assert res.unmatched_items[0].isin == "INE009A01021"

    # Ledger must remain empty of incorrect records
    all_divs = d_ledger.list_dividends(acc)
    assert len(all_divs) == 0


def test_payment_prior_to_holding_acquisition_is_unmatched() -> None:
    """Proof: Dividend dated before security acquisition date cannot claim eligible quantity."""
    h_ledger = HoldingsLedger()
    d_ledger = DividendLedger()
    acc = "acc_div_date_mismatch"

    # RELIANCE acquired on 2024-06-01
    h_ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 6, 1),
        acquisition_price=2800.0,
        quantity=50,
    )

    # Payment dated 2024-04-15 (prior to acquisition date)
    prior_payment = DividendPaymentImportItem(
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        payment_date=date(2024, 4, 15),
        net_amount=500.0,
        tds_deducted=0.0,
        gross_amount=500.0,
        description="Prior Dividend",
    )

    res = d_ledger.match_dividend_payments(acc, [prior_payment], ledger=h_ledger)
    assert len(res.matched_records) == 0
    assert len(res.unmatched_items) == 1


def test_dividend_income_view_and_yield_metrics() -> None:
    """Proof: Monthly calendar breakdown, upcoming dividends, and yield on cost are computed."""
    h_ledger = HoldingsLedger()
    d_ledger = DividendLedger()
    acc = "acc_div_income"

    # Invested capital: 100 * 2000 = 200,000
    h_ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=2000.0,
        quantity=100,
    )

    # Record two past dividends and one upcoming dividend
    d_ledger.record_dividend(
        DividendRecord(
            dividend_id="div-1",
            account_id=acc,
            security_id="RELIANCE",
            isin="INE002A01018",
            trading_symbol="RELIANCE",
            record_date=date(2024, 3, 15),
            ex_dividend_date=date(2024, 3, 15),
            payment_date=date(2024, 3, 15),
            rate_per_share=10.0,
            eligible_quantity=100,
            gross_amount=1000.0,
            tds_rate_pct=10.0,
            tds_deducted=100.0,
            net_received=900.0,
            status=DividendStatus.PAID,
        )
    )
    d_ledger.record_dividend(
        DividendRecord(
            dividend_id="div-2",
            account_id=acc,
            security_id="RELIANCE",
            isin="INE002A01018",
            trading_symbol="RELIANCE",
            record_date=date(2024, 8, 15),
            ex_dividend_date=date(2024, 8, 15),
            payment_date=date(2024, 8, 15),
            rate_per_share=15.0,
            eligible_quantity=100,
            gross_amount=1500.0,
            tds_rate_pct=10.0,
            tds_deducted=150.0,
            net_received=1350.0,
            status=DividendStatus.PAID,
        )
    )
    # Upcoming dividend in future
    d_ledger.record_dividend(
        DividendRecord(
            dividend_id="div-3",
            account_id=acc,
            security_id="RELIANCE",
            isin="INE002A01018",
            trading_symbol="RELIANCE",
            record_date=date(2025, 12, 1),
            ex_dividend_date=date(2025, 12, 1),
            payment_date=date(2025, 12, 1),
            rate_per_share=20.0,
            eligible_quantity=100,
            gross_amount=2000.0,
            tds_rate_pct=10.0,
            tds_deducted=200.0,
            net_received=1800.0,
            status=DividendStatus.DECLARED,
        )
    )

    as_of = date(2024, 12, 31)
    view = d_ledger.generate_income_view(
        acc,
        ledger=h_ledger,
        current_prices={"RELIANCE": 2500.0},
        as_of_date=as_of,
    )

    # Realized gross: 1000 + 1500 = 2500, net: 900 + 1350 = 2250, TDS: 250
    assert view.total_gross_income == 2500.0
    assert view.total_net_income == 2250.0
    assert view.total_tds == 250.0

    # Yield on cost: 2500 / 200,000 = 1.25%
    assert view.annualized_yield_on_cost_pct == 1.25
    # Current yield: 2500 / 250,000 = 1.00%
    assert view.annualized_current_yield_pct == 1.00

    # Calendar contains March and August
    assert len(view.monthly_calendar) == 2
    assert len(view.upcoming_dividends) == 1
    assert view.upcoming_dividends[0].dividend_id == "div-3"


def test_dividend_rest_api_endpoints() -> None:
    """Proof: REST API endpoints for dividend import, list, and income view function end-to-end."""
    # 1. Import dividend
    resp_imp = client.post(
        "/api/v1/investing/dividends/import",
        json={
            "account_id": "api_test_acc",
            "items": [
                {
                    "isin": "INE999A01099",
                    "trading_symbol": "UNKNOWNSTOCK",
                    "payment_date": "2024-05-01",
                    "net_amount": 750.0,
                    "tds_deducted": 0.0,
                    "gross_amount": 750.0,
                }
            ],
        },
    )
    assert resp_imp.status_code == 200
    data_imp = resp_imp.json()
    # Unknown stock must be reported in unmatched_items
    assert len(data_imp["unmatched_items"]) == 1

    # 2. List dividends
    resp_list = client.get("/api/v1/investing/dividends?account_id=api_test_acc")
    assert resp_list.status_code == 200

    # 3. Income view
    resp_view = client.get("/api/v1/investing/dividends/income-view?account_id=api_test_acc")
    assert resp_view.status_code == 200
    data_view = resp_view.json()
    assert "monthly_calendar" in data_view
    assert "annualized_yield_on_cost_pct" in data_view
