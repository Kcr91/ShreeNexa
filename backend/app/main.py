"""api process entry point: FastAPI application.

Owns REST endpoints, browser WebSocket fan-out, validation, the development
auth boundary, and user commands (per ADR-0002). F0.3 adds only a health
endpoint and this process's own heartbeat -- real routers, auth, and
WebSocket fan-out arrive with F0.4/F4.1/F7.4.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.backtests import router as backtests_router
from app.api.calibration import router as calibration_router
from app.api.depth import router as depth_router
from app.api.feed import router as feed_router
from app.api.heatmap import router as heatmap_router
from app.api.indicators import alias_router as indicators_alias_router
from app.api.indicators import router as indicators_router
from app.api.instruments import router as instruments_router
from app.api.options import router as options_router
from app.api.screeners import router as screeners_router
from app.api.universe import router as universe_router
from app.api.watchlists import router as watchlists_router
from app.contracts import heartbeat as hb
from app.contracts.process_loop import HEARTBEAT_INTERVAL_S
from app.dhan.credentials import resolve_dhan_credentials
from app.dhan.health import DhanTokenHealth, check_token_health

PROCESS_NAME = "api"


async def _heartbeat_task() -> None:
    engine = hb.make_engine()
    pid = os.getpid()
    hb.record_start(engine, PROCESS_NAME, pid)
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)
            hb.beat(engine, PROCESS_NAME)
    except asyncio.CancelledError:
        hb.record_stop(engine, PROCESS_NAME)
        raise
    finally:
        engine.dispose()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_heartbeat_task())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="ShreeNexa API", lifespan=lifespan)
app.include_router(instruments_router)
app.include_router(universe_router)
app.include_router(feed_router)
app.include_router(indicators_router)
app.include_router(indicators_alias_router)
app.include_router(screeners_router)
app.include_router(backtests_router)
app.include_router(watchlists_router)
app.include_router(heatmap_router)
app.include_router(depth_router)
app.include_router(options_router)
app.include_router(calibration_router)


@app.get("/healthz")
def healthz() -> dict[str, object]:
    """Liveness of `api` itself, plus a snapshot of every process's row --
    this is api's eventual dashboard role, exercised here at its simplest."""
    engine = hb.make_engine()
    try:
        rows = hb.read_all(engine)
    finally:
        engine.dispose()
    return {
        "process": PROCESS_NAME,
        "processes": [
            {
                "process_name": r.process_name,
                "pid": r.pid,
                "status": r.status,
                "last_heartbeat_at": r.last_heartbeat_at.isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/api/v1/dhan/token-health", response_model=DhanTokenHealth)
def get_dhan_token_health() -> DhanTokenHealth:
    """Return non-secret Dhan token health and expiry metadata for dashboard banners."""
    creds = resolve_dhan_credentials()
    return check_token_health(creds)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
