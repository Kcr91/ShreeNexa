"""Unit tests for the effective-dated Indian market cost and tax calculator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.engine.contracts import OrderSide
from app.engine.costs import ProductType, cost_calculator


def test_effective_date_schedule_resolution_pre_vs_post_oct_2024() -> None:
    """Test STT rate adjustments across the October 1, 2024 tax regime boundary."""
    # 1. Futures Sell Trade: Pre Oct 2024 (0.0125% STT) vs Post Oct 2024 (0.020% STT)
    pre_date = datetime(2024, 9, 15, 10, 0, tzinfo=UTC)
    post_date = datetime(2024, 10, 15, 10, 0, tzinfo=UTC)

    qty = 25
    price = 25000.0  # Turnover = 625,000

    cost_pre = cost_calculator.calculate_cost(
        ProductType.FUTURES, OrderSide.SELL, qty, price, pre_date
    )
    cost_post = cost_calculator.calculate_cost(
        ProductType.FUTURES, OrderSide.SELL, qty, price, post_date
    )

    assert cost_pre.schedule_id == "pre_oct_2024"
    assert cost_post.schedule_id == "post_oct_2024"

    # Pre: 625,000 * 0.000125 = 78.125
    assert cost_pre.stt_ctt == pytest.approx(78.125)
    # Post: 625,000 * 0.00020 = 125.0
    assert cost_post.stt_ctt == pytest.approx(125.0)

    # 2. Options Sell Trade: Pre Oct 2024 (0.0625% STT) vs Post Oct 2024 (0.1% STT)
    opt_qty = 50
    opt_price = 100.0  # Premium Turnover = 5,000

    opt_cost_pre = cost_calculator.calculate_cost(
        ProductType.OPTIONS, OrderSide.SELL, opt_qty, opt_price, pre_date
    )
    opt_cost_post = cost_calculator.calculate_cost(
        ProductType.OPTIONS, OrderSide.SELL, opt_qty, opt_price, post_date
    )

    # Pre: 5,000 * 0.000625 = 3.125
    assert opt_cost_pre.stt_ctt == pytest.approx(3.125)
    # Post: 5,000 * 0.0010 = 5.0
    assert opt_cost_post.stt_ctt == pytest.approx(5.0)


def test_segment_and_side_specific_cost_rules() -> None:
    """Test tax and brokerage rules across delivery, intraday, stamp duty, and GST."""
    dt = datetime(2024, 11, 1, 10, 0, tzinfo=UTC)

    # 1. Equity Delivery Buy (Stamp Duty: Yes, STT: Yes, Brokerage: ₹0)
    del_buy = cost_calculator.calculate_cost(
        ProductType.DELIVERY, OrderSide.BUY, 100, 1000.0, dt
    )
    assert del_buy.brokerage == 0.0
    assert del_buy.stamp_duty == pytest.approx(100_000 * 0.00015)  # 15.0
    assert del_buy.stt_ctt == pytest.approx(100_000 * 0.001)  # 100.0

    # 2. Equity Delivery Sell (Stamp Duty: No, STT: Yes, Brokerage: ₹0)
    del_sell = cost_calculator.calculate_cost(
        ProductType.DELIVERY, OrderSide.SELL, 100, 1000.0, dt
    )
    assert del_sell.stamp_duty == 0.0
    assert del_sell.stt_ctt == pytest.approx(100_000 * 0.001)

    # 3. Equity Intraday Buy (Stamp Duty: Yes, STT: No, Brokerage: Min(20, 0.03%))
    intra_buy = cost_calculator.calculate_cost(
        ProductType.INTRADAY, OrderSide.BUY, 10, 100.0, dt
    )  # Turnover = 1,000
    # 1,000 * 0.0003 = 0.30 (< 20.0)
    assert intra_buy.brokerage == pytest.approx(0.30)
    assert intra_buy.stt_ctt == 0.0
    assert intra_buy.stamp_duty == pytest.approx(1000 * 0.00003)

    # 4. GST Invariant (18% of Brokerage + Exchange Txn + SEBI)
    expected_gst = (del_buy.brokerage + del_buy.exchange_txn_charge + del_buy.sebi_fee) * 0.18
    assert del_buy.gst == pytest.approx(expected_gst)


def test_contract_note_fixture_reconciliation() -> None:
    """Reconcile cost calculations line-by-line against real redacted Dhan contract note fixture."""
    fixture_path = Path("backend/tests/fixtures/sample_contract_note.json")
    assert fixture_path.exists(), f"Missing fixture {fixture_path}"

    with open(fixture_path, encoding="utf-8") as f:
        contract_note = json.load(f)

    for trade in contract_note["trades"]:
        p_type = ProductType(trade["product_type"])
        side = OrderSide(trade["side"])
        qty = trade["quantity"]
        price = trade["price"]
        ts = datetime.fromisoformat(trade["timestamp"])

        calculated = cost_calculator.calculate_cost(p_type, side, qty, price, ts)
        expected = trade["expected_costs"]

        # Exact line-item assertions (within 0.001 precision)
        assert calculated.brokerage == pytest.approx(expected["brokerage"], abs=1e-3)
        assert calculated.stt_ctt == pytest.approx(expected["stt_ctt"], abs=1e-3)
        assert calculated.exchange_txn_charge == pytest.approx(
            expected["exchange_txn_charge"], abs=1e-3
        )
        assert calculated.sebi_fee == pytest.approx(expected["sebi_fee"], abs=1e-3)
        assert calculated.stamp_duty == pytest.approx(expected["stamp_duty"], abs=1e-3)
        assert calculated.gst == pytest.approx(expected["gst"], abs=1e-3)
        assert calculated.total_cost == pytest.approx(expected["total_cost"], abs=1e-3)
