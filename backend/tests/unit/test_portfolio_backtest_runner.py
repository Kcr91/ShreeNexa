"""Unit tests for PortfolioBacktestRunner, multi-strategy capital allocation, and rebalancing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.backtest.futures_models import (
    FuturesBacktestConfig,
    FuturesContractSpec,
    FuturesStrategyConfig,
)
from app.backtest.models import BacktestConfig
from app.backtest.options_models import (
    OptionBacktestConfig,
    OptionLegConfig,
    OptionStrategyConfig,
)
from app.backtest.portfolio_models import (
    PortfolioBacktestConfig,
    RebalanceFrequency,
    StrategyAllocation,
)
from app.backtest.portfolio_runner import PortfolioBacktestRunner
from app.engine.contracts import OrderSide
from app.marketdata.options_analytics import OptionType
from app.strategy.ir import StrategyIR
from app.warehouse.schema import BarRecord


def _make_bars(
    symbol: str,
    start_dt: datetime,
    prices: list[float],
) -> list[BarRecord]:
    bars: list[BarRecord] = []
    for i, p in enumerate(prices):
        ts = start_dt + timedelta(days=i)
        bars.append(
            BarRecord(
                symbol=symbol,
                exchange_segment="NSE_EQ",
                security_id=symbol,
                timestamp=ts,
                open=p,
                high=p + 10.0,
                low=p - 10.0,
                close=p,
                volume=100000,
                open_interest=0,
            )
        )
    return bars


def _make_dummy_stock_strategy() -> StrategyIR:
    return StrategyIR.model_validate(
        {
            "schema_version": "1.0",
            "name": "Buy and Hold",
            "kind": "stock",
            "author": "Research",
            "description": "Simple positional buy and hold",
            "asset_class": "equity",
            "horizon": "positional",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "RELIANCE"}],
            },
            "timeframe": "1d",
            "sizing": {"type": "fixed_qty", "qty": 100},
            "entries": [
                {
                    "id": "entry_1",
                    "side": "BUY",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": 0.0,
                    },
                }
            ],
            "exits": [],
        }
    )


def test_multi_strategy_capital_allocation_and_equity_aggregation() -> None:
    """Reconcile 60/40 Stock and Option strategy allocation and aggregate equity curve."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=10)

    # 1. Stock Strategy Config
    stock_ir = _make_dummy_stock_strategy()
    stock_cfg = BacktestConfig(
        strategy=stock_ir,
        start_date=t0,
        end_date=expiry,
        initial_cash=1_200_000.0,  # 60% of 2,000,000
    )

    # 2. Option Strategy Config (Bull Call Spread)
    leg1 = OptionLegConfig(
        leg_id="NIFTY26SEP25000CE",
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        strike=25000.0,
        expiry_date=expiry,
    )
    leg2 = OptionLegConfig(
        leg_id="NIFTY26SEP25200CE",
        option_type=OptionType.CALL,
        side=OrderSide.SELL,
        strike=25200.0,
        expiry_date=expiry,
    )
    opt_strat = OptionStrategyConfig(
        name="NIFTY Bull Call Spread",
        underlying_symbol="NIFTY",
        legs=[leg1, leg2],
        lots=1,
    )
    opt_cfg = OptionBacktestConfig(
        strategy=opt_strat,
        start_date=t0,
        end_date=expiry,
        initial_cash=800_000.0,  # 40% of 2,000,000
    )

    port_cfg = PortfolioBacktestConfig(
        name="Growth & Derivatives Portfolio",
        initial_cash=2_000_000.0,
        start_date=t0,
        end_date=expiry,
        allocations=[
            StrategyAllocation(
                strategy_id="strat_stock",
                strategy_name="Reliance Core",
                strategy_type="stock",
                weight=0.6,
                stock_config=stock_cfg,
            ),
            StrategyAllocation(
                strategy_id="strat_option",
                strategy_name="Nifty Spread",
                strategy_type="option",
                weight=0.4,
                option_config=opt_cfg,
            ),
        ],
    )

    # Market data
    stock_bars = _make_bars("RELIANCE", t0, [2500.0 + 10.0 * i for i in range(11)])
    opt_bars = _make_bars("NIFTY", t0, [25000.0 + 30.0 * i for i in range(11)])

    runner = PortfolioBacktestRunner()
    result = runner.run(
        config=port_cfg,
        stock_data={"RELIANCE": stock_bars},
        option_data={"NIFTY": opt_bars},
    )

    # Combined Initial & Final Equity Reconciliation
    assert len(result.contributions) == 2
    c_stock = result.contributions[0]
    c_opt = result.contributions[1]

    assert c_stock.allocated_capital == pytest.approx(1_200_000.0)
    assert c_opt.allocated_capital == pytest.approx(800_000.0)

    expected_combined_final = c_stock.final_equity + c_opt.final_equity
    assert result.combined_metrics.final_equity == pytest.approx(expected_combined_final)
    assert result.combined_metrics.total_pnl == pytest.approx(c_stock.total_pnl + c_opt.total_pnl)


def test_multi_asset_class_portfolio_attribution() -> None:
    """Test 3-way multi-asset portfolio attribution (Stock + Option + Futures)."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=10)

    stock_ir = _make_dummy_stock_strategy()
    stock_cfg = BacktestConfig(strategy=stock_ir, start_date=t0, end_date=expiry)

    leg = OptionLegConfig(
        leg_id="NIFTY26SEP25000CE",
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        strike=25000.0,
        expiry_date=expiry,
    )
    opt_strat = OptionStrategyConfig(name="NIFTY Call", underlying_symbol="NIFTY", legs=[leg])
    opt_cfg = OptionBacktestConfig(strategy=opt_strat, start_date=t0, end_date=expiry)

    fut_strat = FuturesStrategyConfig(
        name="NIFTY Future", underlying_symbol="NIFTY", lot_size=50, side=OrderSide.BUY
    )
    fut_cfg = FuturesBacktestConfig(strategy=fut_strat, start_date=t0, end_date=expiry)
    fut_spec = FuturesContractSpec(
        symbol="NIFTY26SEPFUT", underlying_symbol="NIFTY", expiry_date=expiry, lot_size=50
    )

    port_cfg = PortfolioBacktestConfig(
        name="All-Asset Portfolio",
        initial_cash=1_000_000.0,
        start_date=t0,
        end_date=expiry,
        allocations=[
            StrategyAllocation(
                strategy_id="s1",
                strategy_name="Stock",
                strategy_type="stock",
                weight=0.5,
                stock_config=stock_cfg,
            ),
            StrategyAllocation(
                strategy_id="s2",
                strategy_name="Option",
                strategy_type="option",
                weight=0.3,
                option_config=opt_cfg,
            ),
            StrategyAllocation(
                strategy_id="s3",
                strategy_name="Futures",
                strategy_type="futures",
                weight=0.2,
                futures_config=fut_cfg,
            ),
        ],
    )

    stock_bars = _make_bars("RELIANCE", t0, [2500.0] * 11)
    opt_bars = _make_bars("NIFTY", t0, [25000.0] * 11)
    fut_bars = _make_bars("NIFTY26SEPFUT", t0, [25050.0] * 11)

    runner = PortfolioBacktestRunner()
    res = runner.run(
        config=port_cfg,
        stock_data={"RELIANCE": stock_bars},
        option_data={"NIFTY": opt_bars},
        futures_contracts=[fut_spec],
        futures_data={"NIFTY26SEPFUT": fut_bars},
    )

    assert len(res.contributions) == 3
    assert res.contributions[0].initial_weight == pytest.approx(0.5)
    assert res.contributions[1].initial_weight == pytest.approx(0.3)
    assert res.contributions[2].initial_weight == pytest.approx(0.2)


def test_drift_based_rebalancing() -> None:
    """Test rebalance triggering when allocation drift exceeds tolerance threshold."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=10)

    stock_ir = _make_dummy_stock_strategy()
    stock_cfg = BacktestConfig(strategy=stock_ir, start_date=t0, end_date=expiry)

    leg = OptionLegConfig(
        leg_id="NIFTY26SEP25000CE",
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        strike=25000.0,
        expiry_date=expiry,
    )
    opt_strat = OptionStrategyConfig(name="NIFTY Call", underlying_symbol="NIFTY", legs=[leg])
    opt_cfg = OptionBacktestConfig(strategy=opt_strat, start_date=t0, end_date=expiry)

    port_cfg = PortfolioBacktestConfig(
        name="Rebalance Test Portfolio",
        initial_cash=1_000_000.0,
        start_date=t0,
        end_date=expiry,
        rebalance_freq=RebalanceFrequency.DAILY,
        rebalance_threshold_pct=0.05,
        allocations=[
            StrategyAllocation(
                strategy_id="s1",
                strategy_name="Stock",
                strategy_type="stock",
                weight=0.5,
                stock_config=stock_cfg,
            ),
            StrategyAllocation(
                strategy_id="s2",
                strategy_name="Option",
                strategy_type="option",
                weight=0.5,
                option_config=opt_cfg,
            ),
        ],
    )

    # Stock doubles in price (+100%), Option stays flat
    stock_bars = _make_bars("RELIANCE", t0, [2500.0 + 250.0 * i for i in range(11)])
    opt_bars = _make_bars("NIFTY", t0, [25000.0] * 11)

    runner = PortfolioBacktestRunner()
    res = runner.run(
        config=port_cfg,
        stock_data={"RELIANCE": stock_bars},
        option_data={"NIFTY": opt_bars},
    )

    # Rebalance event should have triggered due to drift > 5%
    assert len(res.rebalance_events) > 0
    reb = res.rebalance_events[0]
    assert reb.delta_cash != 0.0
