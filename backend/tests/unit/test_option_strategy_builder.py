"""Unit tests for Multi-Leg Option Strategy Builder suite."""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.analytics.greeks import OptionType
from app.analytics.strategy_builder import (
    MultiLegStrategy,
    OptionLeg,
    calculate_strategy_payoff_and_greeks,
    create_standard_strategy,
)
from app.main import app
from fastapi.testclient import TestClient

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


def test_bull_call_spread_payoff_and_extrema() -> None:
    expiry = date.today() + timedelta(days=7)
    # Buy 25000 CE @ 150, Sell 25100 CE @ 90 (Spread width = 100, Lot size = 25)
    strategy = MultiLegStrategy(
        strategy_id="bcs-1",
        name="Bull Call Spread",
        underlying="NIFTY",
        spot_price=25000.0,
        forward_price=25050.0,
        legs=[
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
                symbol="NIFTY-25100-CE",
                strike=25100.0,
                option_type=OptionType.CALL,
                action="SELL",
                quantity=1,
                lot_size=25,
                entry_price=90.0,
                iv=0.135,
                expiry_date=expiry,
            ),
        ],
    )

    res = calculate_strategy_payoff_and_greeks(strategy, target_days_forward=0)

    # Net debit = (150 - 90) * 25 = 1500 INR
    assert res.net_premium == 1500.0
    # Max Loss = -1500.0
    assert res.max_loss == -1500.0
    # Max Profit = (100 - 60) * 25 = 1000.0
    assert res.max_profit == 1000.0
    # Risk : Reward = 1000 / 1500 = 0.67
    assert res.risk_reward_ratio == 0.67
    # Breakeven = 25000 + 60 = 25060 (approx zero-crossing)
    assert len(res.breakevens) == 1
    assert 25055.0 <= res.breakevens[0] <= 25065.0
    # Bullish strategy -> positive net delta
    assert res.net_delta > 0.0


def test_long_straddle_payoff_and_unlimited_profit() -> None:
    expiry = date.today() + timedelta(days=7)
    # Buy 25000 CE @ 150, Buy 25000 PE @ 145 (Lot size = 25)
    strategy = MultiLegStrategy(
        strategy_id="straddle-1",
        name="Long Straddle",
        underlying="NIFTY",
        spot_price=25000.0,
        forward_price=25050.0,
        legs=[
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
                symbol="NIFTY-25000-PE",
                strike=25000.0,
                option_type=OptionType.PUT,
                action="BUY",
                quantity=1,
                lot_size=25,
                entry_price=145.0,
                iv=0.145,
                expiry_date=expiry,
            ),
        ],
    )

    res = calculate_strategy_payoff_and_greeks(strategy, target_days_forward=0)

    # Net debit = (150 + 145) * 25 = 7375 INR
    assert res.net_premium == 7375.0
    # Max loss = -7375.0 (at K=25000)
    assert res.max_loss == -7375.0
    # Max profit is unlimited
    assert res.max_profit is None
    # 2 Breakevens (25000 - 295 = 24705, 25000 + 295 = 25295)
    assert len(res.breakevens) == 2
    assert 24700.0 <= res.breakevens[0] <= 24710.0
    assert 25290.0 <= res.breakevens[1] <= 25300.0
    # Long Gamma and Vega, Negative Theta
    assert res.net_gamma > 0.0
    assert res.net_vega > 0.0
    assert res.net_theta < 0.0


def test_iron_condor_symmetry_and_extrema() -> None:
    expiry = date.today() + timedelta(days=7)
    strategy = create_standard_strategy(
        strategy_type="IRON_CONDOR",
        underlying="NIFTY",
        spot_price=25000.0,
        atm_strike=25000.0,
        step=50.0,
        lot_size=25,
        expiry_date=expiry,
    )

    res = calculate_strategy_payoff_and_greeks(strategy, target_days_forward=0)

    # Iron Condor is a net credit strategy (negative net premium)
    assert res.net_premium < 0.0
    # Bounded profit and bounded loss
    assert res.max_profit is not None and res.max_profit > 0.0
    assert res.max_loss is not None and res.max_loss < 0.0
    # 2 Breakevens
    assert len(res.breakevens) == 2
    # Short Vol / Positive Theta
    assert res.net_theta > 0.0
    assert res.net_vega < 0.0


def test_disabled_leg_exclusion() -> None:
    expiry = date.today() + timedelta(days=7)
    leg1 = OptionLeg(
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
        is_enabled=True,
    )
    leg2_disabled = OptionLeg(
        leg_id="leg-2",
        symbol="NIFTY-25000-PE",
        strike=25000.0,
        option_type=OptionType.PUT,
        action="BUY",
        quantity=1,
        lot_size=25,
        entry_price=145.0,
        iv=0.145,
        expiry_date=expiry,
        is_enabled=False,  # Disabled
    )

    strategy = MultiLegStrategy(
        strategy_id="toggle-1",
        name="Toggled Legs",
        underlying="NIFTY",
        spot_price=25000.0,
        forward_price=25050.0,
        legs=[leg1, leg2_disabled],
    )

    res = calculate_strategy_payoff_and_greeks(strategy)
    # Only leg 1 premium (150 * 25 = 3750)
    assert res.net_premium == 3750.0
    # Single long call has only 1 breakeven
    assert len(res.breakevens) == 1


def test_strategy_builder_rest_api() -> None:
    # 1. GET template
    resp_template = client.get(
        "/api/v1/options/strategy/template?strategy_type=IRON_CONDOR&underlying=NIFTY"
    )
    assert resp_template.status_code == 200
    strat_data = resp_template.json()
    assert strat_data["name"] == "Iron Condor"
    assert len(strat_data["legs"]) == 4

    # 2. POST analyze
    resp_analyze = client.post(
        "/api/v1/options/strategy/analyze",
        json={
            "strategy": strat_data,
            "target_days_forward": 2,
            "price_range_pct": 0.08,
            "num_points": 31,
        },
    )
    assert resp_analyze.status_code == 200
    res_data = resp_analyze.json()
    assert res_data["strategy_name"] == "Iron Condor"
    assert len(res_data["payoff_curve"]) == 31
    assert res_data["net_theta"] > 0.0
