"""Paper trading P&L calendar and returns timeline adapter (F9.7).

Reuses the Epic 3 quantitative accounting ledger (DailyPnLTracker) with
mode=ExecutionMode.PAPER, guaranteeing zero duplicated calendar or
return-calculation logic across execution environments.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.engine.daily_pnl import (
    DailyPnLRecord,
    DailyPnLTracker,
    ExecutionMode,
    MonthlyPnLSummary,
    YearlyPnLSummary,
)
from app.paper.repository import PaperRepository, paper_repository

# Registry of account-level trackers for paper trading sessions
_paper_trackers: dict[str, DailyPnLTracker] = {}


def get_or_create_paper_tracker(
    account_id: str,
    initial_capital: float = 1_000_000.0,
    repository: PaperRepository | None = None,
) -> DailyPnLTracker:
    """Retrieve or initialize the DailyPnLTracker for a paper trading account."""
    repo = repository or paper_repository
    if account_id not in _paper_trackers:
        account = repo.get_account(account_id)
        cap = account.initial_capital if account else initial_capital
        _paper_trackers[account_id] = DailyPnLTracker(
            initial_capital=cap,
            mode=ExecutionMode.PAPER,
        )
    return _paper_trackers[account_id]


def reset_paper_trackers() -> None:
    """Reset paper trading trackers (for test isolation)."""
    _paper_trackers.clear()


class PaperCalendarResponse(BaseModel):
    """Authoritative P&L calendar and return summary for paper trading."""

    model_config = ConfigDict(extra="forbid")

    account_id: str
    source_kind: str = "paper"
    initial_capital: float
    current_equity: float
    cumulative_twr_pct: float
    daily_records: list[DailyPnLRecord] = Field(default_factory=list)
    monthly_summaries: list[MonthlyPnLSummary] = Field(default_factory=list)
    yearly_summaries: list[YearlyPnLSummary] = Field(default_factory=list)


class PaperReturnPoint(BaseModel):
    """Daily return point formatted for continuous timeline stitching."""

    date: str  # YYYY-MM-DD
    phase: str = "PAPER"
    equity: float
    daily_return: float
    cumulative_return: float


class PaperReturnsTimelineSlice(BaseModel):
    """Paper execution phase slice conforming to TimelinePhaseSlice contract."""

    phase: str = "PAPER"
    start_date: str
    end_date: str
    start_equity: float
    end_equity: float
    total_return: float
    daily_points: list[PaperReturnPoint] = Field(default_factory=list)
    source_kind: str = "paper"


def record_paper_day(
    account_id: str,
    record_date: date,
    realized_pnl: float = 0.0,
    unrealized_pnl: float = 0.0,
    transaction_costs: float = 0.0,
    cashflow: float = 0.0,
    repository: PaperRepository | None = None,
) -> DailyPnLRecord:
    """Record daily trading activity for a paper account in the shared accounting ledger."""
    tracker = get_or_create_paper_tracker(account_id, repository=repository)
    return tracker.record_day(
        record_date=record_date,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        transaction_costs=transaction_costs,
        cashflow=cashflow,
    )


def generate_paper_calendar_report(
    account_id: str,
    repository: PaperRepository | None = None,
) -> PaperCalendarResponse:
    """Generate calendar performance report by reading the paper account's DailyPnLTracker."""
    repo = repository or paper_repository
    account = repo.get_account(account_id)
    initial_capital = account.initial_capital if account else 1_000_000.0

    tracker = get_or_create_paper_tracker(
        account_id, initial_capital=initial_capital, repository=repo
    )

    history = tracker.get_history()
    monthly = tracker.get_monthly_summaries()
    yearly = tracker.get_yearly_summaries()

    return PaperCalendarResponse(
        account_id=account_id,
        source_kind="paper",
        initial_capital=initial_capital,
        current_equity=tracker.current_equity,
        cumulative_twr_pct=tracker.cumulative_twr_pct,
        daily_records=history,
        monthly_summaries=monthly,
        yearly_summaries=yearly,
    )


def generate_paper_returns_slice(
    account_id: str,
    repository: PaperRepository | None = None,
) -> PaperReturnsTimelineSlice:
    """Generate TimelinePhaseSlice for paper execution phase."""
    repo = repository or paper_repository
    account = repo.get_account(account_id)
    initial_capital = account.initial_capital if account else 1_000_000.0

    tracker = get_or_create_paper_tracker(
        account_id, initial_capital=initial_capital, repository=repo
    )
    history = tracker.get_history()

    if not history:
        today_str = date.today().isoformat()
        return PaperReturnsTimelineSlice(
            phase="PAPER",
            start_date=today_str,
            end_date=today_str,
            start_equity=initial_capital,
            end_equity=initial_capital,
            total_return=0.0,
            daily_points=[],
            source_kind="paper",
        )

    start_date = history[0].date.isoformat()
    end_date = history[-1].date.isoformat()
    start_equity = history[0].starting_equity
    end_equity = history[-1].ending_equity
    total_return = round(tracker.cumulative_twr, 6)

    daily_points = [
        PaperReturnPoint(
            date=rec.date.isoformat(),
            phase="PAPER",
            equity=rec.ending_equity,
            daily_return=rec.daily_return,
            cumulative_return=rec.cumulative_twr,
        )
        for rec in history
    ]

    return PaperReturnsTimelineSlice(
        phase="PAPER",
        start_date=start_date,
        end_date=end_date,
        start_equity=start_equity,
        end_equity=end_equity,
        total_return=total_return,
        daily_points=daily_points,
        source_kind="paper",
    )
