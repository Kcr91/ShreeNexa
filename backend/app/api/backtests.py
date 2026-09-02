"""FastAPI router for Stock Strategy Backtesting, execution runs, and performance reports."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.backtest.models import BacktestConfig, BacktestResult
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.store import backtest_store

router = APIRouter(tags=["backtests"])


@router.post(
    "/api/v1/backtests/run",
    response_model=BacktestResult,
    status_code=201,
)
@router.post(
    "/api/backtests/run",
    response_model=BacktestResult,
    status_code=201,
    include_in_schema=False,
)
def run_backtest(config: BacktestConfig) -> BacktestResult:
    """Execute a stock strategy backtest and persist performance snapshot."""
    runner = StockStrategyBacktestRunner()
    result = runner.run(config)
    backtest_store.save_result(result)
    return result


@router.get(
    "/api/v1/backtests",
    response_model=list[BacktestResult],
)
@router.get(
    "/api/backtests",
    response_model=list[BacktestResult],
    include_in_schema=False,
)
def list_backtests() -> list[BacktestResult]:
    """List all persisted backtest runs."""
    return backtest_store.list_results()


@router.get(
    "/api/v1/backtests/{backtest_id}",
    response_model=BacktestResult,
)
@router.get(
    "/api/backtests/{backtest_id}",
    response_model=BacktestResult,
    include_in_schema=False,
)
def get_backtest(backtest_id: str) -> BacktestResult:
    """Retrieve detailed backtest result and equity curve by ID."""
    result = backtest_store.get_result(backtest_id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"Backtest '{backtest_id}' not found"
        )
    return result
