"""Multi-strategy portfolio backtesting runner with capital allocation and rebalancing."""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime

from app.backtest.futures_models import FuturesContractSpec
from app.backtest.futures_runner import FuturesStrategyBacktestRunner
from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.options_runner import OptionStrategyBacktestRunner
from app.backtest.portfolio_models import (
    PortfolioBacktestConfig,
    PortfolioBacktestResult,
    PortfolioRebalanceEvent,
    RebalanceFrequency,
    StrategyContribution,
)
from app.backtest.runner import StockStrategyBacktestRunner
from app.engine.contracts import EquityPoint, Portfolio
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


def _get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


class PortfolioBacktestRunner:
    """Coordinates execution of multi-asset sub-strategies, merging equity curves and metrics."""

    def run(
        self,
        config: PortfolioBacktestConfig,
        stock_data: dict[str, list[BarRecord]] | None = None,
        option_data: dict[str, list[BarRecord]] | None = None,
        futures_contracts: list[FuturesContractSpec] | None = None,
        futures_data: dict[str, list[BarRecord]] | None = None,
    ) -> PortfolioBacktestResult:
        """Execute portfolio backtest across all child allocations."""
        stock_data = stock_data or {}
        option_data = option_data or {}
        futures_contracts = futures_contracts or []
        futures_data = futures_data or {}

        total_weight = sum(a.weight for a in config.allocations)
        if total_weight <= 0:
            total_weight = 1.0

        contributions: list[StrategyContribution] = []
        equity_series_by_strat: dict[str, dict[float, float]] = {}
        all_timestamps: set[float] = set()
        rebalance_events: list[PortfolioRebalanceEvent] = []

        # Execute each sub-strategy with its allocated capital slice
        for alloc in config.allocations:
            allocated_cap = config.initial_cash * (alloc.weight / total_weight)
            strat_equity_curve: list[EquityPoint] = []

            if alloc.strategy_type == "stock" and alloc.stock_config:
                alloc.stock_config.initial_cash = allocated_cap
                runner_stock = StockStrategyBacktestRunner()
                res_stock = runner_stock.run(alloc.stock_config, bars_dataset=stock_data)

                strat_equity_curve = res_stock.equity_curve
                metrics = res_stock.metrics

            elif alloc.strategy_type == "option" and alloc.option_config:
                alloc.option_config.initial_cash = allocated_cap
                bars = option_data.get(alloc.option_config.strategy.underlying_symbol, [])
                runner_opt = OptionStrategyBacktestRunner()
                res_opt = runner_opt.run(alloc.option_config, bars)

                strat_equity_curve = res_opt.equity_curve
                metrics = res_opt.metrics

            elif alloc.strategy_type == "futures" and alloc.futures_config:
                alloc.futures_config.initial_cash = allocated_cap
                runner_fut = FuturesStrategyBacktestRunner()
                res_fut = runner_fut.run(alloc.futures_config, futures_contracts, futures_data)

                strat_equity_curve = res_fut.equity_curve
                metrics = res_fut.metrics

            else:
                # Fallback / Empty
                synth_port = Portfolio.create(initial_cash=allocated_cap)
                metrics = calculate_backtest_metrics(
                    allocated_cap, synth_port, config.start_date, config.end_date
                )

            # Record strategy equity time series
            eq_dict: dict[float, float] = {}
            for ep in strat_equity_curve:
                ts_val = ep.timestamp.timestamp()
                eq_dict[ts_val] = ep.equity
                all_timestamps.add(ts_val)

            equity_series_by_strat[alloc.strategy_id] = eq_dict

            return_pct = (
                (metrics.final_equity - allocated_cap) / allocated_cap
                if allocated_cap > 0
                else 0.0
            )
            contributions.append(
                StrategyContribution(
                    strategy_id=alloc.strategy_id,
                    strategy_name=alloc.strategy_name,
                    allocated_capital=allocated_cap,
                    final_equity=metrics.final_equity,
                    total_pnl=metrics.total_pnl,
                    return_pct=return_pct,
                    initial_weight=alloc.weight / total_weight,
                    final_weight=0.0,  # Updated after combined equity calculation
                    metrics=metrics,
                )
            )

        # Merge daily equity curves across all strategies
        sorted_timestamps = sorted(all_timestamps)
        combined_equity_curve: list[EquityPoint] = []

        for ts in sorted_timestamps:
            total_eq_at_t = 0.0
            for alloc in config.allocations:
                strat_dict = equity_series_by_strat.get(alloc.strategy_id, {})
                strat_initial = config.initial_cash * (alloc.weight / total_weight)
                eq_val = strat_dict.get(ts, strat_initial)
                total_eq_at_t += eq_val

            dt = datetime.fromtimestamp(ts, tz=UTC)
            combined_equity_curve.append(
                EquityPoint(
                    timestamp=dt,
                    cash=0.0,
                    equity=total_eq_at_t,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                )
            )

        combined_final_equity = (
            combined_equity_curve[-1].equity if combined_equity_curve else config.initial_cash
        )

        # Update final weights in contributions
        for c in contributions:
            c.final_weight = (
                c.final_equity / combined_final_equity if combined_final_equity > 0 else 0.0
            )

        # Evaluate Rebalancing events
        if config.rebalance_freq != RebalanceFrequency.NEVER and combined_equity_curve:
            last_ts = combined_equity_curve[-1].timestamp
            for c in contributions:
                drift = abs(c.final_weight - c.initial_weight)
                if drift >= config.rebalance_threshold_pct:
                    target_cap = combined_final_equity * c.initial_weight
                    delta = target_cap - c.final_equity
                    rebalance_events.append(
                        PortfolioRebalanceEvent(
                            timestamp=last_ts,
                            strategy_id=c.strategy_id,
                            old_capital=c.final_equity,
                            new_capital=target_cap,
                            delta_cash=delta,
                        )
                    )

        # Create combined performance metrics
        comb_port = Portfolio.create(initial_cash=config.initial_cash)
        comb_port.equity_curve = combined_equity_curve
        combined_metrics = calculate_backtest_metrics(
            initial_capital=config.initial_cash,
            portfolio=comb_port,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        return PortfolioBacktestResult(
            name=config.name,
            config=config,
            combined_metrics=combined_metrics,
            contributions=contributions,
            rebalance_events=rebalance_events,
            combined_equity_curve=combined_equity_curve,
            engine_commit=_get_git_commit(),
        )
