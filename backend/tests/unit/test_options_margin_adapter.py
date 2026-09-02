"""Unit tests for Options Margin Adapter, SPAN/Exposure, Hedging Relief, and Dhan Reconciliation."""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.analytics.greeks import OptionType
from app.analytics.options_margin import calculate_basket_margin
from app.analytics.strategy_builder import OptionLeg
from app.dhan.margin_adapter import dhan_margin_adapter
from app.main import app
from fastapi.testclient import TestClient

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


def test_long_option_premium_margin() -> None:
    expiry = date.today() + timedelta(days=7)
    long_leg = OptionLeg(
        leg_id="leg-1",
        symbol="NIFTY-25000-CE",
        strike=25000.0,
        option_type=OptionType.CALL,
        action="BUY",
        quantity=1,
        lot_size=25,
        entry_price=150.0,
        iv=0.14,
        expiry_date=expiry,
    )

    res = calculate_basket_margin("NIFTY", spot_price=25000.0, legs=[long_leg])
    assert res.is_available is True
    assert res.total_span_margin == 0.0
    assert res.total_exposure_margin == 0.0
    assert res.total_premium_margin == 3750.0  # 150 * 25
    assert res.net_required_margin == 3750.0
    assert res.hedging_benefit_margin == 0.0


def test_naked_short_option_span_and_exposure() -> None:
    expiry = date.today() + timedelta(days=7)
    short_leg = OptionLeg(
        leg_id="leg-1",
        symbol="NIFTY-25000-CE",
        strike=25000.0,
        option_type=OptionType.CALL,
        action="SELL",
        quantity=1,
        lot_size=25,
        entry_price=90.0,
        iv=0.14,
        expiry_date=expiry,
    )

    res = calculate_basket_margin("NIFTY", spot_price=25000.0, legs=[short_leg])
    assert res.is_available is True
    # Contract value = 25000 * 25 = 625,000 INR
    # SPAN = 625000 * 0.11 + 2250 = 71,000 INR
    # Exposure = 625000 * 0.02 = 12,500 INR
    # Total = 83,500 INR
    assert 70000.0 <= res.total_span_margin <= 72000.0
    assert 12000.0 <= res.total_exposure_margin <= 13000.0
    assert res.net_required_margin >= 80000.0


def test_bull_call_spread_hedging_relief() -> None:
    expiry = date.today() + timedelta(days=7)
    legs = [
        OptionLeg(
            leg_id="leg-1",
            symbol="NIFTY-25000-CE",
            strike=25000.0,
            option_type=OptionType.CALL,
            action="BUY",
            quantity=1,
            lot_size=25,
            entry_price=150.0,
            iv=0.14,
            expiry_date=expiry,
        ),
        OptionLeg(
            leg_id="leg-2",
            symbol="NIFTY-25050-CE",
            strike=25050.0,
            option_type=OptionType.CALL,
            action="SELL",
            quantity=1,
            lot_size=25,
            entry_price=90.0,
            iv=0.14,
            expiry_date=expiry,
        ),
    ]

    res = calculate_basket_margin("NIFTY", spot_price=25000.0, legs=legs)
    assert res.is_available is True
    # Gross margin without hedge is ~87,000 INR
    assert res.gross_margin > 80000.0
    # Defined spread risk is 50 * 25 = 1250 INR, so net required margin is small
    assert res.net_required_margin < 15000.0
    # Hedging benefit is huge (> 60,000 INR)
    assert res.hedging_benefit_margin > 60000.0


def test_iron_condor_basket_margin_and_relief() -> None:
    expiry = date.today() + timedelta(days=7)
    legs = [
        OptionLeg(
            leg_id="leg-1",
            symbol="NIFTY-24900-PE",
            strike=24900.0,
            option_type=OptionType.PUT,
            action="BUY",
            quantity=1,
            lot_size=25,
            entry_price=15.0,
            iv=0.14,
            expiry_date=expiry,
        ),
        OptionLeg(
            leg_id="leg-2",
            symbol="NIFTY-24950-PE",
            strike=24950.0,
            option_type=OptionType.PUT,
            action="SELL",
            quantity=1,
            lot_size=25,
            entry_price=35.0,
            iv=0.14,
            expiry_date=expiry,
        ),
        OptionLeg(
            leg_id="leg-3",
            symbol="NIFTY-25050-CE",
            strike=25050.0,
            option_type=OptionType.CALL,
            action="SELL",
            quantity=1,
            lot_size=25,
            entry_price=35.0,
            iv=0.14,
            expiry_date=expiry,
        ),
        OptionLeg(
            leg_id="leg-4",
            symbol="NIFTY-25100-CE",
            strike=25100.0,
            option_type=OptionType.CALL,
            action="BUY",
            quantity=1,
            lot_size=25,
            entry_price=15.0,
            iv=0.14,
            expiry_date=expiry,
        ),
    ]

    res = calculate_basket_margin("NIFTY", spot_price=25000.0, legs=legs)
    assert res.is_available is True
    # Two short legs would unhedged require > 160,000 INR
    assert res.gross_margin > 140000.0
    # Iron condor requires < 25,000 INR
    assert res.net_required_margin < 25000.0
    assert res.hedging_benefit_margin > 120000.0


def test_dhan_margin_adapter_recorded_response_override() -> None:
    broker_mock = {
        "totalMargin": 48500.0,
        "spanMargin": 36000.0,
        "exposureMargin": 12500.0,
        "marginBenefit": 85000.0,
    }

    res = dhan_margin_adapter.calculate_basket_margin(
        underlying="NIFTY",
        spot_price=25000.0,
        legs=[],
        broker_response_override=broker_mock,
    )

    assert res.is_available is True
    assert res.net_required_margin == 48500.0
    assert res.total_span_margin == 36000.0
    assert res.total_exposure_margin == 12500.0
    assert res.hedging_benefit_margin == 85000.0
    assert res.gross_margin == 133500.0


def test_unavailable_margin_safety_rule() -> None:
    # Spot price <= 0 returns explicit is_available: False
    res_zero_spot = calculate_basket_margin("NIFTY", spot_price=0.0, legs=[])
    assert res_zero_spot.is_available is False
    assert "invalid or unavailable" in (res_zero_spot.unreliable_reason or "")

    # Malformed broker override returns explicit is_available: False
    res_malformed = dhan_margin_adapter.calculate_basket_margin(
        underlying="NIFTY",
        spot_price=25000.0,
        legs=[],
        broker_response_override={"totalMargin": "INVALID_FLOAT"},
    )
    assert res_malformed.is_available is False
    assert "Failed to parse Dhan margin response" in (res_malformed.unreliable_reason or "")


def test_margin_rest_api_endpoint() -> None:
    expiry = date.today() + timedelta(days=7)
    payload = {
        "underlying": "NIFTY",
        "spot_price": 25000.0,
        "legs": [
            {
                "leg_id": "leg-1",
                "symbol": "NIFTY-25000-CE",
                "strike": 25000.0,
                "option_type": "CALL",
                "action": "BUY",
                "quantity": 1,
                "lot_size": 25,
                "entry_price": 150.0,
                "iv": 0.14,
                "expiry_date": expiry.isoformat(),
                "is_enabled": True,
            }
        ],
    }

    resp = client.post("/api/v1/options/margin/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["underlying"] == "NIFTY"
    assert data["net_required_margin"] == 3750.0
    assert data["is_available"] is True
