"""Offline scheduled execution engine for saved screeners."""

from __future__ import annotations

import logging

from app.screener.runner import PointInTimeScreenerRunner
from app.screener.store import ScreenerRunSnapshot, ScreenerStore, screener_store

logger = logging.getLogger(__name__)


class ScreenerScheduler:
    """Manager for scheduling and executing offline periodic screener jobs."""

    def __init__(
        self,
        store: ScreenerStore | None = None,
        runner: PointInTimeScreenerRunner | None = None,
    ) -> None:
        self.store = store or screener_store
        self.runner = runner

    def run_scheduled_job(
        self, screener_id: str, runner: PointInTimeScreenerRunner | None = None
    ) -> ScreenerRunSnapshot:
        """Execute a scheduled screener job and persist its immutable snapshot."""
        record = self.store.get_screener(screener_id)
        if not record:
            raise KeyError(f"Screener '{screener_id}' not found in store")

        active_runner = runner or self.runner
        if not active_runner:
            raise ValueError("No PointInTimeScreenerRunner provided for execution")

        logger.info("Executing scheduled screener job '%s' (%s)", record.name, screener_id)
        result = active_runner.run(record.definition)
        snapshot = self.store.save_run_snapshot(
            screener_id=record.id,
            screener_name=record.name,
            result=result,
        )
        logger.info(
            "Scheduled screener job '%s' finished with %d matches (Run ID: %s)",
            record.name,
            len(result.matches),
            snapshot.run_id,
        )
        return snapshot
