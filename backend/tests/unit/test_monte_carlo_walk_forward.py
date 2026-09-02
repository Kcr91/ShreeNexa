"""Unit tests for Monte Carlo resampling and Walk-Forward analysis engines."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.backtest.models import BacktestConfig
from app.backtest.monte_carlo import (
    MonteCarloConfig,
    ResampleMethod,
    run_monte_carlo,
)
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.walk_forward import (
    WalkForwardConfig,
    generate_walk_forward_splits,
    run_walk_forward_analysis,
)
from app.strategy.ir import StrategyIR
from app.warehouse.schema import BarRecord


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


def _make_daily_bars(symbol: str, start_dt: datetime, n_bars: int) -> list[BarRecord]:
    bars: list[BarRecord] = []
    p = 100.0
    for i in range(n_bars):
        ts = start_dt + timedelta(days=i)
        p += 0.5  # Positive trend
        bars.append(
            BarRecord(
                symbol=symbol,
                exchange_segment="NSE_EQ",
                security_id=symbol,
                timestamp=ts,
                open=p - 0.2,
                high=p + 1.0,
                low=p - 1.0,
                close=p,
                volume=100000,
                open_interest=0,
            )
        )
    return bars


def test_monte_carlo_deterministic_percentile_reconciliation() -> None:
    """Verify Monte Carlo trade shuffle terminal equity invariance and DD percentiles."""
    trades = [1000.0] * 10 + [-500.0] * 5  # 10 wins (+10k), 5 losses (-2.5k) -> Net +7500.0
    initial_cash = 100_000.0

    cfg = MonteCarloConfig(
        iterations=500,
        resample_method=ResampleMethod.TRADE_SHUFFLE,
        seed=42,
    )
    res = run_monte_carlo(trades, initial_cash, cfg)

    # In Trade Shuffle, total sum of PnL is invariant across all permutations:
    assert res.terminal_equity.p5 == pytest.approx(107_500.0)
    assert res.terminal_equity.p50 == pytest.approx(107_500.0)
    assert res.terminal_equity.p95 == pytest.approx(107_500.0)

    # Max Drawdown varies depending on trade sequence ordering:
    assert 0.0 <= res.max_drawdown_pct.p5 <= res.max_drawdown_pct.p50 <= res.max_drawdown_pct.p95
    assert res.risk_of_ruin_pct == 0.0
    assert len(res.sample_paths) == 20


def test_monte_carlo_bootstrap_and_risk_of_ruin() -> None:
    """Verify Bootstrap resampling and empirical risk of ruin detection on losing series."""
    # Negative skew: small wins, big losses
    trades = [100.0] * 3 + [-2000.0] * 7
    initial_cash = 5_000.0

    cfg = MonteCarloConfig(
        iterations=500,
        resample_method=ResampleMethod.BOOTSTRAP,
        ruin_threshold_pct=0.5,  # Ruin if equity <= 2500.0
        seed=123,
    )
    res = run_monte_carlo(trades, initial_cash, cfg)

    # Negative mean return produces lower terminal equity and non-zero ruin probability
    assert res.terminal_equity.p50 < initial_cash
    assert res.risk_of_ruin_pct > 0.0


def test_walk_forward_splits_generation_rolling_and_anchored() -> None:
    """Verify exact non-overlapping date boundaries for rolling and anchored splits."""
    t0 = datetime(2026, 1, 1, 9, 15, tzinfo=UTC)
    t_end = t0 + timedelta(days=180)

    # Rolling: 90-day train, 30-day val, 30-day step
    cfg_rolling = WalkForwardConfig(
        train_window_days=90,
        validation_window_days=30,
        step_days=30,
        anchored=False,
    )
    splits_r = generate_walk_forward_splits(t0, t_end, cfg_rolling)

    assert len(splits_r) == 3
    assert splits_r[0].train_start == t0
    assert splits_r[0].train_end == t0 + timedelta(days=90)
    assert splits_r[0].validation_start == t0 + timedelta(days=90)
    assert splits_r[0].validation_end == t0 + timedelta(days=120)

    assert splits_r[1].train_start == t0 + timedelta(days=30)
    assert splits_r[1].train_end == t0 + timedelta(days=120)
    assert splits_r[1].validation_start == t0 + timedelta(days=120)
    assert splits_r[1].validation_end == t0 + timedelta(days=150)

    # Anchored: Train starts always at t0
    cfg_anchored = WalkForwardConfig(
        train_window_days=90,
        validation_window_days=30,
        step_days=30,
        anchored=True,
    )
    splits_a = generate_walk_forward_splits(t0, t_end, cfg_anchored)

    assert len(splits_a) == 3
    assert splits_a[0].train_start == t0
    assert splits_a[1].train_start == t0
    assert splits_a[2].train_start == t0


def test_walk_forward_analysis_execution_and_efficiency() -> None:
    """Test full Walk-Forward backtest execution, WFE metrics, and stitched OOS equity."""
    t0 = datetime(2026, 1, 1, 9, 15, tzinfo=UTC)
    t_end = t0 + timedelta(days=180)
    bars = _make_daily_bars("RELIANCE", t0, 185)

    strategy_ir = _make_dummy_stock_strategy()
    cfg = BacktestConfig(
        strategy=strategy_ir,
        start_date=t0,
        end_date=t_end,
        initial_cash=100_000.0,
    )

    wf_cfg = WalkForwardConfig(
        train_window_days=90,
        validation_window_days=30,
        step_days=30,
        anchored=False,
    )

    runner = StockStrategyBacktestRunner()
    result = run_walk_forward_analysis(
        runner=runner,
        config=cfg,
        wf_config=wf_cfg,
        bars_dataset={"RELIANCE": bars},
    )

    assert len(result.windows) == 3
    assert len(result.combined_out_of_sample_equity) > 0
    assert result.robustness_score_pct == 100.0  # Consistently profitable in all OOS windows
    assert result.mean_walk_forward_efficiency > 0.0
    assert result.overall_out_of_sample_metrics.final_equity > 100_000.0
