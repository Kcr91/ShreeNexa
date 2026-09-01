"""engine process entry point.

Owns paper/live deployment event loops, broker boundary, portfolio/risk
evaluation, orders, fills, positions, checkpoint/recovery (per ADR-0002).
None of that exists yet -- this is the F0.3 skeleton: prove the process is
independent and its liveness is durable. Real strategy execution arrives
with F3.1+.
"""

from __future__ import annotations

from app.contracts.process_loop import main_for

PROCESS_NAME = "engine"


def run() -> None:
    main_for(PROCESS_NAME)


if __name__ == "__main__":
    run()
