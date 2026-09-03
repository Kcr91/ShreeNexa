"""Stock Strategy Backtest Runner executing StrategyIR with realistic fees."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from datetime import datetime

from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.models import BacktestConfig, BacktestResult
from app.engine.contracts import (
    HistoricalDataSource,
    OrderRequest,
    OrderSide,
    OrderType,
    Portfolio,
    SimClock,
)
from app.engine.costs import cost_calculator
from app.engine.sim_broker import SimBroker
from app.engine.slippage import (
    NoSlippageModel,
    PercentageSlippageModel,
    SlippageModel,
    TickSlippageModel,
)
from app.strategy.compiler import StrategyEvaluationResult, VectorStrategyCompiler
from app.strategy.ir import (
    InstrumentRef,
    StaticUniverse,
    StrategyIR,
)
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


class StockStrategyBacktestRunner:
    """Executes StrategyIR definitions against historical stock bars with taxes."""

    def __init__(
        self,
        bar_provider: Callable[[str, str, datetime, datetime], list[BarRecord]] | None = None,
    ) -> None:
        self.bar_provider = bar_provider
        self.compiler = VectorStrategyCompiler()

    def run(
        self,
        config: BacktestConfig,
        bars_dataset: dict[str, list[BarRecord]] | None = None,
    ) -> BacktestResult:
        """Run complete backtest simulation and return audited performance snapshot."""
        strategy = config.strategy

        # 1. Resolve Universe Instruments
        instruments: list[InstrumentRef] = []
        if isinstance(strategy.universe, StaticUniverse):
            instruments = strategy.universe.instruments

        # 2. Gather Bars
        all_bars: list[BarRecord] = []
        bars_by_sec: dict[str, list[BarRecord]] = {}

        if bars_dataset:
            for sec_id, b_list in bars_dataset.items():
                filtered = [
                    b for b in b_list if config.start_date <= b.timestamp <= config.end_date
                ]
                bars_by_sec[sec_id] = sorted(filtered, key=lambda b: b.timestamp)
                all_bars.extend(filtered)
        elif self.bar_provider:
            for inst in instruments:
                b_list = self.bar_provider(
                    inst.segment, inst.security_id, config.start_date, config.end_date
                )
                bars_by_sec[inst.security_id] = sorted(b_list, key=lambda b: b.timestamp)
                all_bars.extend(b_list)

        if not all_bars:
            empty_portfolio = Portfolio.create(initial_cash=config.initial_cash)
            metrics = calculate_backtest_metrics(
                config.initial_cash, empty_portfolio, config.start_date, config.end_date
            )
            return BacktestResult(
                strategy_name=strategy.name,
                config=config,
                metrics=metrics,
                trades=[],
                equity_curve=[],
                engine_commit=_get_git_commit(),
                ai_metadata=config.ai_metadata,
            )

        # 3. Precompile Signals using VectorStrategyCompiler
        compiled = self.compiler.compile(strategy)
        eval_results: dict[str, StrategyEvaluationResult] = {}
        for sec_id, b_list in bars_by_sec.items():
            if b_list:
                eval_results[sec_id] = compiled.evaluate(b_list)

        # 4. Initialize Clock, Slippage Model, SimBroker, and Portfolio
        timestamps = sorted({b.timestamp for b in all_bars})
        clock = SimClock(timestamps)
        datasource = HistoricalDataSource(all_bars)

        slippage_model: SlippageModel
        if config.slippage_model == "tick":
            slippage_model = TickSlippageModel(ticks=int(config.slippage_param))
        elif config.slippage_model == "percent":
            slippage_model = PercentageSlippageModel(percentage=config.slippage_param)
        else:
            slippage_model = NoSlippageModel()

        broker = SimBroker(
            slippage_model=slippage_model,
            fill_timing=config.fill_timing,
            initial_cash=config.initial_cash,
        )

        # Map timestamps to index per security for signal evaluation
        bar_idx_by_sec: dict[str, dict[datetime, int]] = {}
        for sec_id, b_list in bars_by_sec.items():
            bar_idx_by_sec[sec_id] = {b.timestamp: idx for idx, b in enumerate(b_list)}

        # 5. Execution Stepping Loop
        while not clock.is_done() or clock.now() == timestamps[-1]:
            now = clock.now()
            current_bars = datasource.advance(now)

            # Process pending orders through SimBroker on incoming bars
            for bar in current_bars:
                fills = broker.process_bar(bar)
                for fill in fills:
                    # Apply accurate Indian transaction taxes to every fill
                    fee = cost_calculator.calculate_cost(
                        product_type=config.product_type,
                        side=fill.side,
                        quantity=fill.quantity,
                        price=fill.price,
                        timestamp=fill.timestamp,
                    )
                    fill.brokerage = fee.brokerage
                    fill.taxes = (
                        fee.stt_ctt
                        + fee.exchange_txn_charge
                        + fee.sebi_fee
                        + fee.stamp_duty
                        + fee.gst
                    )

            # Evaluate strategy signals and generate orders
            for bar in current_bars:
                sec_id = bar.security_id
                sec_res = eval_results.get(sec_id)
                sec_idx_map = bar_idx_by_sec.get(sec_id, {})
                idx = sec_idx_map.get(bar.timestamp)

                if sec_res is not None and idx is not None:
                    pos = broker.portfolio.positions.get(sec_id)
                    current_qty = pos.quantity if pos else 0

                    # Any entry rule matching at this bar
                    entry_signal = any(
                        bool(sig_list[idx])
                        for sig_list in sec_res.entry_signals.values()
                        if idx < len(sig_list)
                    )

                    # Any exit rule matching at this bar
                    exit_signal = any(
                        bool(sig_list[idx])
                        for sig_list in sec_res.exit_signals.values()
                        if idx < len(sig_list)
                    )

                    # Sizing calculation
                    order_qty = self._calculate_order_qty(
                        strategy, broker.portfolio.cash, bar.close
                    )

                    # Long Entry
                    if entry_signal and current_qty == 0 and order_qty > 0:
                        req = OrderRequest(
                            security_id=sec_id,
                            exchange_segment=bar.exchange_segment,
                            side=OrderSide.BUY,
                            quantity=order_qty,
                            order_type=OrderType.MARKET,
                            tag=f"entry_{strategy.name}",
                        )
                        broker.submit([req])

                    # Long Exit
                    elif exit_signal and current_qty > 0:
                        req = OrderRequest(
                            security_id=sec_id,
                            exchange_segment=bar.exchange_segment,
                            side=OrderSide.SELL,
                            quantity=current_qty,
                            order_type=OrderType.MARKET,
                            tag=f"exit_{strategy.name}",
                        )
                        broker.submit([req])

            # Mark to Market
            mark_prices = {b.security_id: b.close for b in current_bars}
            broker.portfolio.mark_to_market(mark_prices, now)

            if clock.is_done():
                break
            clock.step()

        # 6. Calculate Performance Metrics
        metrics = calculate_backtest_metrics(
            initial_capital=config.initial_cash,
            portfolio=broker.portfolio,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        return BacktestResult(
            strategy_name=strategy.name,
            config=config,
            metrics=metrics,
            trades=broker.portfolio.fills,
            equity_curve=broker.portfolio.equity_curve,
            engine_commit=_get_git_commit(),
            ai_metadata=config.ai_metadata,
        )

    def _calculate_order_qty(
        self, strategy: StrategyIR, available_cash: float, current_price: float
    ) -> int:
        """Resolve order quantity from strategy sizing rule."""
        if current_price <= 0:
            return 0

        sizing = strategy.sizing
        if sizing.type == "fixed_qty" and sizing.qty:
            return sizing.qty
        elif sizing.type == "fixed_value" and sizing.value:
            return max(1, int(sizing.value / current_price))
        elif sizing.type == "pct_capital" and sizing.pct:
            target_val = available_cash * (sizing.pct / 100.0)
            return max(1, int(target_val / current_price))
        return 1
