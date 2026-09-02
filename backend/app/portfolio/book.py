"""Isolated strategy accounting book tracking dedicated cash, positions, and daily PnL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.engine.daily_pnl import DailyPnLRecord, DailyPnLTracker, ExecutionMode


@dataclass
class PositionEntry:
    """Position tracker for a single instrument within an isolated book."""

    quantity: int = 0
    average_price: float = 0.0
    current_price: float = 0.0


class StrategyBook:
    """Self-contained accounting ledger for an individual sub-strategy.

    Enforces total isolation: strategy A cannot spend, pledge, or modify
    cash, margin, or positions belonging to strategy B.
    """

    def __init__(
        self,
        *,
        strategy_id: str,
        strategy_name: str,
        allocated_capital: float,
        mode: ExecutionMode = ExecutionMode.BACKTEST,
    ) -> None:
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.initial_capital = allocated_capital
        self.cash = allocated_capital
        self.positions: dict[str, PositionEntry] = {}
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.pending_cashflow = 0.0
        self.daily_tracker = DailyPnLTracker(
            initial_capital=allocated_capital,
            mode=mode,
        )

    def deposit_or_withdraw(self, delta_cash: float) -> None:
        """Transfer capital during rebalancing without corrupting trading PnL."""
        self.cash += delta_cash
        self.pending_cashflow += delta_cash

    def apply_trade(
        self,
        symbol: str,
        qty: int,
        price: float,
        fee: float = 0.0,
    ) -> None:
        """Record trade execution within this book.

        Positive qty = Buy, Negative qty = Sell.
        """
        cost = qty * price
        total_outlay = cost + fee
        self.cash -= total_outlay

        entry = self.positions.setdefault(symbol, PositionEntry())
        prev_qty = entry.quantity
        entry.current_price = price

        if (prev_qty > 0 and qty > 0) or (prev_qty < 0 and qty < 0):
            # Increasing position size
            total_shares = prev_qty + qty
            new_avg = (
                (prev_qty * entry.average_price + qty * price) / total_shares
                if total_shares != 0
                else 0.0
            )
            entry.quantity = total_shares
            entry.average_price = new_avg
        elif prev_qty != 0 and ((prev_qty > 0 and qty < 0) or (prev_qty < 0 and qty > 0)):
            # Reducing or closing position: calculate realized PnL
            closing_qty = min(abs(prev_qty), abs(qty))
            if prev_qty > 0:
                pnl = closing_qty * (price - entry.average_price)
            else:
                pnl = closing_qty * (entry.average_price - price)

            self.realized_pnl += pnl
            rem_qty = prev_qty + qty
            entry.quantity = rem_qty
            if rem_qty == 0:
                entry.average_price = 0.0
        else:
            # Opening new position from flat
            entry.quantity = qty
            entry.average_price = price

    def mark_to_market(
        self,
        current_prices: dict[str, float],
        as_of_date: date,
        day_realized_pnl: float = 0.0,
        day_costs: float = 0.0,
    ) -> DailyPnLRecord:
        """Compute end-of-day MTM and append record to DailyPnLTracker."""
        mtm = 0.0
        for symbol, entry in self.positions.items():
            if symbol in current_prices:
                entry.current_price = current_prices[symbol]
            elif entry.current_price == 0.0:
                entry.current_price = entry.average_price

            if entry.quantity != 0:
                mtm += entry.quantity * (entry.current_price - entry.average_price)

        self.unrealized_pnl = mtm
        cf = self.pending_cashflow
        self.pending_cashflow = 0.0

        record = self.daily_tracker.record_day(
            record_date=as_of_date,
            realized_pnl=day_realized_pnl,
            unrealized_pnl=mtm,
            transaction_costs=day_costs,
            cashflow=cf,
        )
        return record

    @property
    def total_equity(self) -> float:
        """Total book equity = cash + market value of open positions."""
        pos_val = sum(
            entry.quantity
            * (entry.current_price if entry.current_price > 0 else entry.average_price)
            for entry in self.positions.values()
        )
        return self.cash + pos_val
