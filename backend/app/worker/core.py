"""worker process entry point.

Owns backfills, corrections, backtests, screeners, parameter sweeps, and
scheduled/queued jobs (per ADR-0002). None of that exists yet -- this is
the F0.3 skeleton. Real job consumption arrives with Epic 1+.
"""

from __future__ import annotations

from app.contracts.process_loop import main_for

PROCESS_NAME = "worker"


def run() -> None:
    main_for(PROCESS_NAME)


if __name__ == "__main__":
    run()
