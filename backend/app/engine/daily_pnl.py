"""Universal daily P&L, MTM, and Time-Weighted Return (TWR) accounting ledger."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ExecutionMode(StrEnum):
    """Trading terminal execution context."""

    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class DailyPnLRecord(BaseModel):
    """Immutable daily accounting record reconciling equity, cashflow, and PnL."""

    model_config = ConfigDict(extra="forbid")

    date: date
    starting_equity: float
    cashflow: float = Field(default=0.0, description="External deposits (+) or withdrawals (-)")
    realized_pnl: float = Field(default=0.0, description="Closed position PnL")
    unrealized_pnl: float = Field(default=0.0, description="End of day open position MTM")
    mtm_change: float = Field(default=0.0, description="Day-over-day change in unrealized MTM")
    transaction_costs: float = Field(default=0.0, ge=0.0, description="Brokerage, taxes, and fees")
    gross_pnl: float = Field(description="realized_pnl + mtm_change")
    net_pnl: float = Field(description="gross_pnl - transaction_costs")
    ending_equity: float = Field(description="starting_equity + cashflow + net_pnl")
    daily_return: float = Field(description="net_pnl / (starting_equity + cashflow)")
    cumulative_twr: float = Field(description="Geometrically linked time-weighted return")
    mode: ExecutionMode = Field(default=ExecutionMode.BACKTEST)


class MonthlyPnLSummary(BaseModel):
    """Aggregated monthly performance snapshot."""

    model_config = ConfigDict(extra="forbid")

    year: int
    month: int
    net_pnl: float
    twr_return_pct: float
    trading_days: int
    win_days: int
    loss_days: int


class YearlyPnLSummary(BaseModel):
    """Aggregated yearly performance snapshot."""

    model_config = ConfigDict(extra="forbid")

    year: int
    net_pnl: float
    twr_return_pct: float
    trading_days: int
    win_days: int
    loss_days: int


class DailyPnLTracker:
    """Manages daily P&L accounting, identity verification, and TWR calculations."""

    def __init__(
        self,
        initial_capital: float,
        mode: ExecutionMode = ExecutionMode.BACKTEST,
    ) -> None:
        if initial_capital <= 0:
            raise ValueError(f"Initial capital must be positive, got {initial_capital}")
        self._current_equity: float = initial_capital
        self._last_unrealized_pnl: float = 0.0
        self._cumulative_twr_factor: float = 1.0
        self._mode: ExecutionMode = mode
        self._history: list[DailyPnLRecord] = []

    @property
    def current_equity(self) -> float:
        """Current account equity."""
        return self._current_equity

    @property
    def cumulative_twr(self) -> float:
        """Cumulative Time-Weighted Return as a decimal fraction (e.g. 0.25 = 25%)."""
        return self._cumulative_twr_factor - 1.0

    @property
    def cumulative_twr_pct(self) -> float:
        """Cumulative Time-Weighted Return as a percentage."""
        return self.cumulative_twr * 100.0

    def record_day(
        self,
        record_date: date,
        realized_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
        transaction_costs: float = 0.0,
        cashflow: float = 0.0,
    ) -> DailyPnLRecord:
        """Record a single trading day's performance and update accounting ledger."""
        if transaction_costs < 0:
            raise ValueError(f"Transaction costs cannot be negative: {transaction_costs}")

        start_equity = self._current_equity
        mtm_change = unrealized_pnl - self._last_unrealized_pnl
        gross_pnl = realized_pnl + mtm_change
        net_pnl = gross_pnl - transaction_costs
        ending_equity = start_equity + cashflow + net_pnl

        # Base capital for sub-period rate of return calculation (start of day cashflow)
        base_capital = start_equity + cashflow
        if base_capital > 0:
            daily_return = net_pnl / base_capital
        else:
            daily_return = 0.0

        # Sub-period TWR geometric chain: factor = factor * (1 + r)
        self._cumulative_twr_factor *= 1.0 + daily_return

        record = DailyPnLRecord(
            date=record_date,
            starting_equity=start_equity,
            cashflow=cashflow,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            mtm_change=mtm_change,
            transaction_costs=transaction_costs,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            ending_equity=ending_equity,
            daily_return=daily_return,
            cumulative_twr=self.cumulative_twr,
            mode=self._mode,
        )

        # Update running state
        self._current_equity = ending_equity
        self._last_unrealized_pnl = unrealized_pnl
        self._history.append(record)

        return record

    def get_history(self) -> list[DailyPnLRecord]:
        """Return full ledger history."""
        return list(self._history)

    def get_monthly_summaries(self) -> list[MonthlyPnLSummary]:
        """Aggregate history into monthly performance summaries."""
        months: dict[tuple[int, int], list[DailyPnLRecord]] = defaultdict(list)
        for rec in self._history:
            key = (rec.date.year, rec.date.month)
            months[key].append(rec)

        summaries: list[MonthlyPnLSummary] = []
        for (year, month), recs in sorted(months.items()):
            tot_pnl = sum(r.net_pnl for r in recs)
            # Monthly TWR is product of (1 + r_t) for that month
            m_factor = 1.0
            for r in recs:
                m_factor *= 1.0 + r.daily_return
            m_twr_pct = (m_factor - 1.0) * 100.0

            win_days = sum(1 for r in recs if r.net_pnl > 0)
            loss_days = sum(1 for r in recs if r.net_pnl < 0)

            summaries.append(
                MonthlyPnLSummary(
                    year=year,
                    month=month,
                    net_pnl=tot_pnl,
                    twr_return_pct=m_twr_pct,
                    trading_days=len(recs),
                    win_days=win_days,
                    loss_days=loss_days,
                )
            )
        return summaries

    def get_yearly_summaries(self) -> list[YearlyPnLSummary]:
        """Aggregate history into yearly performance summaries."""
        years: dict[int, list[DailyPnLRecord]] = defaultdict(list)
        for rec in self._history:
            years[rec.date.year].append(rec)

        summaries: list[YearlyPnLSummary] = []
        for year, recs in sorted(years.items()):
            tot_pnl = sum(r.net_pnl for r in recs)
            y_factor = 1.0
            for r in recs:
                y_factor *= 1.0 + r.daily_return
            y_twr_pct = (y_factor - 1.0) * 100.0

            win_days = sum(1 for r in recs if r.net_pnl > 0)
            loss_days = sum(1 for r in recs if r.net_pnl < 0)

            summaries.append(
                YearlyPnLSummary(
                    year=year,
                    net_pnl=tot_pnl,
                    twr_return_pct=y_twr_pct,
                    trading_days=len(recs),
                    win_days=win_days,
                    loss_days=loss_days,
                )
            )
        return summaries
