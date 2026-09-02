"""FastAPI router for Point-in-Time Screeners, run execution, and export."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from app.screener.models import ScreenerDefinition
from app.screener.routing import (
    export_screener_csv,
    export_screener_json,
    route_to_static_universe,
    route_to_watchlist,
)
from app.screener.runner import PointInTimeScreenerRunner
from app.screener.store import (
    ScreenerRecord,
    ScreenerRunSnapshot,
    screener_store,
)
from app.strategy.ir import StaticUniverse
from app.warehouse.schema import BarRecord

router = APIRouter(tags=["screeners"])


class CreateScreenerRequest(BaseModel):
    """Payload for creating a new screener definition."""

    model_config = ConfigDict(extra="forbid")

    definition: ScreenerDefinition
    schedule: str | None = Field(default=None, description="Optional cron schedule expression")


class RouteWatchlistRequest(BaseModel):
    """Payload for routing matches to a named watchlist."""

    model_config = ConfigDict(extra="forbid")

    watchlist_name: str


# In-memory watchlists store for demo/routing integration
_watchlist_store: dict[str, list[str]] = {}


def _get_default_runner() -> PointInTimeScreenerRunner:
    # Default fallback runner returning empty bars if not overridden
    def empty_bar_provider(seg: str, sec: str, dt: Any, lookback: int) -> list[BarRecord]:
        return []

    return PointInTimeScreenerRunner(bar_provider=empty_bar_provider)


@router.post(
    "/api/v1/screeners",
    response_model=ScreenerRecord,
    status_code=201,
)
@router.post(
    "/api/screeners",
    response_model=ScreenerRecord,
    status_code=201,
    include_in_schema=False,
)
def create_screener(req: CreateScreenerRequest) -> ScreenerRecord:
    """Create and persist a new screener definition."""
    return screener_store.create_screener(req.definition, schedule=req.schedule)


@router.get(
    "/api/v1/screeners",
    response_model=list[ScreenerRecord],
)
@router.get(
    "/api/screeners",
    response_model=list[ScreenerRecord],
    include_in_schema=False,
)
def list_screeners() -> list[ScreenerRecord]:
    """List all saved screener definitions."""
    return screener_store.list_screeners()


@router.get(
    "/api/v1/screeners/{screener_id}",
    response_model=ScreenerRecord,
)
@router.get(
    "/api/screeners/{screener_id}",
    response_model=ScreenerRecord,
    include_in_schema=False,
)
def get_screener(screener_id: str) -> ScreenerRecord:
    """Retrieve a screener definition by ID."""
    rec = screener_store.get_screener(screener_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Screener '{screener_id}' not found")
    return rec


@router.delete(
    "/api/v1/screeners/{screener_id}",
    status_code=204,
)
@router.delete(
    "/api/screeners/{screener_id}",
    status_code=204,
    include_in_schema=False,
)
def delete_screener(screener_id: str) -> None:
    """Delete a screener definition by ID."""
    if not screener_store.delete_screener(screener_id):
        raise HTTPException(status_code=404, detail=f"Screener '{screener_id}' not found")


@router.post(
    "/api/v1/screeners/{screener_id}/run",
    response_model=ScreenerRunSnapshot,
)
@router.post(
    "/api/screeners/{screener_id}/run",
    response_model=ScreenerRunSnapshot,
    include_in_schema=False,
)
def run_screener(screener_id: str) -> ScreenerRunSnapshot:
    """Execute screener and save immutable run snapshot."""
    rec = screener_store.get_screener(screener_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Screener '{screener_id}' not found")

    runner = _get_default_runner()
    result = runner.run(rec.definition)
    return screener_store.save_run_snapshot(
        screener_id=rec.id,
        screener_name=rec.name,
        result=result,
    )


@router.get(
    "/api/v1/screeners/{screener_id}/runs",
    response_model=list[ScreenerRunSnapshot],
)
@router.get(
    "/api/screeners/{screener_id}/runs",
    response_model=list[ScreenerRunSnapshot],
    include_in_schema=False,
)
def list_screener_runs(screener_id: str) -> list[ScreenerRunSnapshot]:
    """List historical run snapshots for a screener."""
    rec = screener_store.get_screener(screener_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Screener '{screener_id}' not found")
    return screener_store.list_runs_for_screener(screener_id)


@router.get(
    "/api/v1/screeners/runs/{run_id}",
    response_model=ScreenerRunSnapshot,
)
@router.get(
    "/api/screeners/runs/{run_id}",
    response_model=ScreenerRunSnapshot,
    include_in_schema=False,
)
def get_run_snapshot(run_id: str) -> ScreenerRunSnapshot:
    """Retrieve single run snapshot by run ID."""
    snapshot = screener_store.get_run_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Run snapshot '{run_id}' not found")
    return snapshot


@router.post(
    "/api/v1/screeners/runs/{run_id}/export",
)
@router.post(
    "/api/screeners/runs/{run_id}/export",
    include_in_schema=False,
)
def export_run(
    run_id: str,
    format: Literal["csv", "json"] = Query(default="csv"),
) -> Response:
    """Export run snapshot matches to CSV or JSON format."""
    snapshot = screener_store.get_run_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Run snapshot '{run_id}' not found")

    if format == "csv":
        content = export_screener_csv(snapshot.result)
        return Response(content=content, media_type="text/csv")
    else:
        content = export_screener_json(snapshot.result)
        return Response(content=content, media_type="application/json")


@router.post(
    "/api/v1/screeners/runs/{run_id}/route-watchlist",
    response_model=dict[str, Any],
)
@router.post(
    "/api/screeners/runs/{run_id}/route-watchlist",
    response_model=dict[str, Any],
    include_in_schema=False,
)
def route_run_to_watchlist(run_id: str, req: RouteWatchlistRequest) -> dict[str, Any]:
    """Route matched symbols into a designated watchlist."""
    snapshot = screener_store.get_run_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Run snapshot '{run_id}' not found")

    routed_ids = route_to_watchlist(
        snapshot.result, req.watchlist_name, watchlist_store=_watchlist_store
    )
    return {
        "watchlist_name": req.watchlist_name,
        "routed_count": len(routed_ids),
        "security_ids": routed_ids,
    }


@router.post(
    "/api/v1/screeners/runs/{run_id}/route-universe",
    response_model=StaticUniverse,
)
@router.post(
    "/api/screeners/runs/{run_id}/route-universe",
    response_model=StaticUniverse,
    include_in_schema=False,
)
def route_run_to_universe(run_id: str) -> StaticUniverse:
    """Transform screener matches into a valid StrategyIR StaticUniverse."""
    snapshot = screener_store.get_run_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Run snapshot '{run_id}' not found")
    if not snapshot.result.matches:
        raise HTTPException(status_code=400, detail="Cannot route empty matches to StaticUniverse")

    return route_to_static_universe(snapshot.result)
