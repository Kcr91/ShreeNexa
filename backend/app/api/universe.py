"""REST API endpoints for index constituent universe and point-in-time membership."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.marketdata.universe import (
    IndexConstituentRecord,
    IndexMembershipResult,
    ManualOverrideRequest,
    apply_manual_override,
    get_constituents_at_date,
    ingest_fallback_constituents,
    is_member_at_date,
    list_available_indices,
)

router = APIRouter(prefix="/api/v1/indices", tags=["indices"])


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


@router.get("", response_model=list[str])
def get_indices(engine: DbEngineDep) -> list[str]:
    """List all available indices currently present in the database."""
    return list_available_indices(engine)


@router.get("/{index_name}/constituents", response_model=list[IndexConstituentRecord])
def get_index_constituents(
    engine: DbEngineDep,
    index_name: str,
    as_of: Annotated[
        str | None, Query(description="Historical date as of (YYYY-MM-DD); defaults to latest")
    ] = None,
) -> list[IndexConstituentRecord]:
    """Retrieve effective constituents for an index as of a specific date with provenance."""
    return get_constituents_at_date(engine, index_name=index_name, as_of=as_of)


@router.get("/{index_name}/membership", response_model=IndexMembershipResult)
def check_index_membership(
    engine: DbEngineDep,
    index_name: str,
    symbol: Annotated[str, Query(description="Stock symbol (e.g. RELIANCE, INFY)")],
    as_of: Annotated[
        str | None, Query(description="Historical date as of (YYYY-MM-DD); defaults to latest")
    ] = None,
) -> IndexMembershipResult:
    """Verify point-in-time membership of a stock symbol in an index as of date."""
    return is_member_at_date(engine, index_name=index_name, symbol=symbol, as_of=as_of)


@router.post("/{index_name}/override")
def override_constituent(
    engine: DbEngineDep,
    index_name: str,
    payload: ManualOverrideRequest,
) -> dict[str, str]:
    """Apply a manual constituent addition or deletion override with visible provenance."""
    if payload.index_name != index_name:
        raise HTTPException(
            status_code=400,
            detail=f"Path index '{index_name}' does not match body index '{payload.index_name}'",
        )
    apply_manual_override(
        engine,
        index_name=index_name,
        symbol=payload.symbol,
        is_member=payload.is_member,
        effective_date=payload.effective_date,
        weight=payload.weight,
        sector=payload.sector,
    )
    action = "added/updated" if payload.is_member else "removed"
    return {
        "status": "success",
        "message": f"Symbol '{payload.symbol}' successfully {action} in index '{index_name}'",
    }


@router.post("/seed-fallback")
def seed_fallback(engine: DbEngineDep) -> dict[str, Any]:
    """Seed committed fallback index constituent snapshots into the database."""
    count = ingest_fallback_constituents(engine)
    return {
        "status": "success",
        "records_ingested": count,
    }
