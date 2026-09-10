"""feedd process entry point.

Owns Dhan market-feed/depth connections, subscription state, packet
decoding, normalized hot-market state and feed health (per ADR-0002). None
of that exists yet -- this is the F0.3 skeleton. Real feed handling arrives
with F7.1+ (F0.9 first builds the connection-budget manager this will use).
"""

from __future__ import annotations

import asyncio
import threading

from app.contracts.process_loop import run_heartbeat_loop
from app.dhan.live_feed_service import get_dhan_live_feed_service

PROCESS_NAME = "feedd"


def run() -> None:
    service = get_dhan_live_feed_service()
    feed_thread = threading.Thread(
        target=lambda: asyncio.run(service.run()),
        name="dhan-market-feed",
        daemon=True,
    )
    feed_thread.start()
    try:
        run_heartbeat_loop(PROCESS_NAME)
    finally:
        service.stop()
        feed_thread.join(timeout=10.0)


if __name__ == "__main__":
    run()
