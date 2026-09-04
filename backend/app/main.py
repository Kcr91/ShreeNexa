"""api process entry point: FastAPI application.

Owns REST endpoints, browser WebSocket fan-out, validation, the development
auth boundary, and user commands (per ADR-0002). F0.3 adds only a health
endpoint and this process's own heartbeat -- real routers, auth, and
WebSocket fan-out arrive with F0.4/F4.1/F7.4.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.backtests import router as backtests_router
from app.api.calibration import router as calibration_router
from app.api.deps import require_csrf, require_session
from app.api.depth import router as depth_router
from app.api.feature_builder import router as feature_builder_router
from app.api.feed import router as feed_router
from app.api.heatmap import router as heatmap_router
from app.api.indicators import alias_router as indicators_alias_router
from app.api.indicators import router as indicators_router
from app.api.instruments import router as instruments_router
from app.api.investing import router as investing_router
from app.api.margin import router as margin_router
from app.api.monitoring import router as monitoring_router
from app.api.options import router as options_router
from app.api.options_analytics import router as options_analytics_router
from app.api.orders import router as orders_router
from app.api.paper import router as paper_router
from app.api.screeners import router as screeners_router
from app.api.strategy_builder import router as strategy_builder_router
from app.api.strategy_ir import router as strategy_ir_router
from app.api.universe import router as universe_router
from app.api.watchlists import router as watchlists_router
from app.api.ws import router as ws_router
from app.contracts import heartbeat as hb
from app.contracts.process_loop import HEARTBEAT_INTERVAL_S
from app.dhan.credentials import resolve_dhan_credentials
from app.dhan.health import DhanTokenHealth, check_token_health

PROCESS_NAME = "api"


async def _heartbeat_task() -> None:
    try:
        engine = hb.make_engine()
        pid = os.getpid()
        hb.record_start(engine, PROCESS_NAME, pid)
    except Exception as exc:
        logging.getLogger(__name__).warning("Heartbeat disabled: database unavailable (%s)", exc)
        return

    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)
            try:
                hb.beat(engine, PROCESS_NAME)
            except Exception:
                pass
    except asyncio.CancelledError:
        try:
            hb.record_stop(engine, PROCESS_NAME)
        except Exception:
            pass
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_AUTH_DEPS = [Depends(require_session)]
_STATE_MUTATING_DEPS = [Depends(require_session), Depends(require_csrf)]

# 1. Self-authenticating or public routers
app.include_router(auth_router)
app.include_router(ws_router)

# 2. Read-only protected routers (require authenticated session)
app.include_router(instruments_router, dependencies=_AUTH_DEPS)
app.include_router(universe_router, dependencies=_AUTH_DEPS)
app.include_router(feed_router, dependencies=_AUTH_DEPS)
app.include_router(indicators_router, dependencies=_AUTH_DEPS)
app.include_router(indicators_alias_router, dependencies=_AUTH_DEPS)
app.include_router(heatmap_router, dependencies=_AUTH_DEPS)
app.include_router(depth_router, dependencies=_AUTH_DEPS)
app.include_router(options_router, dependencies=_AUTH_DEPS)
app.include_router(options_analytics_router, dependencies=_AUTH_DEPS)
app.include_router(margin_router, dependencies=_AUTH_DEPS)
app.include_router(monitoring_router, dependencies=_AUTH_DEPS)

# 3. Mutating / trading protected routers (require authenticated session + CSRF token)
app.include_router(orders_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(paper_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(screeners_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(backtests_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(watchlists_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(calibration_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(strategy_builder_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(strategy_ir_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(investing_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(ai_router, dependencies=_STATE_MUTATING_DEPS)
app.include_router(feature_builder_router, dependencies=_STATE_MUTATING_DEPS)


@app.get("/healthz")
def healthz() -> dict[str, object]:
    """Liveness of `api` itself, plus a snapshot of every process's row --
    this is api's eventual dashboard role, exercised here at its simplest."""
    try:
        engine = hb.make_engine()
        try:
            rows = hb.read_all(engine)
        finally:
            engine.dispose()
        processes = [
            {
                "process_name": r.process_name,
                "pid": r.pid,
                "status": r.status,
                "last_heartbeat_at": r.last_heartbeat_at.isoformat(),
            }
            for r in rows
        ]
    except Exception:
        processes = []
    return {
        "process": PROCESS_NAME,
        "processes": processes,
    }


@app.get(
    "/api/v1/dhan/token-health",
    response_model=DhanTokenHealth,
    dependencies=[Depends(require_session)],
)
def get_dhan_token_health() -> DhanTokenHealth:
    """Return non-secret Dhan token health and expiry metadata for dashboard banners."""
    creds = resolve_dhan_credentials()
    return check_token_health(creds)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
