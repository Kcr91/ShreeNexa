"""Unit and invariant tests for multi-strategy portfolio allocation and orchestration."""

from __future__ import annotations

from datetime import date

import pytest
from app.portfolio import (
    AllocationValidationError,
    PortfolioAllocationConfig,
    PortfolioOrchestrator,
    RebalanceFrequency,
    StrategyAllocationSpec,
    split_initial_capital,
    validate_allocation_config,
)
from pydantic import ValidationError


def _sample_config(
    weights: list[float] | None = None,
    total_cap: float = 1_000_000.0,
    rebalance_freq: RebalanceFrequency = RebalanceFrequency.DRIFT_ONLY,
    threshold: float = 0.05,
) -> PortfolioAllocationConfig:
    weights = weights or [0.60, 0.40]
    specs = [
        StrategyAllocationSpec(
            strategy_id=f"strat_{i}",
            strategy_name=f"Strategy {i}",
            weight=w,
            strategy_type="stock" if i == 0 else "option",
        )
        for i, w in enumerate(weights)
    ]
    return PortfolioAllocationConfig(
        portfolio_name="Alpha Core Balanced",
        total_initial_capital=total_cap,
        allocations=specs,
        rebalance_freq=rebalance_freq,
        rebalance_threshold_pct=threshold,
    )


def test_allocation_invariant_validates_weights_and_splits() -> None:
    config = _sample_config([0.50, 0.30, 0.20], total_cap=1_000_000.0)
    validate_allocation_config(config)

    splits = split_initial_capital(config)
    assert splits["strat_0"] == 500_000.0
    assert splits["strat_1"] == 300_000.0
    assert splits["strat_2"] == 200_000.0
    assert sum(splits.values()) == 1_000_000.0


def test_allocation_invariant_rejects_non_unity_weights() -> None:
    # Sum is 0.90 != 1.0
    config = _sample_config([0.50, 0.40])
    with pytest.raises(AllocationValidationError) as exc_info:
        validate_allocation_config(config)

    assert "must sum to 1.0" in str(exc_info.value)


def test_allocation_invariant_rejects_invalid_weights() -> None:
    # Negative weight rejected by Pydantic gt=0
    with pytest.raises(ValidationError):
        StrategyAllocationSpec(
            strategy_id="s1",
            strategy_name="S1",
            weight=-0.2,
            strategy_type="stock",
        )


def test_isolated_strategy_books_prevent_cross_contamination() -> None:
    config = _sample_config([0.60, 0.40], total_cap=1_000_000.0)
    orchestrator = PortfolioOrchestrator(config)

    assert orchestrator.books["strat_0"].cash == 600_000.0
    assert orchestrator.books["strat_1"].cash == 400_000.0
    assert orchestrator.total_portfolio_cash == 1_000_000.0

    # Execute trade strictly in strat_0
    trades = {
        "strat_0": [{"symbol": "RELIANCE", "qty": 100, "price": 2500.0, "fee": 50.0}]
    }
    prices = {"RELIANCE": 2500.0, "TCS": 3500.0}

    orchestrator.step_day(
        as_of_date=date(2026, 9, 1),
        prices=prices,
        trades=trades,
    )

    # strat_0 spent 250,000 + 50 = 250,050
    assert orchestrator.books["strat_0"].cash == 600_000.0 - 250_050.0
    assert orchestrator.books["strat_0"].positions["RELIANCE"].quantity == 100

    # strat_1 cash and positions remain completely unaffected
    assert orchestrator.books["strat_1"].cash == 400_000.0
    assert len(orchestrator.books["strat_1"].positions) == 0

    # Total portfolio cash equals sum of book cash amounts
    assert orchestrator.total_portfolio_cash == (
        orchestrator.books["strat_0"].cash + orchestrator.books["strat_1"].cash
    )


def test_deterministic_rebalancing_with_zero_sum_transfers() -> None:
    config = _sample_config([0.50, 0.50], total_cap=1_000_000.0, threshold=0.05)
    orchestrator = PortfolioOrchestrator(config)

    # Day 1: strat_0 buys 200 RELIANCE at 2500 (500,000 cost), strat_1 stays in cash
    trades = {
        "strat_0": [{"symbol": "RELIANCE", "qty": 200, "price": 2500.0, "fee": 0.0}]
    }
    prices_day1 = {"RELIANCE": 2500.0}
    orchestrator.step_day(date(2026, 9, 1), prices=prices_day1, trades=trades)

    # Day 2: RELIANCE rallies to 3500 (+40%)
    # strat_0 equity = 0 cash + 200 * 3500 = 700,000 (700,000 / 1,200,000 = 58.33%)
    # strat_1 equity = 500,000 cash (500,000 / 1,200,000 = 41.67%)
    # Drift = 8.33% > threshold (5%) -> Triggers rebalance
    prices_day2 = {"RELIANCE": 3500.0}
    orchestrator.step_day(date(2026, 9, 2), prices=prices_day2)

    assert len(orchestrator.rebalance_history) == 2  # one transfer record per strategy

    t0 = orchestrator.rebalance_history[0]
    t1 = orchestrator.rebalance_history[1]

    # Target capital for each is 1,200,000 * 0.50 = 600,000
    assert t0.target_capital == 600_000.0
    assert t1.target_capital == 600_000.0

    # Net capital transferred must conserve funds: delta_0 + delta_1 == 0
    assert abs(t0.delta_cash + t1.delta_cash) <= 1e-3

    # strat_0 harvested 100,000 (-100,000), strat_1 infused 100,000 (+100,000)
    assert t0.delta_cash == -100_000.0
    assert t1.delta_cash == 100_000.0

    # strat_1 cash increased from 500,000 to 600,000
    assert orchestrator.books["strat_1"].cash == 600_000.0


def test_simulation_replay_determinism() -> None:
    def _run() -> float:
        cfg = _sample_config([0.60, 0.40], total_cap=1_000_000.0)
        orch = PortfolioOrchestrator(cfg)
        trades = {
            "strat_0": [{"symbol": "INFY", "qty": 100, "price": 1500.0, "fee": 20.0}],
            "strat_1": [{"symbol": "TCS", "qty": 50, "price": 3000.0, "fee": 25.0}],
        }
        orch.step_day(date(2026, 9, 1), prices={"INFY": 1500.0, "TCS": 3000.0}, trades=trades)
        orch.step_day(date(2026, 9, 2), prices={"INFY": 1550.0, "TCS": 3100.0})
        orch.step_day(date(2026, 9, 3), prices={"INFY": 1520.0, "TCS": 3150.0})
        summary = orch.build_summary()
        return summary.final_capital

    run1 = _run()
    run2 = _run()
    assert run1 == run2
