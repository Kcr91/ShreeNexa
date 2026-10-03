"""Go / No-Go Readiness Score Engine & Drift Analytics Calculator."""

from __future__ import annotations

from typing import Any, Literal

from app.paper.paper_models import (
    DriftAnalysisResponse,
    QuickCompareMetricItem,
    QuickCompareResponse,
    ReadinessScoreBreakdown,
)


def compute_readiness_score(
    paper_pnl: float,
    expected_pnl: float,
    paper_win_rate: float,
    backtest_win_rate: float,
    paper_drawdown_pct: float,
    backtest_drawdown_pct: float,
    total_trades: int,
) -> ReadinessScoreBreakdown:
    """Compute 0-100% Go/No-Go Readiness Score with 4-factor weighting."""
    # 1. PnL Match Score (Weight 40%)
    if expected_pnl != 0:
        pnl_diff_ratio = abs(paper_pnl - expected_pnl) / max(100.0, abs(expected_pnl))
        pnl_match = max(0.0, 100.0 * (1.0 - min(1.0, pnl_diff_ratio)))
    else:
        pnl_match = 80.0

    # 2. Win Rate Stability Score (Weight 30%)
    wr_drift = abs(paper_win_rate - backtest_win_rate)
    win_rate_score = max(0.0, 100.0 - (wr_drift * 2.0))

    # 3. Drawdown Safety Score (Weight 20%)
    if paper_drawdown_pct <= backtest_drawdown_pct:
        dd_score = 100.0
    else:
        excess_dd = paper_drawdown_pct - backtest_drawdown_pct
        dd_score = max(0.0, 100.0 - (excess_dd * 15.0))

    # 4. Sample Size Weight Score (Weight 10%) - Reaches 100% at 20+ trades
    sample_score = min(100.0, total_trades * 5.0)

    # Weighted Total Score
    total_score = (
        (0.40 * pnl_match) + (0.30 * win_rate_score) + (0.20 * dd_score) + (0.10 * sample_score)
    )
    total_score = round(min(100.0, max(0.0, total_score)), 2)

    verdict: Literal["READY_FOR_LIVE", "NEEDS_FURTHER_VALIDATION"] = (
        "READY_FOR_LIVE" if total_score >= 80.0 else "NEEDS_FURTHER_VALIDATION"
    )
    msg = (
        "✅ Strategy is performing stably within historical parameters. Ready for live deployment."
        if verdict == "READY_FOR_LIVE"
        else (
            "⚠️ Paper performance is drifting or sample size is too low (<20 trades). "
            "Needs further validation."
        )
    )

    return ReadinessScoreBreakdown(
        pnl_match_score=round(pnl_match, 2),
        win_rate_stability_score=round(win_rate_score, 2),
        drawdown_safety_score=round(dd_score, 2),
        sample_size_weight_score=round(sample_score, 2),
        total_readiness_score=total_score,
        verdict=verdict,
        verdict_message=msg,
    )


def generate_quick_comparison(
    strategy_id: int,
    strategy_name: str,
    session_id: int,
    paper_pnl: float,
    backtest_pnl: float,
    paper_win_rate: float,
    backtest_win_rate: float,
    paper_dd: float,
    backtest_dd: float,
    paper_trades_count: int,
    backtest_trades_count: int,
    open_positions: list[Any],
    shadow_leaderboard: list[dict[str, Any]],
) -> QuickCompareResponse:
    """Build Quick Comparison Card data structure."""
    pnl_status: Literal["ON_TRACK", "WARNING"] = (
        "ON_TRACK" if abs(paper_pnl - backtest_pnl) <= 2000.0 else "WARNING"
    )
    wr_status: Literal["STABLE", "DIVERGENT"] = (
        "STABLE" if abs(paper_win_rate - backtest_win_rate) <= 5.0 else "DIVERGENT"
    )
    dd_status: Literal["SAFE", "WARNING"] = "SAFE" if paper_dd <= backtest_dd * 1.2 else "WARNING"
    trade_status: Literal["MATCH", "WARNING"] = (
        "MATCH" if abs(paper_trades_count - backtest_trades_count) <= 5 else "WARNING"
    )

    metrics = [
        QuickCompareMetricItem(
            metric="Total Realized PnL",
            live_paper_val=f"+₹{paper_pnl:,.2f}" if paper_pnl >= 0 else f"-₹{abs(paper_pnl):,.2f}",
            backtest_expected_val=f"+₹{backtest_pnl:,.2f}"
            if backtest_pnl >= 0
            else f"-₹{abs(backtest_pnl):,.2f}",
            status=pnl_status,
            badge_label="ON TRACK" if pnl_status == "ON_TRACK" else "DIVERGING",
        ),
        QuickCompareMetricItem(
            metric="Win Rate (%)",
            live_paper_val=f"{paper_win_rate:.1f}%",
            backtest_expected_val=f"{backtest_win_rate:.1f}%",
            status=wr_status,
            badge_label="STABLE" if wr_status == "STABLE" else "VOLATILE",
        ),
        QuickCompareMetricItem(
            metric="Max Drawdown (%)",
            live_paper_val=f"-{paper_dd:.1f}%",
            backtest_expected_val=f"-{backtest_dd:.1f}%",
            status=dd_status,
            badge_label="SAFE" if dd_status == "SAFE" else "HIGH DD",
        ),
        QuickCompareMetricItem(
            metric="Total Trades Executed",
            live_paper_val=f"{paper_trades_count} Trades",
            backtest_expected_val=f"{backtest_trades_count} Trades",
            status=trade_status,
            badge_label="MATCH" if trade_status == "MATCH" else "MISMATCH",
        ),
    ]

    return QuickCompareResponse(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        session_id=session_id,
        execution_mode="PAPER TRADING",
        metrics=metrics,
        open_positions=open_positions,
        shadow_leaderboard=shadow_leaderboard,
    )


def generate_drift_analysis(
    session_id: int,
    strategy_name: str,
    paper_pnl: float,
    backtest_pnl: float,
    paper_win_rate: float,
    backtest_win_rate: float,
    paper_dd: float,
    backtest_dd: float,
    total_paper_trades: int,
    slippage_latency_cost: float = 140.0,
) -> DriftAnalysisResponse:
    """Build detailed drift analytics response."""
    wr_drift = round(paper_win_rate - backtest_win_rate, 2)
    readiness = compute_readiness_score(
        paper_pnl=paper_pnl,
        expected_pnl=backtest_pnl,
        paper_win_rate=paper_win_rate,
        backtest_win_rate=backtest_win_rate,
        paper_drawdown_pct=paper_dd,
        backtest_drawdown_pct=backtest_dd,
        total_trades=total_paper_trades,
    )

    return DriftAnalysisResponse(
        session_id=session_id,
        strategy_name=strategy_name,
        paper_win_rate=round(paper_win_rate, 2),
        backtest_win_rate=round(backtest_win_rate, 2),
        win_rate_drift_pct=wr_drift,
        paper_max_drawdown_pct=round(paper_dd, 2),
        backtest_max_drawdown_pct=round(backtest_dd, 2),
        slippage_latency_cost_total=round(slippage_latency_cost, 2),
        total_paper_trades=total_paper_trades,
        readiness=readiness,
    )
