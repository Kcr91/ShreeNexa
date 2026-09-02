"""Adapter layer connecting paper trading results to the Epic 3 metric registry."""

from __future__ import annotations

from datetime import UTC, datetime

from app.backtest.grading import (
    GradingConfig,
    StrategyHorizon,
    StrategyScorecard,
    evaluate_strategy_scorecard,
)
from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.models import BacktestPerformanceMetrics
from app.engine.contracts import EquityPoint, FillEvent, OrderSide, Portfolio, Position
from app.paper.models import PaperOrderSide
from app.paper.repository import PaperRepository, paper_repository


def paper_account_to_portfolio(
    account_id: str,
    repository: PaperRepository | None = None,
) -> Portfolio:
    """Adapt paper repository account state, fills, and equity into a canonical Portfolio."""
    repo = repository or paper_repository
    account = repo.get_or_create_account(account_id)
    fills = repo.list_fills(account_id)
    positions = repo.list_positions(account_id)
    equity_points = repo.get_equity_curve(account_id)

    # Convert PaperFill objects to canonical FillEvent objects in chronological order
    fill_events: list[FillEvent] = []
    # list_fills returns reverse chronological (newest first), so reverse to chronological
    for f in reversed(fills):
        side = OrderSide.BUY if f.side == PaperOrderSide.BUY else OrderSide.SELL
        fill_events.append(
            FillEvent(
                order_id=f.order_id,
                security_id=f.security_id,
                exchange_segment=f.segment,
                side=side,
                quantity=f.quantity,
                price=f.price,
                timestamp=f.timestamp,
                brokerage=0.0,
                taxes=f.transaction_cost,
                slippage=f.slippage,
            )
        )

    # Convert PaperPosition objects to canonical Position objects
    pos_map: dict[str, Position] = {}
    for p in positions:
        pos_map[p.security_id] = Position(
            security_id=p.security_id,
            exchange_segment=p.segment,
            quantity=p.quantity,
            average_price=p.avg_entry_price,
            realized_pnl=p.realized_pnl,
            unrealized_pnl=p.unrealized_pnl,
            current_price=p.current_price,
        )

    # If no explicit equity points were recorded, construct a minimal 2-point boundary curve
    points = list(equity_points)
    if not points:
        now = datetime.now(UTC)
        points = [
            EquityPoint(
                timestamp=account.created_at,
                equity=account.initial_capital,
                cash=account.initial_capital,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
            ),
            EquityPoint(
                timestamp=now,
                equity=account.total_equity,
                cash=account.cash_balance,
                unrealized_pnl=account.unrealized_pnl,
                realized_pnl=account.realized_pnl,
            ),
        ]

    return Portfolio(
        initial_cash=account.initial_capital,
        cash=account.cash_balance,
        positions=pos_map,
        fills=fill_events,
        equity_curve=points,
    )


def calculate_paper_metrics(
    account_id: str,
    repository: PaperRepository | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> BacktestPerformanceMetrics:
    """Calculate quantitative performance metrics for a paper trading account without forks."""
    portfolio = paper_account_to_portfolio(account_id, repository=repository)

    # Determine date range from equity curve or fills if not explicitly specified
    if start_date is None:
        if portfolio.equity_curve:
            start_date = portfolio.equity_curve[0].timestamp
        elif portfolio.fills:
            start_date = portfolio.fills[0].timestamp
        else:
            start_date = datetime.now(UTC)

    if end_date is None:
        if portfolio.equity_curve:
            end_date = portfolio.equity_curve[-1].timestamp
        elif portfolio.fills:
            end_date = portfolio.fills[-1].timestamp
        else:
            end_date = datetime.now(UTC)

    # Reuse canonical Epic 3 metrics engine directly
    return calculate_backtest_metrics(
        initial_capital=portfolio.initial_cash,
        portfolio=portfolio,
        start_date=start_date,
        end_date=end_date,
    )


def evaluate_paper_scorecard(
    account_id: str,
    strategy_name: str,
    horizon: StrategyHorizon = StrategyHorizon.POSITIONAL,
    config: GradingConfig | None = None,
    repository: PaperRepository | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> StrategyScorecard:
    """Evaluate strategy scorecard and deployment verdict for a paper account without forks."""
    metrics = calculate_paper_metrics(
        account_id=account_id,
        repository=repository,
        start_date=start_date,
        end_date=end_date,
    )

    # Reuse canonical Epic 3 strategy grading engine directly
    return evaluate_strategy_scorecard(
        strategy_name=strategy_name,
        metrics=metrics,
        horizon=horizon,
        config=config,
    )
