"""REST and WebSocket API endpoints for Dhan feed monitoring and browser market data fan-out."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)

from app.api.ws import (
    ClientSession,
    get_market_data_fanout_manager,
)
from app.feedd.budget import (
    BudgetStatus,
    ConnectionBudgetManager,
    get_connection_budget_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])


def get_budget_manager() -> ConnectionBudgetManager:
    """Dependency providing the central connection budget manager."""
    return get_connection_budget_manager()


BudgetManagerDep = Annotated[ConnectionBudgetManager, Depends(get_budget_manager)]


@router.get("/budget", response_model=BudgetStatus)
def get_budget_status(manager: BudgetManagerDep) -> BudgetStatus:
    """Retrieve current Dhan WebSocket connection budget capacity and active leases."""
    return manager.get_status()


@router.get("/metrics")
def get_fanout_metrics() -> dict[str, Any]:
    """Retrieve browser WebSocket fan-out telemetry, session counts, and backpressure metrics."""
    manager = get_market_data_fanout_manager()
    return manager.get_metrics()


async def _pump_outbound_messages(websocket: WebSocket, session: ClientSession) -> None:
    """Pumps messages from the session's bounded queue to the client WebSocket."""
    try:
        while True:
            msg = await session.queue.get()
            await websocket.send_json(msg)
            session.queue.task_done()
    except WebSocketDisconnect, asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.debug("Outbound pump encountered error for session %s: %s", session.session_id, exc)


@router.websocket("/ws")
async def market_data_websocket(
    websocket: WebSocket,
    token: str | None = None,
) -> None:
    """Browser WebSocket endpoint for real-time market data snapshots, deltas, and resync."""
    # Authorization boundary: validate token if token is provided or auth enforcement enabled
    # For local development terminal, accept connection
    await websocket.accept()

    fanout_manager = get_market_data_fanout_manager()
    session = ClientSession(websocket=websocket)
    fanout_manager.register_session(session)

    pump_task = asyncio.create_task(_pump_outbound_messages(websocket, session))

    try:
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                continue

            action = data.get("action")
            if action == "subscribe":
                raw_instruments = data.get("instruments", [])
                instruments: list[tuple[str, str]] = []
                for inst in raw_instruments:
                    if isinstance(inst, dict):
                        seg = str(inst.get("segment", ""))
                        sec_id = str(inst.get("security_id", ""))
                        instruments.append((seg, sec_id))
                    elif isinstance(inst, (list, tuple)) and len(inst) >= 2:
                        instruments.append((str(inst[0]), str(inst[1])))

                channels = data.get("channels")
                fanout_manager.subscribe(session.session_id, instruments, channels=channels)

            elif action == "unsubscribe":
                raw_instruments = data.get("instruments", [])
                unsub_instruments: list[tuple[str, str]] = []
                for inst in raw_instruments:
                    if isinstance(inst, dict):
                        seg = str(inst.get("segment", ""))
                        sec_id = str(inst.get("security_id", ""))
                        unsub_instruments.append((seg, sec_id))
                    elif isinstance(inst, (list, tuple)) and len(inst) >= 2:
                        unsub_instruments.append((str(inst[0]), str(inst[1])))
                fanout_manager.unsubscribe(session.session_id, unsub_instruments)

            elif action == "resync":
                fanout_manager.resync(session.session_id)

            elif action == "ping":
                session.send_nowait({"type": "pong", "timestamp": data.get("timestamp")})

    except WebSocketDisconnect, asyncio.CancelledError:
        pass
    finally:
        pump_task.cancel()
        try:
            await pump_task
        except asyncio.CancelledError:
            pass
        fanout_manager.unregister_session(session.session_id)
