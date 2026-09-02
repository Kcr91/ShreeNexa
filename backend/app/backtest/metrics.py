"""Quantitative performance metrics calculator for backtest equity curves and trade ledgers."""

from __future__ import annotations

import math
import statistics
from datetime import datetime

from app.backtest.models import BacktestPerformanceMetrics
from app.engine.contracts import Portfolio


def calculate_backtest_metrics(
    initial_capital: float,
    portfolio: Portfolio,
    start_date: datetime,
    end_date: datetime,
) -> BacktestPerformanceMetrics:
    """Compute comprehensive risk, return, and trade metrics from portfolio execution results."""
    final_equity = portfolio.total_equity()
    total_pnl = final_equity - initial_capital
    total_return_pct = (total_pnl / initial_capital) * 100.0 if initial_capital > 0 else 0.0

    days = max(1, (end_date - start_date).days)
    if final_equity > 0 and initial_capital > 0:
        cagr_factor = final_equity / initial_capital
        if cagr_factor > 0:
            cagr_pct = ((cagr_factor ** (365.0 / days)) - 1.0) * 100.0
        else:
            cagr_pct = -100.0
    else:
        cagr_pct = -100.0

    total_costs = sum(f.total_cost for f in portfolio.fills)
    realized_pnl = sum(p.realized_pnl for p in portfolio.positions.values())
    unrealized_pnl = sum(p.unrealized_pnl for p in portfolio.positions.values())

    # Drawdown calculations across equity curve
    peak_equity = initial_capital
    max_dd_pct = 0.0
    max_dd_val = 0.0

    equities = [p.equity for p in portfolio.equity_curve]
    if not equities:
        equities = [final_equity]

    for eq in equities:
        if eq > peak_equity:
            peak_equity = eq
        dd_val = peak_equity - eq
        dd_pct = (dd_val / peak_equity) * 100.0 if peak_equity > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
        if dd_val > max_dd_val:
            max_dd_val = dd_val

    # Daily returns for Sharpe and Sortino
    if len(equities) > 1:
        rets: list[float] = []
        for i in range(1, len(equities)):
            prev = equities[i - 1]
            if prev > 0:
                rets.append((equities[i] - prev) / prev)
            else:
                rets.append(0.0)

        mean_ret = statistics.mean(rets) if rets else 0.0
        std_ret = statistics.stdev(rets) if len(rets) > 1 else 0.0
        neg_rets = [r for r in rets if r < 0]
        downside_std = statistics.stdev(neg_rets) if len(neg_rets) > 1 else 0.0

        # Annualized Sharpe (sqrt 252 trading sessions)
        sharpe = (mean_ret / std_ret) * math.sqrt(252) if std_ret > 1e-9 else 0.0
        sortino = (mean_ret / downside_std) * math.sqrt(252) if downside_std > 1e-9 else 0.0
    else:
        sharpe = 0.0
        sortino = 0.0

    # Calmar ratio
    calmar = (cagr_pct / max_dd_pct) if max_dd_pct > 1e-4 else 0.0

    # Trade statistics
    total_trades = len(portfolio.fills)
    winning_trades = sum(1 for p in portfolio.positions.values() if p.realized_pnl > 0)
    losing_trades = sum(1 for p in portfolio.positions.values() if p.realized_pnl < 0)
    denom = winning_trades + losing_trades
    win_rate_pct = (winning_trades / denom * 100.0) if denom > 0 else 0.0

    gross_profit = sum(p.realized_pnl for p in portfolio.positions.values() if p.realized_pnl > 0)
    gross_loss = abs(
        sum(p.realized_pnl for p in portfolio.positions.values() if p.realized_pnl < 0)
    )
    if gross_loss > 1e-9:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = gross_profit if gross_profit > 0 else 1.0

    return BacktestPerformanceMetrics(
        initial_capital=initial_capital,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        cagr_pct=cagr_pct,
        total_pnl=total_pnl,
        total_costs=total_costs,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_value=max_dd_val,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
    )
