"""Multi-strategy portfolio run orchestrator coordinating capital, execution, and rebalancing."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.portfolio.allocation import (
    compute_rebalance_transfers,
    split_initial_capital,
    validate_allocation_config,
)
from app.portfolio.book import StrategyBook
from app.portfolio.models import (
    PortfolioAllocationConfig,
    PortfolioDailySnapshot,
    PortfolioRunSummary,
    RebalanceFrequency,
    RebalanceTransferRecord,
    RebalanceTrigger,
)


class PortfolioOrchestrator:
    """Orchestrates multi-strategy portfolio backtest and live monitoring with isolated books."""

    def __init__(self, config: PortfolioAllocationConfig) -> None:
        validate_allocation_config(config)
        self.config = config
        self.initial_splits = split_initial_capital(config)

        # Initialize isolated accounting book for each strategy
        self.books: dict[str, StrategyBook] = {}
        for alloc in config.allocations:
            allocated_cap = self.initial_splits[alloc.strategy_id]
            self.books[alloc.strategy_id] = StrategyBook(
                strategy_id=alloc.strategy_id,
                strategy_name=alloc.strategy_name,
                allocated_capital=allocated_cap,
            )

        self.rebalance_history: list[RebalanceTransferRecord] = []
        self.daily_snapshots: list[PortfolioDailySnapshot] = []

    @property
    def total_portfolio_cash(self) -> float:
        """Sum of cash across all isolated books. Guarantees no double spend."""
        return sum(book.cash for book in self.books.values())

    @property
    def total_portfolio_equity(self) -> float:
        """Sum of mark-to-market equity across all isolated books."""
        return sum(book.total_equity for book in self.books.values())

    def get_current_weights(self) -> dict[str, float]:
        """Compute real-time equity percentage allocation for each strategy."""
        tot_eq = self.total_portfolio_equity
        if tot_eq <= 0.0:
            return {s_id: 0.0 for s_id in self.books}
        return {s_id: book.total_equity / tot_eq for s_id, book in self.books.items()}

    def evaluate_rebalancing(
        self,
        timestamp: datetime,
        *,
        is_calendar_boundary: bool = False,
    ) -> list[RebalanceTransferRecord]:
        """Check rebalancing triggers and execute zero-sum capital rebalancing."""
        freq = self.config.rebalance_freq
        if freq == RebalanceFrequency.NEVER:
            return []

        trigger: RebalanceTrigger | None = None

        if freq != RebalanceFrequency.DRIFT_ONLY and is_calendar_boundary:
            trigger = RebalanceTrigger.CALENDAR
        else:
            # Check drift threshold
            current_weights = self.get_current_weights()
            for alloc in self.config.allocations:
                curr_w = current_weights.get(alloc.strategy_id, 0.0)
                if abs(curr_w - alloc.weight) >= self.config.rebalance_threshold_pct:
                    trigger = RebalanceTrigger.DRIFT_THRESHOLD
                    break

        if trigger is None:
            return []

        # Execute rebalance transfers
        target_weights = {a.strategy_id: a.weight for a in self.config.allocations}
        current_equities = {s_id: b.total_equity for s_id, b in self.books.items()}

        transfers = compute_rebalance_transfers(
            current_equities=current_equities,
            target_weights=target_weights,
            trigger=trigger,
            timestamp=timestamp,
        )

        for transfer in transfers:
            book = self.books.get(transfer.strategy_id)
            if book is not None:
                book.deposit_or_withdraw(transfer.delta_cash)

        self.rebalance_history.extend(transfers)
        return transfers

    def step_day(
        self,
        as_of_date: date,
        prices: dict[str, float],
        trades: dict[str, list[dict[str, Any]]] | None = None,
        is_calendar_boundary: bool = False,
    ) -> PortfolioDailySnapshot:
        """Simulate one trading day across all strategy books."""
        trades = trades or {}
        timestamp = datetime(as_of_date.year, as_of_date.month, as_of_date.day, 15, 30, tzinfo=UTC)

        # 1. Apply trades to respective isolated books
        for strat_id, strat_trades in trades.items():
            book = self.books.get(strat_id)
            if book is not None:
                for t in strat_trades:
                    book.apply_trade(
                        symbol=t["symbol"],
                        qty=t["qty"],
                        price=t["price"],
                        fee=t.get("fee", 0.0),
                    )

        # 2. Mark to market each book
        for book in self.books.values():
            book.mark_to_market(
                current_prices=prices,
                as_of_date=as_of_date,
            )

        # 3. Check and execute rebalancing
        self.evaluate_rebalancing(
            timestamp=timestamp,
            is_calendar_boundary=is_calendar_boundary,
        )

        # 4. Record portfolio snapshot
        snapshot = PortfolioDailySnapshot(
            timestamp=timestamp,
            total_cash=round(self.total_portfolio_cash, 2),
            total_equity=round(self.total_portfolio_equity, 2),
            strategy_equities={s_id: round(b.total_equity, 2) for s_id, b in self.books.items()},
            strategy_weights={s_id: round(w, 4) for s_id, w in self.get_current_weights().items()},
        )
        self.daily_snapshots.append(snapshot)
        return snapshot

    def build_summary(self) -> PortfolioRunSummary:
        """Compile complete portfolio backtest/orchestration summary."""
        init_cap = self.config.total_initial_capital
        final_eq = self.total_portfolio_equity
        total_pnl = final_eq - init_cap
        ret_pct = (total_pnl / init_cap) * 100.0 if init_cap > 0 else 0.0

        return PortfolioRunSummary(
            portfolio_name=self.config.portfolio_name,
            initial_capital=round(init_cap, 2),
            final_capital=round(final_eq, 2),
            total_pnl=round(total_pnl, 2),
            total_return_pct=round(ret_pct, 4),
            rebalance_events=self.rebalance_history,
            daily_snapshots=self.daily_snapshots,
        )
