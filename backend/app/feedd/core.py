"""feedd process entry point.

Owns Dhan market-feed/depth connections, subscription state, packet
decoding, normalized hot-market state and feed health (per ADR-0002). None
of that exists yet -- this is the F0.3 skeleton. Real feed handling arrives
with F7.1+ (F0.9 first builds the connection-budget manager this will use).
"""

from __future__ import annotations

from app.contracts.process_loop import main_for

PROCESS_NAME = "feedd"


def run() -> None:
    main_for(PROCESS_NAME)


if __name__ == "__main__":
    run()
