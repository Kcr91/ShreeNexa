"""Strategy scorecard, metric grading, horizon profiles, and deployment gates."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.backtest.models import BacktestPerformanceMetrics
from app.backtest.overfitting import OverfittingReport


class StrategyHorizon(StrEnum):
    """Trading timeframe and holding horizon profiles."""

    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITIONAL = "POSITIONAL"
    INVESTMENT = "INVESTMENT"


class MetricGrade(StrEnum):
    """Quality grade categories for strategy metrics."""

    EXCELLENT = "EXCELLENT"  # A
    GOOD = "GOOD"  # B
    ACCEPTABLE = "ACCEPTABLE"  # C
    POOR = "POOR"  # D
    REJECTED = "REJECTED"  # F


class Verdict(StrEnum):
    """Overall strategy deployment verdict."""

    DEPLOYABLE = "DEPLOYABLE"
    INVESTIGATE = "INVESTIGATE"
    REJECT = "REJECT"


class MetricScore(BaseModel):
    """Scoring breakdown for an individual performance metric."""

    model_config = ConfigDict(extra="forbid")

    metric_name: str
    value: float
    grade: MetricGrade
    weight: float
    score: float = Field(ge=0.0, le=100.0)


class DeploymentGateResult(BaseModel):
    """Evaluation result for an individual risk/deployment gate."""

    model_config = ConfigDict(extra="forbid")

    gate_name: str
    passed: bool
    threshold: float | str
    actual_value: float | str
    message: str


class GradingConfig(BaseModel):
    """Versioned threshold configuration for horizon profiles and deployment gates."""

    model_config = ConfigDict(extra="forbid")

    config_version: str = Field(default="1.0")
    min_trade_count_gate: int = Field(default=30)
    overfitting_pbo_threshold: float = Field(default=0.50)
    overfitting_dsr_threshold: float = Field(default=0.95)


class StrategyScorecard(BaseModel):
    """Complete strategy evaluation scorecard snapshot."""

    model_config = ConfigDict(extra="forbid")

    strategy_name: str
    horizon: StrategyHorizon
    config_version: str
    overall_score: float = Field(ge=0.0, le=100.0)
    overall_grade: MetricGrade
    verdict: Verdict
    metric_scores: list[MetricScore]
    flags: list[str]
    deployment_gates: list[DeploymentGateResult]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


def _grade_higher_is_better(
    val: float, thresholds: tuple[float, float, float, float]
) -> tuple[MetricGrade, float]:
    """Grade metric where higher value is better (e.g. Sharpe, Profit Factor)."""
    e, g, a, p = thresholds
    if val >= e:
        score = 90.0 + min(10.0, 10.0 * (val - e) / max(1e-6, e))
        return MetricGrade.EXCELLENT, min(100.0, score)
    elif val >= g:
        frac = (val - g) / max(1e-6, e - g)
        return MetricGrade.GOOD, 75.0 + 15.0 * frac
    elif val >= a:
        frac = (val - a) / max(1e-6, g - a)
        return MetricGrade.ACCEPTABLE, 60.0 + 15.0 * frac
    elif val >= p:
        frac = (val - p) / max(1e-6, a - p)
        return MetricGrade.POOR, 40.0 + 20.0 * frac
    else:
        frac = max(0.0, val / max(1e-6, p))
        return MetricGrade.REJECTED, 40.0 * frac


def _grade_lower_is_better(
    val: float, thresholds: tuple[float, float, float, float]
) -> tuple[MetricGrade, float]:
    """Grade metric where lower value is better (e.g. Max Drawdown %)."""
    e, g, a, p = thresholds
    if val <= e:
        return MetricGrade.EXCELLENT, 100.0
    elif val <= g:
        frac = (g - val) / max(1e-6, g - e)
        return MetricGrade.GOOD, 75.0 + 15.0 * frac
    elif val <= a:
        frac = (a - val) / max(1e-6, a - g)
        return MetricGrade.ACCEPTABLE, 60.0 + 15.0 * frac
    elif val <= p:
        frac = (p - val) / max(1e-6, p - a)
        return MetricGrade.POOR, 40.0 + 20.0 * frac
    else:
        excess = val - p
        return MetricGrade.REJECTED, max(0.0, 40.0 - 20.0 * (excess / max(1e-6, p)))


def evaluate_strategy_scorecard(
    strategy_name: str,
    metrics: BacktestPerformanceMetrics,
    horizon: StrategyHorizon = StrategyHorizon.POSITIONAL,
    config: GradingConfig | None = None,
    overfitting_report: OverfittingReport | None = None,
) -> StrategyScorecard:
    """Evaluate backtest performance metrics against horizon profile and deployment gates."""
    cfg = config or GradingConfig()
    metric_scores: list[MetricScore] = []
    flags: list[str] = []
    gates: list[DeploymentGateResult] = []

    # Horizon-specific threshold profiles (EXCELLENT, GOOD, ACCEPTABLE, POOR)
    if horizon == StrategyHorizon.INTRADAY:
        sharpe_thresh = (2.0, 1.5, 1.0, 0.5)
        dd_thresh = (3.0, 5.0, 8.0, 12.0)
        win_rate_thresh = (60.0, 50.0, 45.0, 40.0)
        pf_thresh = (2.0, 1.5, 1.2, 1.0)
        cagr_thresh = (40.0, 25.0, 15.0, 8.0)
        max_dd_gate = 10.0
        min_sharpe_gate = 1.0
    elif horizon == StrategyHorizon.SWING:
        sharpe_thresh = (1.5, 1.2, 0.8, 0.4)
        dd_thresh = (8.0, 15.0, 20.0, 25.0)
        win_rate_thresh = (55.0, 45.0, 40.0, 35.0)
        pf_thresh = (1.8, 1.4, 1.15, 1.0)
        cagr_thresh = (30.0, 20.0, 12.0, 6.0)
        max_dd_gate = 20.0
        min_sharpe_gate = 0.8
    elif horizon == StrategyHorizon.POSITIONAL:
        sharpe_thresh = (1.2, 1.0, 0.7, 0.3)
        dd_thresh = (12.0, 20.0, 28.0, 35.0)
        win_rate_thresh = (50.0, 40.0, 35.0, 30.0)
        pf_thresh = (1.6, 1.3, 1.1, 1.0)
        cagr_thresh = (25.0, 18.0, 12.0, 5.0)
        max_dd_gate = 30.0
        min_sharpe_gate = 0.6
    else:  # INVESTMENT
        sharpe_thresh = (1.0, 0.8, 0.5, 0.2)
        dd_thresh = (15.0, 25.0, 35.0, 45.0)
        win_rate_thresh = (45.0, 38.0, 32.0, 25.0)
        pf_thresh = (1.5, 1.25, 1.05, 0.95)
        cagr_thresh = (22.0, 15.0, 10.0, 4.0)
        max_dd_gate = 40.0
        min_sharpe_gate = 0.4

    # 1. Sharpe Ratio
    gr_sr, sc_sr = _grade_higher_is_better(metrics.sharpe_ratio, sharpe_thresh)
    metric_scores.append(
        MetricScore(
            metric_name="Sharpe Ratio",
            value=metrics.sharpe_ratio,
            grade=gr_sr,
            weight=0.25,
            score=sc_sr,
        )
    )

    # 2. Maximum Drawdown %
    gr_dd, sc_dd = _grade_lower_is_better(metrics.max_drawdown_pct, dd_thresh)
    metric_scores.append(
        MetricScore(
            metric_name="Max Drawdown %",
            value=metrics.max_drawdown_pct,
            grade=gr_dd,
            weight=0.25,
            score=sc_dd,
        )
    )

    # 3. Profit Factor
    gr_pf, sc_pf = _grade_higher_is_better(metrics.profit_factor, pf_thresh)
    metric_scores.append(
        MetricScore(
            metric_name="Profit Factor",
            value=metrics.profit_factor,
            grade=gr_pf,
            weight=0.20,
            score=sc_pf,
        )
    )

    # 4. Win Rate %
    gr_wr, sc_wr = _grade_higher_is_better(metrics.win_rate_pct, win_rate_thresh)
    metric_scores.append(
        MetricScore(
            metric_name="Win Rate %",
            value=metrics.win_rate_pct,
            grade=gr_wr,
            weight=0.15,
            score=sc_wr,
        )
    )

    # 5. CAGR %
    gr_cagr, sc_cagr = _grade_higher_is_better(metrics.cagr_pct, cagr_thresh)
    metric_scores.append(
        MetricScore(
            metric_name="CAGR %",
            value=metrics.cagr_pct,
            grade=gr_cagr,
            weight=0.15,
            score=sc_cagr,
        )
    )

    # Composite Overall Score (Weighted Average)
    overall_score = sum(ms.score * ms.weight for ms in metric_scores)
    if overall_score >= 85.0:
        overall_grade = MetricGrade.EXCELLENT
    elif overall_score >= 70.0:
        overall_grade = MetricGrade.GOOD
    elif overall_score >= 55.0:
        overall_grade = MetricGrade.ACCEPTABLE
    elif overall_score >= 40.0:
        overall_grade = MetricGrade.POOR
    else:
        overall_grade = MetricGrade.REJECTED

    # Evaluate Deployment Gates
    # Gate 1: Total Return / Profitability
    g1_pass = metrics.total_return_pct > 0
    gates.append(
        DeploymentGateResult(
            gate_name="Positive Total Return",
            passed=g1_pass,
            threshold=0.0,
            actual_value=metrics.total_return_pct,
            message="Strategy must achieve positive net return." if not g1_pass else "Passed.",
        )
    )

    # Gate 2: Maximum Drawdown Limit
    g2_pass = metrics.max_drawdown_pct <= max_dd_gate
    gates.append(
        DeploymentGateResult(
            gate_name="Max Drawdown Gate",
            passed=g2_pass,
            threshold=max_dd_gate,
            actual_value=metrics.max_drawdown_pct,
            message=(
                f"Max drawdown ({metrics.max_drawdown_pct:.1f}%) exceeds "
                f"horizon limit ({max_dd_gate:.1f}%)."
                if not g2_pass
                else "Passed."
            ),
        )
    )

    # Gate 3: Minimum Sharpe Ratio
    g3_pass = metrics.sharpe_ratio >= min_sharpe_gate
    gates.append(
        DeploymentGateResult(
            gate_name="Minimum Sharpe Gate",
            passed=g3_pass,
            threshold=min_sharpe_gate,
            actual_value=metrics.sharpe_ratio,
            message=(
                f"Sharpe ratio ({metrics.sharpe_ratio:.2f}) below gate ({min_sharpe_gate:.2f})."
                if not g3_pass
                else "Passed."
            ),
        )
    )

    # Gate 4: Minimum Trade Sample Size
    g4_pass = metrics.total_trades >= cfg.min_trade_count_gate
    gates.append(
        DeploymentGateResult(
            gate_name="Sample Size Gate",
            passed=g4_pass,
            threshold=cfg.min_trade_count_gate,
            actual_value=metrics.total_trades,
            message=(
                f"Trade count ({metrics.total_trades}) below minimum sample size "
                f"({cfg.min_trade_count_gate})."
                if not g4_pass
                else "Passed."
            ),
        )
    )

    # Check Flags
    if metrics.total_trades < cfg.min_trade_count_gate:
        flags.append(f"LOW_TRADE_COUNT: Only {metrics.total_trades} trades executed.")

    if metrics.max_drawdown_pct > max_dd_gate:
        flags.append(
            f"EXCESSIVE_DRAWDOWN: Drawdown reached {metrics.max_drawdown_pct:.1f}% "
            f"(> {max_dd_gate:.1f}%)."
        )

    if metrics.profit_factor < 1.1:
        flags.append(f"POOR_RISK_REWARD: Profit Factor ({metrics.profit_factor:.2f}) is marginal.")

    # Overfitting Audit
    if overfitting_report and overfitting_report.is_overfit:
        flags.append("OVERFITTING_DETECTED: Strategy failed statistical multi-testing audit.")
        for w in overfitting_report.warnings:
            flags.append(f"OVERFIT_AUDIT_WARNING: {w}")

    # Determine Verdict
    all_gates_passed = all(g.passed for g in gates)
    has_critical_failure = (not g1_pass) or (not g2_pass) or (metrics.profit_factor < 1.0)

    if has_critical_failure:
        verdict = Verdict.REJECT
    elif not all_gates_passed or (overfitting_report and overfitting_report.is_overfit) or flags:
        verdict = Verdict.INVESTIGATE
    else:
        verdict = Verdict.DEPLOYABLE

    return StrategyScorecard(
        strategy_name=strategy_name,
        horizon=horizon,
        config_version=cfg.config_version,
        overall_score=overall_score,
        overall_grade=overall_grade,
        verdict=verdict,
        metric_scores=metric_scores,
        flags=flags,
        deployment_gates=gates,
    )
