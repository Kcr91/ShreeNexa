"""Shared heartbeat-loop runner for the four F0.3 process skeletons.

Each process's entire loop body, for now, is "write a heartbeat" -- see
docs/qa/acceptance/F0.3.md's "No real capability logic" scope decision.
Later features add real work inside a process's own module; this helper
only owns startup/heartbeat/graceful-shutdown, which every process shares.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from collections.abc import Callable

from app.contracts import heartbeat as hb

HEARTBEAT_INTERVAL_S = 1.0


def run_heartbeat_loop(
    process_name: str,
    *,
    on_beat: Callable[[], None] | None = None,
    interval_s: float = HEARTBEAT_INTERVAL_S,
) -> None:
    """Block until SIGINT/SIGTERM, writing a heartbeat every `interval_s`.

    `on_beat`, when given, runs once per interval alongside the heartbeat
    write -- the hook a real process (feedd's packet poll, worker's queue
    poll) will eventually use, without this helper needing to know about it.
    """
    engine = hb.make_engine()
    pid = os.getpid()
    hb.record_start(engine, process_name, pid)
    print(f"[{process_name}] started, pid={pid}", flush=True)

    stop_requested = False

    def _handle_signal(signum: int, _frame: object) -> None:
        nonlocal stop_requested
        print(f"[{process_name}] received signal {signum}, shutting down", flush=True)
        stop_requested = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        while not stop_requested:
            hb.beat(engine, process_name)
            if on_beat is not None:
                on_beat()
            time.sleep(interval_s)
    finally:
        hb.record_stop(engine, process_name)
        print(f"[{process_name}] stopped cleanly", flush=True)
        engine.dispose()


def main_for(process_name: str) -> None:
    """Console-script entry point body for one process role."""
    try:
        run_heartbeat_loop(process_name)
    except KeyboardInterrupt:
        sys.exit(0)
