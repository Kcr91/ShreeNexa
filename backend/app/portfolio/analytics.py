"""Combined portfolio equity curves, drawdown analysis, risk caps, and risk/return attribution."""

from __future__ import annotations

import math
from datetime import datetime

from app.portfolio.models import (
    DrawdownPoint,
    PortfolioAnalyticsReport,
    PortfolioDailySnapshot,
    PortfolioRiskCaps,
    StrategyRiskAttribution,
)
from app.portfolio.orchestrator import PortfolioOrchestrator


def compute_drawdown_curve(
    equity_series: list[tuple[datetime, float]],
) -> tuple[list[DrawdownPoint], float, int]:
    """Calculate High Water Mark, Drawdown curve, Maximum Drawdown (MDD), and Max DD Duration.

    Returns:
        tuple of (drawdown_points, max_drawdown_pct, max_drawdown_duration_days)
    """
    if not equity_series:
        return [], 0.0, 0

    points: list[DrawdownPoint] = []
    hwm = equity_series[0][1]
    max_dd_pct = 0.0

    current_dd_start: datetime | None = None
    max_dd_duration_days = 0

    for dt, eq in equity_series:
        if eq >= hwm:
            hwm = eq
            if current_dd_start is not None:
                duration = (dt - current_dd_start).days
                if duration > max_dd_duration_days:
                    max_dd_duration_days = duration
                current_dd_start = None
        else:
            if current_dd_start is None:
                current_dd_start = dt
            else:
                duration = (dt - current_dd_start).days
                if duration > max_dd_duration_days:
                    max_dd_duration_days = duration

        dd_abs = round(eq - hwm, 4)
        dd_pct = round((eq - hwm) / hwm, 6) if hwm > 0 else 0.0

        if dd_pct < max_dd_pct:
            max_dd_pct = dd_pct

        points.append(
            DrawdownPoint(
                timestamp=dt,
                equity=round(eq, 2),
                high_water_mark=round(hwm, 2),
                drawdown_abs=dd_abs,
                drawdown_pct=dd_pct,
            )
        )

    # Check unrecovered ongoing drawdown at the end
    if current_dd_start is not None:
        last_dt = equity_series[-1][0]
        duration = (last_dt - current_dd_start).days
        if duration > max_dd_duration_days:
            max_dd_duration_days = duration

    return points, max_dd_pct, max_dd_duration_days


def check_risk_caps(
    snapshots: list[PortfolioDailySnapshot],
    max_drawdown_pct: float,
    caps: PortfolioRiskCaps,
) -> list[str]:
    """Evaluate portfolio risk guardrails and return human-readable breach messages."""
    breaches: list[str] = []

    # 1. Max Drawdown Cap
    if abs(max_drawdown_pct) > caps.max_drawdown_pct_cap:
        breaches.append(
            f"Max Drawdown breach: {abs(max_drawdown_pct):.2%} exceeded cap of "
            f"{caps.max_drawdown_pct_cap:.2%}"
        )

    # 2. Strategy Concentration Cap
    for snap in snapshots:
        for strat_id, weight in snap.strategy_weights.items():
            if weight > caps.max_strategy_concentration_pct:
                breaches.append(
                    f"Concentration breach on {snap.timestamp.strftime('%Y-%m-%d')}: "
                    f"Strategy '{strat_id}' weight {weight:.2%} exceeded cap of "
                    f"{caps.max_strategy_concentration_pct:.2%}"
                )
                break  # Record one breach per snapshot date

    return breaches


def compute_marginal_risk_return_attribution(
    *,
    strategy_returns: dict[str, list[float]],
    target_weights: dict[str, float],
    actual_weights: dict[str, float],
    strategy_names: dict[str, str],
    initial_allocations: dict[str, float],
    final_equities: dict[str, float],
    total_initial_capital: float,
) -> list[StrategyRiskAttribution]:
    """Compute Euler marginal contribution to risk (MCR) and percentage risk contribution (PCR).

    Guarantees Euler's allocation theorem: sum(PCR_i) == 1.0 (100% total risk attribution).
    """
    strat_ids = list(strategy_returns.keys())
    if not strat_ids:
        return []

    num_periods = len(next(iter(strategy_returns.values())))
    if num_periods < 2:
        # Trivial single-point case
        return [
            StrategyRiskAttribution(
                strategy_id=s_id,
                strategy_name=strategy_names.get(s_id, s_id),
                target_weight=round(target_weights.get(s_id, 0.0), 4),
                actual_weight=round(actual_weights.get(s_id, 0.0), 4),
                total_return_pct=0.0,
                return_contribution_pct=0.0,
                volatility=0.0,
                marginal_contribution_to_risk=0.0,
                percentage_risk_contribution=round(target_weights.get(s_id, 0.0), 4),
            )
            for s_id in strat_ids
        ]

    # Compute portfolio return time series: R_p(t) = sum(w_i * R_i(t))
    portfolio_returns: list[float] = [0.0] * num_periods
    for t in range(num_periods):
        portfolio_returns[t] = sum(
            target_weights.get(s_id, 0.0) * strategy_returns[s_id][t] for s_id in strat_ids
        )

    # Portfolio mean and variance
    mean_p = sum(portfolio_returns) / num_periods
    var_p = sum((r - mean_p) ** 2 for r in portfolio_returns) / (num_periods - 1)
    std_p = math.sqrt(var_p) if var_p > 0 else 0.0

    attributions: list[StrategyRiskAttribution] = []

    for s_id in strat_ids:
        r_series = strategy_returns[s_id]
        mean_i = sum(r_series) / num_periods
        var_i = sum((r - mean_i) ** 2 for r in r_series) / (num_periods - 1)
        std_i = math.sqrt(var_i) if var_i > 0 else 0.0

        # Covariance Cov(R_i, R_p)
        cov_i_p = (
            sum(
                (r_series[t] - mean_i) * (portfolio_returns[t] - mean_p)
                for t in range(num_periods)
            )
            / (num_periods - 1)
        )

        w = target_weights.get(s_id, 0.0)

        if std_p > 0.0:
            mcr = cov_i_p / std_p
            pcr = (w * mcr) / std_p
        else:
            mcr = 0.0
            pcr = w

        init_cap = initial_allocations.get(s_id, 0.0)
        final_eq = final_equities.get(s_id, init_cap)
        strat_pnl = final_eq - init_cap
        strat_ret_pct = (strat_pnl / init_cap * 100.0) if init_cap > 0 else 0.0
        ret_contrib_pct = (
            (strat_pnl / total_initial_capital * 100.0) if total_initial_capital > 0 else 0.0
        )

        attributions.append(
            StrategyRiskAttribution(
                strategy_id=s_id,
                strategy_name=strategy_names.get(s_id, s_id),
                target_weight=round(w, 4),
                actual_weight=round(actual_weights.get(s_id, 0.0), 4),
                total_return_pct=round(strat_ret_pct, 4),
                return_contribution_pct=round(ret_contrib_pct, 4),
                volatility=round(std_i * math.sqrt(252), 4),
                marginal_contribution_to_risk=round(mcr * math.sqrt(252), 4),
                percentage_risk_contribution=round(pcr, 4),
            )
        )

    return attributions


def generate_portfolio_analytics_report(
    orchestrator: PortfolioOrchestrator,
    caps: PortfolioRiskCaps | None = None,
) -> PortfolioAnalyticsReport:
    """Generate complete portfolio analytics, drawdown curve, and risk/return attribution."""
    caps = caps or PortfolioRiskCaps()
    summary = orchestrator.build_summary()
    snapshots = summary.daily_snapshots

    equity_series = [(s.timestamp, s.total_equity) for s in snapshots]
    drawdown_points, max_dd_pct, max_dd_days = compute_drawdown_curve(equity_series)

    breaches = check_risk_caps(snapshots, max_dd_pct, caps)

    # Strategy daily returns reconstruction
    strat_returns: dict[str, list[float]] = {s_id: [] for s_id in orchestrator.books}
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]
        for s_id in orchestrator.books:
            prev_eq = prev.strategy_equities.get(s_id, 1.0)
            curr_eq = curr.strategy_equities.get(s_id, prev_eq)
            ret = (curr_eq - prev_eq) / prev_eq if prev_eq > 0 else 0.0
            strat_returns[s_id].append(ret)

    target_weights = {a.strategy_id: a.weight for a in orchestrator.config.allocations}
    actual_weights = orchestrator.get_current_weights()
    strat_names = {a.strategy_id: a.strategy_name for a in orchestrator.config.allocations}
    final_equities = {s_id: b.total_equity for s_id, b in orchestrator.books.items()}

    attributions = compute_marginal_risk_return_attribution(
        strategy_returns=strat_returns,
        target_weights=target_weights,
        actual_weights=actual_weights,
        strategy_names=strat_names,
        initial_allocations=orchestrator.initial_splits,
        final_equities=final_equities,
        total_initial_capital=orchestrator.config.total_initial_capital,
    )

    # Portfolio metrics
    num_days = max(len(snapshots), 1)
    tot_ret = summary.total_return_pct
    ann_ret = tot_ret * (252.0 / num_days) if num_days > 0 else 0.0

    port_daily_rets = [
        (snapshots[i].total_equity - snapshots[i - 1].total_equity)
        / snapshots[i - 1].total_equity
        for i in range(1, len(snapshots))
        if snapshots[i - 1].total_equity > 0
    ]
    if len(port_daily_rets) >= 2:
        m_r = sum(port_daily_rets) / len(port_daily_rets)
        v_r = sum((r - m_r) ** 2 for r in port_daily_rets) / (len(port_daily_rets) - 1)
        port_vol = math.sqrt(v_r) * math.sqrt(252)
        sharpe = (ann_ret / 100.0) / port_vol if port_vol > 0 else 0.0
    else:
        port_vol = 0.0
        sharpe = 0.0

    return PortfolioAnalyticsReport(
        portfolio_name=orchestrator.config.portfolio_name,
        initial_capital=summary.initial_capital,
        final_capital=summary.final_capital,
        total_return_pct=summary.total_return_pct,
        annualized_return_pct=round(ann_ret, 4),
        portfolio_volatility=round(port_vol, 4),
        portfolio_sharpe=round(sharpe, 4),
        max_drawdown_pct=round(max_dd_pct, 4),
        max_drawdown_duration_days=max_dd_days,
        drawdown_curve=drawdown_points,
        attributions=attributions,
        caps_breaches=breaches,
    )
