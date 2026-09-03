"""Lightweight production container healthcheck probe module for engine, feedd, and worker.

Usage:
    python -m app.contracts.health_check <process_name> [--max-age-seconds 15]

Exits with code 0 if the process has a recent valid heartbeat in Postgres,
and code 1 if missing, stopped, or stale.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from app.contracts import heartbeat as hb

DEFAULT_MAX_AGE_SECONDS = 15.0


def check_process_health(
    process_name: str, max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS
) -> bool:
    """Verify that process is running and has written a heartbeat within max_age_seconds."""
    if process_name not in hb.PROCESS_NAMES:
        return False

    try:
        engine = hb.make_engine()
        try:
            row = hb.read(engine, process_name)
            if row is None:
                return False
            if row.status != hb.STATUS_RUNNING:
                return False

            age = (datetime.now(tz=UTC) - row.last_heartbeat_at).total_seconds()
            return age <= max_age_seconds
        finally:
            engine.dispose()
    except Exception:
        return False


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python -m app.contracts.health_check <process_name>\n")
        sys.exit(1)

    process_name = sys.argv[1]
    is_healthy = check_process_health(process_name)
    if is_healthy:
        sys.stdout.write(f"OK: {process_name} is healthy\n")
        sys.exit(0)
    else:
        sys.stderr.write(f"UNHEALTHY: {process_name} heartbeat missing or stale\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
