"""Futures strategy backtesting simulation engine with automated contract rolls."""

from __future__ import annotations

import logging
import subprocess
import uuid
from datetime import datetime, timedelta

from app.backtest.futures_models import (
    FuturesBacktestConfig,
    FuturesBacktestResult,
    FuturesContractSpec,
    FuturesRollRecord,
)
from app.backtest.metrics import calculate_backtest_metrics
from app.engine.contracts import (
    FillEvent,
    OrderSide,
    Portfolio,
)
from app.engine.costs import ProductType, cost_calculator
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


class FuturesStrategyBacktestRunner:
    """Executes single and multi-month futures trading strategies with roll execution and MTM."""

    def run(
        self,
        config: FuturesBacktestConfig,
        contracts: list[FuturesContractSpec],
        bars_by_contract: dict[str, list[BarRecord]],
    ) -> FuturesBacktestResult:
        """Run futures backtest simulation over sequential contract schedules."""
        strategy = config.strategy
        portfolio = Portfolio.create(initial_cash=config.initial_cash)
        fills: list[FillEvent] = []
        rolls: list[FuturesRollRecord] = []
        margin_history: list[dict[str, float]] = []

        sorted_contracts = sorted(contracts, key=lambda c: c.expiry_date)
        if not sorted_contracts or not bars_by_contract:
            metrics = calculate_backtest_metrics(
                config.initial_cash, portfolio, config.start_date, config.end_date
            )
            return FuturesBacktestResult(
                strategy_name=strategy.name,
                config=config,
                metrics=metrics,
                rolls=[],
                margin_history=[],
                trades=[],
                equity_curve=[],
                engine_commit=_get_git_commit(),
            )

        # Collect all unique chronological timestamps across contracts
        all_bars: list[BarRecord] = []
        for b_list in bars_by_contract.values():
            all_bars.extend(b_list)

        filtered_bars = [
            b for b in all_bars if config.start_date <= b.timestamp <= config.end_date
        ]
        sorted_timestamps = sorted({b.timestamp for b in filtered_bars})

        if not sorted_timestamps:
            metrics = calculate_backtest_metrics(
                config.initial_cash, portfolio, config.start_date, config.end_date
            )
            return FuturesBacktestResult(
                strategy_name=strategy.name,
                config=config,
                metrics=metrics,
                rolls=[],
                margin_history=[],
                trades=[],
                equity_curve=[],
                engine_commit=_get_git_commit(),
            )

        # Index bars by contract and timestamp
        bars_lookup: dict[str, dict[datetime, BarRecord]] = {}
        for c_sym, b_list in bars_by_contract.items():
            bars_lookup[c_sym] = {b.timestamp: b for b in b_list}

        # Active contract index
        contract_idx = 0
        active_contract = sorted_contracts[contract_idx]
        qty = strategy.lot_size * strategy.lots

        # Initial Entry on first bar
        first_ts = sorted_timestamps[0]
        first_bar = bars_lookup.get(active_contract.symbol, {}).get(first_ts)
        entry_price = first_bar.open if first_bar else 100.0

        entry_fee = cost_calculator.calculate_cost(
            product_type=ProductType.FUTURES,
            side=strategy.side,
            quantity=qty,
            price=entry_price,
            timestamp=first_ts,
        )

        entry_fill = FillEvent(
            fill_id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            security_id=active_contract.symbol,
            exchange_segment=strategy.exchange_segment,
            side=strategy.side,
            quantity=qty,
            price=entry_price,
            timestamp=first_ts,
            brokerage=entry_fee.brokerage,
            taxes=(
                entry_fee.stt_ctt
                + entry_fee.exchange_txn_charge
                + entry_fee.sebi_fee
                + entry_fee.stamp_duty
                + entry_fee.gst
            ),
        )
        fills.append(entry_fill)
        portfolio.apply_fill(entry_fill)

        # Simulation stepping loop
        for t in sorted_timestamps:
            curr_bar = bars_lookup.get(active_contract.symbol, {}).get(t)
            curr_price = curr_bar.close if curr_bar else entry_price

            # Check contract roll condition
            roll_date_threshold = (
                active_contract.expiry_date.date()
                - timedelta(days=strategy.days_before_expiry_roll)
            )
            has_next_contract = contract_idx + 1 < len(sorted_contracts)

            if t.date() >= roll_date_threshold and has_next_contract:
                next_contract = sorted_contracts[contract_idx + 1]
                next_bar = bars_lookup.get(next_contract.symbol, {}).get(t)

                if next_bar:
                    # 1. Close current active contract position
                    close_side = (
                        OrderSide.SELL if strategy.side == OrderSide.BUY else OrderSide.BUY
                    )
                    close_price = curr_bar.close if curr_bar else curr_price
                    close_fee = cost_calculator.calculate_cost(
                        product_type=ProductType.FUTURES,
                        side=close_side,
                        quantity=qty,
                        price=close_price,
                        timestamp=t,
                    )
                    close_fill = FillEvent(
                        fill_id=str(uuid.uuid4()),
                        order_id=str(uuid.uuid4()),
                        security_id=active_contract.symbol,
                        exchange_segment=strategy.exchange_segment,
                        side=close_side,
                        quantity=qty,
                        price=close_price,
                        timestamp=t,
                        brokerage=close_fee.brokerage,
                        taxes=(
                            close_fee.stt_ctt
                            + close_fee.exchange_txn_charge
                            + close_fee.sebi_fee
                            + close_fee.stamp_duty
                            + close_fee.gst
                        ),
                    )
                    fills.append(close_fill)
                    portfolio.apply_fill(close_fill)

                    # 2. Open next contract position
                    open_price = next_bar.close
                    open_fee = cost_calculator.calculate_cost(
                        product_type=ProductType.FUTURES,
                        side=strategy.side,
                        quantity=qty,
                        price=open_price,
                        timestamp=t,
                    )
                    open_fill = FillEvent(
                        fill_id=str(uuid.uuid4()),
                        order_id=str(uuid.uuid4()),
                        security_id=next_contract.symbol,
                        exchange_segment=strategy.exchange_segment,
                        side=strategy.side,
                        quantity=qty,
                        price=open_price,
                        timestamp=t,
                        brokerage=open_fee.brokerage,
                        taxes=(
                            open_fee.stt_ctt
                            + open_fee.exchange_txn_charge
                            + open_fee.sebi_fee
                            + open_fee.stamp_duty
                            + open_fee.gst
                        ),
                    )
                    fills.append(open_fill)
                    portfolio.apply_fill(open_fill)

                    # Record roll event
                    roll_rec = FuturesRollRecord(
                        timestamp=t,
                        from_contract=active_contract.symbol,
                        to_contract=next_contract.symbol,
                        old_price=close_price,
                        new_price=open_price,
                        roll_spread=open_price - close_price,
                        roll_cost=close_fee.total_cost + open_fee.total_cost,
                    )
                    rolls.append(roll_rec)

                    # Switch active contract
                    contract_idx += 1
                    active_contract = next_contract
                    curr_price = open_price

            # Mark to Market
            mark_prices = {active_contract.symbol: curr_price}
            portfolio.mark_to_market(mark_prices, t)

            # Margin requirement
            req_margin = qty * curr_price * strategy.margin_pct
            margin_history.append({"timestamp": t.timestamp(), "required_margin": req_margin})

        # Calculate Performance Metrics
        metrics = calculate_backtest_metrics(
            initial_capital=config.initial_cash,
            portfolio=portfolio,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        return FuturesBacktestResult(
            strategy_name=strategy.name,
            config=config,
            metrics=metrics,
            rolls=rolls,
            margin_history=margin_history,
            trades=fills,
            equity_curve=portfolio.equity_curve,
            engine_commit=_get_git_commit(),
        )
