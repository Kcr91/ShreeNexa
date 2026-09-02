"""Unit tests for combined portfolio equity, drawdown curves, risk caps, and risk attribution."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.portfolio import (
    PortfolioAllocationConfig,
    PortfolioOrchestrator,
    PortfolioRiskCaps,
    RebalanceFrequency,
    StrategyAllocationSpec,
    check_risk_caps,
    compute_drawdown_curve,
    compute_marginal_risk_return_attribution,
    generate_portfolio_analytics_report,
)


def _make_orchestrator() -> PortfolioOrchestrator:
    config = PortfolioAllocationConfig(
        portfolio_name="All Weather India",
        total_initial_capital=2_000_000.0,
        allocations=[
            StrategyAllocationSpec(
                strategy_id="strat_equity",
                strategy_name="Equity Momentum",
                weight=0.60,
                strategy_type="stock",
            ),
            StrategyAllocationSpec(
                strategy_id="strat_options",
                strategy_name="NIFTY Delta Neutral",
                weight=0.40,
                strategy_type="option",
            ),
        ],
        rebalance_freq=RebalanceFrequency.NEVER,
        rebalance_threshold_pct=0.10,
    )
    orch = PortfolioOrchestrator(config)
    # Day 1: Trades
    orch.step_day(
        as_of_date=date(2026, 9, 1),
        prices={"RELIANCE": 2500.0, "NIFTY_CE": 120.0},
        trades={
            "strat_equity": [{"symbol": "RELIANCE", "qty": 200, "price": 2500.0, "fee": 50.0}],
            "strat_options": [{"symbol": "NIFTY_CE", "qty": 100, "price": 120.0, "fee": 30.0}],
        },
    )
    # Day 2: Market moves up
    orch.step_day(
        as_of_date=date(2026, 9, 2),
        prices={"RELIANCE": 2600.0, "NIFTY_CE": 150.0},
    )
    # Day 3: Market pulls back
    orch.step_day(
        as_of_date=date(2026, 9, 3),
        prices={"RELIANCE": 2450.0, "NIFTY_CE": 90.0},
    )
    # Day 4: Strong recovery
    orch.step_day(
        as_of_date=date(2026, 9, 4),
        prices={"RELIANCE": 2700.0, "NIFTY_CE": 180.0},
    )
    return orch


def test_combined_equity_reconciles_to_individual_strategy_fixtures() -> None:
    orch = _make_orchestrator()
    summary = orch.build_summary()

    for snap in summary.daily_snapshots:
        # Sum of cash across books strictly matches snapshot total_cash
        expected_cash = sum(orch.books[s_id].cash for s_id in orch.books)
        assert abs(snap.total_cash - expected_cash) <= 1e-2

        # Sum of equities across books strictly matches snapshot total_equity
        expected_equity = sum(snap.strategy_equities.values())
        assert abs(snap.total_equity - expected_equity) <= 1e-2


def test_drawdown_curve_and_high_water_mark_calculation() -> None:
    equity_series = [
        (datetime(2026, 9, 1, tzinfo=UTC), 100_000.0),
        (datetime(2026, 9, 2, tzinfo=UTC), 110_000.0),  # new HWM = 110k
        (datetime(2026, 9, 3, tzinfo=UTC), 105_000.0),  # DD = -5k (-4.545%)
        (datetime(2026, 9, 4, tzinfo=UTC), 95_000.0),  # DD = -15k (-13.636%) -> Max DD
        (datetime(2026, 9, 5, tzinfo=UTC), 100_000.0),  # DD = -10k (-9.091%)
        (datetime(2026, 9, 6, tzinfo=UTC), 120_000.0),  # new HWM = 120k (recovered)
    ]

    points, max_dd_pct, max_dd_days = compute_drawdown_curve(equity_series)

    assert len(points) == 6
    assert all(p.drawdown_abs <= 0.0 for p in points)
    assert all(p.drawdown_pct <= 0.0 for p in points)

    # Spot checks
    assert points[1].high_water_mark == 110_000.0
    assert points[1].drawdown_abs == 0.0

    assert points[3].high_water_mark == 110_000.0
    assert points[3].drawdown_abs == -15_000.0
    assert abs(points[3].drawdown_pct - (-15_000.0 / 110_000.0)) <= 1e-5

    # Max drawdown verification
    assert abs(max_dd_pct - (-15_000.0 / 110_000.0)) <= 1e-5
    assert max_dd_days >= 3  # Sept 2 to Sept 6


def test_aggregate_risk_caps_breaches() -> None:
    orch = _make_orchestrator()
    summary = orch.build_summary()

    # Very strict caps to trigger breaches
    strict_caps = PortfolioRiskCaps(
        max_drawdown_pct_cap=0.01,  # 1% max DD
        max_strategy_concentration_pct=0.55,  # 55% max allocation
    )

    breaches = check_risk_caps(
        snapshots=summary.daily_snapshots,
        max_drawdown_pct=-0.05,  # 5% drawdown
        caps=strict_caps,
    )

    assert len(breaches) > 0
    assert any("Max Drawdown breach" in b for b in breaches)
    assert any("Concentration breach" in b for b in breaches)


def test_marginal_risk_and_return_attribution_euler_sum() -> None:
    strat_returns = {
        "strat_A": [0.01, -0.02, 0.015, 0.03, -0.01],
        "strat_B": [0.005, 0.01, -0.005, 0.012, 0.008],
    }
    target_weights = {"strat_A": 0.60, "strat_B": 0.40}
    actual_weights = {"strat_A": 0.61, "strat_B": 0.39}
    names = {"strat_A": "Strategy A", "strat_B": "Strategy B"}
    initial_alloc = {"strat_A": 600_000.0, "strat_B": 400_000.0}
    final_eq = {"strat_A": 630_000.0, "strat_B": 415_000.0}

    attributions = compute_marginal_risk_return_attribution(
        strategy_returns=strat_returns,
        target_weights=target_weights,
        actual_weights=actual_weights,
        strategy_names=names,
        initial_allocations=initial_alloc,
        final_equities=final_eq,
        total_initial_capital=1_000_000.0,
    )

    assert len(attributions) == 2

    # Euler risk decomposition theorem: sum(PCR_i) == 1.0 (100%)
    total_pcr = sum(attr.percentage_risk_contribution for attr in attributions)
    assert abs(total_pcr - 1.0) <= 1e-4

    # Return contributions sum to total portfolio return:
    # Strat A PnL = 30k (3.0% of total cap), Strat B PnL = 15k (1.5% of total cap)
    # Total portfolio return = 4.5%
    total_ret_contrib = sum(attr.return_contribution_pct for attr in attributions)
    assert abs(total_ret_contrib - 4.5) <= 1e-4


def test_full_portfolio_analytics_report_generation() -> None:
    orch = _make_orchestrator()
    report = generate_portfolio_analytics_report(orch)

    assert report.portfolio_name == "All Weather India"
    assert report.initial_capital == 2_000_000.0
    assert report.final_capital > 0.0
    assert len(report.drawdown_curve) == len(orch.daily_snapshots)
    assert len(report.attributions) == 2
    assert report.max_drawdown_pct <= 0.0
