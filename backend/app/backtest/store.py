"""Persistence store for Backtest run executions, audit logs, and performance snapshots."""

from __future__ import annotations

from app.backtest.models import BacktestResult


class BacktestStore:
    """Thread-safe storage manager for historical backtest runs."""

    def __init__(self) -> None:
        self._results: dict[str, BacktestResult] = {}

    def save_result(self, result: BacktestResult) -> BacktestResult:
        """Save a completed backtest result."""
        self._results[result.backtest_id] = result
        return result

    def get_result(self, backtest_id: str) -> BacktestResult | None:
        """Retrieve a backtest result by ID."""
        return self._results.get(backtest_id)

    def list_results(self) -> list[BacktestResult]:
        """List all saved backtest results in reverse chronological order."""
        results = list(self._results.values())
        results.sort(key=lambda r: r.executed_at, reverse=True)
        return results

    def clear(self) -> None:
        """Clear all stored backtest results."""
        self._results.clear()


# Global singleton backtest store
backtest_store = BacktestStore()
