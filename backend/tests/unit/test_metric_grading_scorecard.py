"""Unit tests for strategy scorecard, metric grading, horizon profiles, and deployment gates."""

from __future__ import annotations

from app.backtest.grading import (
    MetricGrade,
    StrategyHorizon,
    Verdict,
    _grade_higher_is_better,
    _grade_lower_is_better,
    evaluate_strategy_scorecard,
)
from app.backtest.models import BacktestPerformanceMetrics
from app.backtest.overfitting import DeflatedSharpeResult, OverfittingReport


def _sample_metrics(
    total_trades: int = 50,
    win_rate_pct: float = 60.0,
    sharpe_ratio: float = 2.2,
    max_drawdown_pct: float = 4.0,
    profit_factor: float = 2.5,
    cagr_pct: float = 35.0,
    total_return_pct: float = 45.0,
) -> BacktestPerformanceMetrics:
    """Create a sample BacktestPerformanceMetrics fixture."""
    winning = int(total_trades * win_rate_pct / 100.0)
    losing = total_trades - winning
    return BacktestPerformanceMetrics(
        initial_capital=100000.0,
        final_equity=100000.0 * (1.0 + total_return_pct / 100.0),
        total_return_pct=total_return_pct,
        cagr_pct=cagr_pct,
        total_pnl=100000.0 * (total_return_pct / 100.0),
        total_costs=500.0,
        realized_pnl=100000.0 * (total_return_pct / 100.0),
        unrealized_pnl=0.0,
        max_drawdown_pct=max_drawdown_pct,
        max_drawdown_value=100000.0 * (max_drawdown_pct / 100.0),
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=3.0,
        calmar_ratio=8.0,
        total_trades=total_trades,
        winning_trades=winning,
        losing_trades=losing,
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
    )


def test_contiguous_boundary_properties() -> None:
    """Verify smooth monotonic score scaling across grade boundaries."""
    thresholds = (2.0, 1.5, 1.0, 0.5)

    # Test values around each boundary
    g1, s1 = _grade_higher_is_better(2.5, thresholds)
    assert g1 == MetricGrade.EXCELLENT
    assert 90.0 <= s1 <= 100.0

    g2, s2 = _grade_higher_is_better(1.8, thresholds)
    assert g2 == MetricGrade.GOOD
    assert 75.0 <= s2 < 90.0

    g3, s3 = _grade_higher_is_better(1.2, thresholds)
    assert g3 == MetricGrade.ACCEPTABLE
    assert 60.0 <= s3 < 75.0

    g4, s4 = _grade_higher_is_better(0.7, thresholds)
    assert g4 == MetricGrade.POOR
    assert 40.0 <= s4 < 60.0

    g5, s5 = _grade_higher_is_better(0.2, thresholds)
    assert g5 == MetricGrade.REJECTED
    assert s5 < 40.0


def test_lower_is_better_grading() -> None:
    """Verify drawdown grading correctly assigns higher scores to smaller drawdowns."""
    thresholds = (3.0, 5.0, 8.0, 12.0)

    g1, s1 = _grade_lower_is_better(2.0, thresholds)
    assert g1 == MetricGrade.EXCELLENT
    assert s1 == 100.0

    g2, s2 = _grade_lower_is_better(4.0, thresholds)
    assert g2 == MetricGrade.GOOD
    assert 75.0 <= s2 < 100.0

    g3, s3 = _grade_lower_is_better(6.5, thresholds)
    assert g3 == MetricGrade.ACCEPTABLE
    assert 60.0 <= s3 < 75.0

    g4, s4 = _grade_lower_is_better(10.0, thresholds)
    assert g4 == MetricGrade.POOR
    assert 40.0 <= s4 < 60.0

    g5, s5 = _grade_lower_is_better(15.0, thresholds)
    assert g5 == MetricGrade.REJECTED
    assert s5 < 40.0


def test_horizon_profiles_different_standards() -> None:
    """Verify Intraday vs Positional profiles apply appropriate standards."""
    # Strategy with 7.0% Max Drawdown and 1.1 Sharpe
    metrics = _sample_metrics(
        sharpe_ratio=1.1,
        max_drawdown_pct=7.0,
        win_rate_pct=48.0,
        profit_factor=1.3,
    )

    # In INTRADAY, 7.0% Drawdown is ACCEPTABLE (exceeds 5.0% GOOD threshold)
    card_intraday = evaluate_strategy_scorecard("TestIntraday", metrics, StrategyHorizon.INTRADAY)
    dd_score_intra = next(
        ms for ms in card_intraday.metric_scores if ms.metric_name == "Max Drawdown %"
    )
    assert dd_score_intra.grade == MetricGrade.ACCEPTABLE

    # In POSITIONAL, 7.0% Drawdown is EXCELLENT (well below 12.0% EXCELLENT threshold)
    card_pos = evaluate_strategy_scorecard("TestPositional", metrics, StrategyHorizon.POSITIONAL)
    dd_score_pos = next(
        ms for ms in card_pos.metric_scores if ms.metric_name == "Max Drawdown %"
    )
    assert dd_score_pos.grade == MetricGrade.EXCELLENT
    assert card_pos.overall_score > card_intraday.overall_score


def test_overfit_verdict_transitions_to_investigate() -> None:
    """Verify strategy with excellent backtest switches to INVESTIGATE upon overfitting."""
    metrics = _sample_metrics(
        total_trades=100,
        sharpe_ratio=2.5,
        max_drawdown_pct=3.0,
        profit_factor=2.8,
    )

    # 1. Without overfitting: DEPLOYABLE
    card_clean = evaluate_strategy_scorecard("AlphaStrategy", metrics, StrategyHorizon.INTRADAY)
    assert card_clean.verdict == Verdict.DEPLOYABLE
    assert card_clean.overall_grade == MetricGrade.EXCELLENT
    assert not card_clean.flags

    # 2. With overfitting audit warning: INVESTIGATE
    overfit_rep = OverfittingReport(
        dsr=DeflatedSharpeResult(
            estimated_sharpe=2.5,
            expected_max_sharpe=1.8,
            psr=0.99,
            deflated_sharpe_ratio=0.82,  # < 0.95
            skewness=0.0,
            kurtosis=3.0,
            trials_count=200,
            observations_count=500,
        ),
        is_overfit=True,
        warnings=["Deflated Sharpe Ratio (82.00%) is below 95% confidence threshold."],
    )

    card_overfit = evaluate_strategy_scorecard(
        "AlphaStrategy",
        metrics,
        StrategyHorizon.INTRADAY,
        overfitting_report=overfit_rep,
    )
    assert card_overfit.verdict == Verdict.INVESTIGATE
    assert any("OVERFITTING_DETECTED" in flag for flag in card_overfit.flags)


def test_failed_risk_gates_triggers_rejection() -> None:
    """Verify failing critical drawdown or profitability gates causes REJECT verdict."""
    # Negative return and 35% drawdown in Intraday
    bad_metrics = _sample_metrics(
        total_trades=15,  # Low trade count
        total_return_pct=-10.0,
        profit_factor=0.8,
        max_drawdown_pct=35.0,
        sharpe_ratio=-0.5,
    )

    card = evaluate_strategy_scorecard("BrokenStrategy", bad_metrics, StrategyHorizon.INTRADAY)
    assert card.verdict == Verdict.REJECT
    assert card.overall_grade == MetricGrade.REJECTED

    failing_gates = [g for g in card.deployment_gates if not g.passed]
    assert len(failing_gates) >= 3
    assert any(g.gate_name == "Positive Total Return" for g in failing_gates)
    assert any(g.gate_name == "Max Drawdown Gate" for g in failing_gates)
    assert any(g.gate_name == "Sample Size Gate" for g in failing_gates)
