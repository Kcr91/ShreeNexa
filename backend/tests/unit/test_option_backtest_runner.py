"""Unit tests for OptionStrategyBacktestRunner, multi-leg payoffs, Greeks, and margin modeling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.backtest.options_models import (
    OptionBacktestConfig,
    OptionLegConfig,
    OptionStrategyConfig,
)
from app.backtest.options_runner import (
    OptionStrategyBacktestRunner,
    calculate_option_margin,
)
from app.engine.contracts import OrderSide
from app.marketdata.options_analytics import OptionType
from app.warehouse.schema import BarRecord


def _make_underlying_bars(
    start_dt: datetime,
    spot_prices: list[float],
) -> list[BarRecord]:
    bars: list[BarRecord] = []
    for i, p in enumerate(spot_prices):
        ts = start_dt + timedelta(days=i)
        bars.append(
            BarRecord(
                symbol="NIFTY",
                exchange_segment="NSE_FNO",
                security_id="NIFTY_IDX",
                timestamp=ts,
                open=p,
                high=p + 20.0,
                low=p - 20.0,
                close=p,
                volume=100000,
                open_interest=50000,
            )
        )
    return bars


def test_bull_call_spread_payoff_and_greeks_reconciliation() -> None:
    """Reconcile Bull Call Spread payoff bounds, Greeks directionality, and debit accounting."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=10)

    # Bull Call Spread: Buy 25000 CE, Sell 25200 CE (50 Qty)
    leg_long = OptionLegConfig(
        leg_id="NIFTY26SEP25000CE",
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        strike=25000.0,
        expiry_date=expiry,
        ratio=1,
        lot_size=50,
    )
    leg_short = OptionLegConfig(
        leg_id="NIFTY26SEP25200CE",
        option_type=OptionType.CALL,
        side=OrderSide.SELL,
        strike=25200.0,
        expiry_date=expiry,
        ratio=1,
        lot_size=50,
    )

    strategy = OptionStrategyConfig(
        name="NIFTY Bull Call Spread",
        underlying_symbol="NIFTY",
        legs=[leg_long, leg_short],
        lots=1,
        volatility=0.15,
        risk_free_rate=0.07,
    )

    config = OptionBacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=expiry,
        initial_cash=500_000.0,
    )

    # Price path moving upward past both strikes
    spot_series = [25000.0 + 30.0 * i for i in range(11)]  # Final spot = 25300.0 (> 25200)
    bars = _make_underlying_bars(t0, spot_series)

    runner = OptionStrategyBacktestRunner()
    result = runner.run(config, bars)

    # 1. Trade Entries: 2 entry fills + 2 expiry settlement fills = 4 total fills
    assert len(result.trades) == 4
    long_fill = next(
        f for f in result.trades if f.security_id == "NIFTY26SEP25000CE" and f.side == OrderSide.BUY
    )
    short_fill = next(
        f
        for f in result.trades
        if f.security_id == "NIFTY26SEP25200CE" and f.side == OrderSide.SELL
    )

    net_debit = (long_fill.price - short_fill.price) * 50
    assert net_debit > 0, "Bull Call Spread must be a net debit spread"

    # 2. Greeks Invariants at entry
    initial_greeks = result.greeks_history[0]
    assert initial_greeks.net_delta > 0, "Bull Call Spread must have positive net delta"
    assert initial_greeks.net_theta < 0, "Debit spread must have negative theta near ATM"

    # 3. Expiry Intrinsic Settlement at S_T = 25300:
    # Long 25000 CE intrinsic = 25300 - 25000 = 300.0
    # Short 25200 CE intrinsic = 25300 - 25200 = 100.0
    # Net spread intrinsic = (300 - 100) * 50 = 200 * 50 = 10,000.0
    # Max Profit = Spread Width (200 * 50 = 10,000) - Net Debit - Total Costs
    max_theoretical_profit = (25200.0 - 25000.0) * 50 - net_debit
    actual_profit = result.metrics.total_pnl

    assert actual_profit == pytest.approx(
        max_theoretical_profit - result.metrics.total_costs, abs=1.0
    )


def test_iron_condor_greeks_and_margin_reconciliation() -> None:
    """Test Iron Condor market-neutral Greeks and exchange margin requirement."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=15)

    # 4 Legs: Long Put 24600, Short Put 24800, Short Call 25200, Long Call 25400
    legs = [
        OptionLegConfig(
            leg_id="LP_24600",
            option_type=OptionType.PUT,
            side=OrderSide.BUY,
            strike=24600.0,
            expiry_date=expiry,
        ),
        OptionLegConfig(
            leg_id="SP_24800",
            option_type=OptionType.PUT,
            side=OrderSide.SELL,
            strike=24800.0,
            expiry_date=expiry,
        ),
        OptionLegConfig(
            leg_id="SC_25200",
            option_type=OptionType.CALL,
            side=OrderSide.SELL,
            strike=25200.0,
            expiry_date=expiry,
        ),
        OptionLegConfig(
            leg_id="LC_25400",
            option_type=OptionType.CALL,
            side=OrderSide.BUY,
            strike=25400.0,
            expiry_date=expiry,
        ),
    ]

    strategy = OptionStrategyConfig(
        name="NIFTY Iron Condor",
        underlying_symbol="NIFTY",
        legs=legs,
        lots=1,
        volatility=0.14,
        risk_free_rate=0.07,
    )

    config = OptionBacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=expiry,
        initial_cash=1_000_000.0,
    )

    # Flat spot path centered between short strikes (25000.0)
    spot_series = [25000.0] * 16
    bars = _make_underlying_bars(t0, spot_series)

    runner = OptionStrategyBacktestRunner()
    result = runner.run(config, bars)

    # 1. Delta Neutral and Positive Theta (harvesting decay)
    initial_greeks = result.greeks_history[0]
    assert abs(initial_greeks.net_delta) < 5.0, "Delta-neutral near ATM"
    assert initial_greeks.net_theta > 0, "Iron Condor must have positive theta"

    # 2. Margin model verification
    curr_prices = {"LP_24600": 30.0, "SP_24800": 70.0, "SC_25200": 70.0, "LC_25400": 30.0}
    margin = calculate_option_margin(legs, 25000.0, curr_prices, lots=1)
    assert margin > 0
    assert result.metrics.final_equity > 0


def test_expiration_exercise_and_assignment_settlement() -> None:
    """Test expiry settlement: ITM options exercise at intrinsic, OTM options expire worthless."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=5)

    # Long 25000 Call + Long 25500 Call
    leg1 = OptionLegConfig(
        leg_id="ITM_CALL",
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        strike=25000.0,
        expiry_date=expiry,
    )
    leg2 = OptionLegConfig(
        leg_id="OTM_CALL",
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        strike=25500.0,
        expiry_date=expiry,
    )

    strategy = OptionStrategyConfig(
        name="Expiry Test Strategy",
        underlying_symbol="NIFTY",
        legs=[leg1, leg2],
        lots=1,
    )

    config = OptionBacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=expiry,
        initial_cash=200_000.0,
    )

    # Spot ends at 25200.0 on Day 5
    spot_series = [25000.0, 25050.0, 25100.0, 25150.0, 25180.0, 25200.0]
    bars = _make_underlying_bars(t0, spot_series)

    runner = OptionStrategyBacktestRunner()
    result = runner.run(config, bars)

    # Check closing settlement fills
    settle_itm = [
        f for f in result.trades if f.security_id == "ITM_CALL" and f.side == OrderSide.SELL
    ]
    settle_otm = [
        f for f in result.trades if f.security_id == "OTM_CALL" and f.side == OrderSide.SELL
    ]

    assert len(settle_itm) == 1
    assert settle_itm[0].price == pytest.approx(200.0)  # max(0, 25200 - 25000)

    assert len(settle_otm) == 1
    assert settle_otm[0].price == 0.0  # max(0, 25200 - 25500) = 0.0
