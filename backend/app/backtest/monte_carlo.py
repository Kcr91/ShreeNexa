"""Monte Carlo simulation engine for backtest trade resampling and risk-of-ruin analysis."""

from __future__ import annotations

import random
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.engine.contracts import FillEvent, OrderSide


class ResampleMethod(StrEnum):
    """Resampling method for Monte Carlo simulations."""

    TRADE_SHUFFLE = "TRADE_SHUFFLE"
    BOOTSTRAP = "BOOTSTRAP"
    BLOCK_BOOTSTRAP = "BLOCK_BOOTSTRAP"


class MonteCarloConfig(BaseModel):
    """Configuration options for Monte Carlo simulation."""

    model_config = ConfigDict(extra="forbid")

    iterations: int = Field(default=1000, ge=10)
    resample_method: ResampleMethod = Field(default=ResampleMethod.TRADE_SHUFFLE)
    block_size: int = Field(default=5, ge=1)
    ruin_threshold_pct: float = Field(default=0.5, ge=0.0, le=1.0)
    sample_paths_count: int = Field(default=20, ge=0)
    seed: int = Field(default=42)


class MonteCarloPercentileSummary(BaseModel):
    """Percentile summary statistics of a simulated distribution."""

    model_config = ConfigDict(extra="forbid")

    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float


class MonteCarloResult(BaseModel):
    """Summary and percentile breakdown of Monte Carlo simulation runs."""

    model_config = ConfigDict(extra="forbid")

    iterations: int
    terminal_equity: MonteCarloPercentileSummary
    max_drawdown_pct: MonteCarloPercentileSummary
    risk_of_ruin_pct: float
    sample_paths: list[list[float]]


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute exact empirical percentile using linear rank interpolation."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]

    k = (n - 1) * p
    f = int(k)
    c = min(f + 1, n - 1)
    d = k - f
    return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])


def _summarize(values: list[float]) -> MonteCarloPercentileSummary:
    sorted_vals = sorted(values)
    return MonteCarloPercentileSummary(
        p5=_percentile(sorted_vals, 0.05),
        p25=_percentile(sorted_vals, 0.25),
        p50=_percentile(sorted_vals, 0.50),
        p75=_percentile(sorted_vals, 0.75),
        p95=_percentile(sorted_vals, 0.95),
        p99=_percentile(sorted_vals, 0.99),
    )


def run_monte_carlo(
    trades: list[FillEvent] | list[float],
    initial_capital: float,
    config: MonteCarloConfig | None = None,
) -> MonteCarloResult:
    """Run deterministic Monte Carlo resampling over historical trade PnLs."""
    cfg = config or MonteCarloConfig()
    rng = random.Random(cfg.seed)

    # Extract net PnL sequence
    trade_pnls: list[float] = []
    if trades and isinstance(trades[0], FillEvent):
        # Pair buy and sell fills sequentially to estimate trade PnLs
        fill_events = [t for t in trades if isinstance(t, FillEvent)]
        for i in range(0, len(fill_events) - 1, 2):
            entry = fill_events[i]
            exit_fill = fill_events[i + 1]
            if entry.side == OrderSide.BUY and exit_fill.side == OrderSide.SELL:
                pnl = (
                    (exit_fill.price - entry.price) * entry.quantity
                    - (entry.brokerage + entry.taxes)
                    - (exit_fill.brokerage + exit_fill.taxes)
                )
            else:
                pnl = (
                    (entry.price - exit_fill.price) * entry.quantity
                    - (entry.brokerage + entry.taxes)
                    - (exit_fill.brokerage + exit_fill.taxes)
                )
            trade_pnls.append(pnl)
    else:
        for t in trades:
            if isinstance(t, (int, float)):
                trade_pnls.append(float(t))

    if not trade_pnls:
        # Default empty
        base_summ = MonteCarloPercentileSummary(
            p5=initial_capital,
            p25=initial_capital,
            p50=initial_capital,
            p75=initial_capital,
            p95=initial_capital,
            p99=initial_capital,
        )
        zero_summ = MonteCarloPercentileSummary(p5=0.0, p25=0.0, p50=0.0, p75=0.0, p95=0.0, p99=0.0)
        return MonteCarloResult(
            iterations=cfg.iterations,
            terminal_equity=base_summ,
            max_drawdown_pct=zero_summ,
            risk_of_ruin_pct=0.0,
            sample_paths=[[initial_capital]],
        )

    n_trades = len(trade_pnls)
    ruin_equity_level = initial_capital * (1.0 - cfg.ruin_threshold_pct)
    ruin_count = 0

    terminal_equities: list[float] = []
    max_drawdowns: list[float] = []
    sample_paths: list[list[float]] = []

    for it in range(cfg.iterations):
        if cfg.resample_method == ResampleMethod.TRADE_SHUFFLE:
            sampled_pnls = list(trade_pnls)
            rng.shuffle(sampled_pnls)
        elif cfg.resample_method == ResampleMethod.BOOTSTRAP:
            sampled_pnls = [rng.choice(trade_pnls) for _ in range(n_trades)]
        else:  # BLOCK_BOOTSTRAP
            sampled_pnls = []
            block_size = min(cfg.block_size, n_trades)
            while len(sampled_pnls) < n_trades:
                start_idx = rng.randint(0, max(0, n_trades - block_size))
                sampled_pnls.extend(trade_pnls[start_idx : start_idx + block_size])
            sampled_pnls = sampled_pnls[:n_trades]

        # Simulate path
        eq = initial_capital
        peak = initial_capital
        max_dd_pct = 0.0
        ruined = False
        path: list[float] = [eq]

        for pnl in sampled_pnls:
            eq += pnl
            if eq > peak:
                peak = eq
            dd_pct = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
            if eq <= ruin_equity_level:
                ruined = True
            path.append(eq)

        if ruined:
            ruin_count += 1

        terminal_equities.append(eq)
        max_drawdowns.append(max_dd_pct)

        if it < cfg.sample_paths_count:
            sample_paths.append(path)

    risk_of_ruin = (ruin_count / cfg.iterations) * 100.0

    return MonteCarloResult(
        iterations=cfg.iterations,
        terminal_equity=_summarize(terminal_equities),
        max_drawdown_pct=_summarize(max_drawdowns),
        risk_of_ruin_pct=risk_of_ruin,
        sample_paths=sample_paths,
    )
