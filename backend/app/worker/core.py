"""worker process entry point.

Owns backfills, corrections, backtests, screeners, parameter sweeps, and
scheduled/queued jobs (per ADR-0002). This now drives the backfill queue through the
``on_beat`` seam in ``app.contracts.process_loop``; the remaining job types arrive later.

Each beat processes a bounded number of windows rather than draining the queue, so the
heartbeat keeps being written and a stop signal is honoured promptly during a download
that runs for weeks.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

from app.contracts import heartbeat as hb
from app.contracts.process_loop import run_heartbeat_loop
from app.dhan.exceptions import DhanAuthenticationError
from app.warehouse.paths import DataRootCapacityError
from app.worker.backfill_runner import BackfillRunner, BudgetExhausted

logger = logging.getLogger(__name__)

PROCESS_NAME = "worker"

# Windows per beat. Small enough that a stop signal lands quickly; the rate limiter,
# not this number, governs throughput.
WINDOWS_PER_BEAT = 5

# How long to wait before retrying after a stop condition that will not clear quickly.
BUDGET_BACKOFF = timedelta(minutes=15)
AUTH_BACKOFF = timedelta(minutes=5)
DISK_BACKOFF = timedelta(minutes=30)

# Set SHREENEXA_BACKFILL_ENABLED=0 to run the worker without draining the queue.
ENABLE_ENV_VAR = "SHREENEXA_BACKFILL_ENABLED"


def backfill_enabled() -> bool:
    """Whether this worker should drain the backfill queue."""
    return os.environ.get(ENABLE_ENV_VAR, "1").strip().lower() not in {"0", "false", "no"}


class BackfillScheduler:
    """Drains a bounded slice of the backfill queue on each heartbeat."""

    def __init__(
        self,
        runner: BackfillRunner,
        windows_per_beat: int = WINDOWS_PER_BEAT,
    ) -> None:
        self.runner = runner
        self.windows_per_beat = windows_per_beat
        self.paused_until: datetime | None = None
        self.last_reason: str = "idle"

    def beat(self, now: datetime | None = None) -> str:
        """Run one slice. Returns the reason the slice ended, for logging and tests."""
        current = now or datetime.now(UTC)

        if self.paused_until is not None:
            if current < self.paused_until:
                return "paused"
            self.paused_until = None

        try:
            stats = self.runner.drain(max_windows=self.windows_per_beat)
        except BudgetExhausted:
            self._pause(current, BUDGET_BACKOFF, "budget_exhausted")
            return "budget_exhausted"
        except DhanAuthenticationError:
            self._pause(current, AUTH_BACKOFF, "paused_auth")
            return "paused_auth"
        except DataRootCapacityError:
            self._pause(current, DISK_BACKOFF, "disk_full")
            return "disk_full"

        if stats.stopped_reason in {"budget_exhausted", "paused_auth", "disk_full"}:
            backoff = {
                "budget_exhausted": BUDGET_BACKOFF,
                "paused_auth": AUTH_BACKOFF,
                "disk_full": DISK_BACKOFF,
            }[stats.stopped_reason]
            self._pause(current, backoff, stats.stopped_reason)
            return stats.stopped_reason

        self.last_reason = stats.stopped_reason
        return stats.stopped_reason

    def _pause(self, now: datetime, backoff: timedelta, reason: str) -> None:
        self.paused_until = now + backoff
        self.last_reason = reason
        logger.warning(
            "Backfill paused (%s); retrying after %s", reason, self.paused_until.isoformat()
        )


def run() -> None:
    """Console-script entry point: heartbeat loop with the backfill drain attached."""
    if not backfill_enabled():
        logger.info("Backfill draining disabled via %s; heartbeat only", ENABLE_ENV_VAR)
        run_heartbeat_loop(PROCESS_NAME)
        return

    engine = hb.make_engine()
    scheduler = BackfillScheduler(BackfillRunner(engine))

    def on_beat() -> None:
        try:
            scheduler.beat()
        except Exception:
            # A scheduler fault must never take down the heartbeat; the queue is
            # durable, so the next beat simply retries.
            logger.exception("Backfill beat failed; continuing")

    try:
        run_heartbeat_loop(PROCESS_NAME, on_beat=on_beat)
    finally:
        engine.dispose()


if __name__ == "__main__":
    run()
