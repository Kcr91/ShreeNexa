"""REST API endpoints for index constituent universe and point-in-time membership."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
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


class IndexDrillInSummary(BaseModel):
    """Aggregated index constituent drill-in with sector breakdown and visible provenance."""

    index_name: str
    as_of: str | None = None
    total_constituents: int
    has_fallback: bool = False
    provenance_sources: list[str] = Field(default_factory=list)
    sector_weights: dict[str, float] = Field(default_factory=dict)
    constituents: list[IndexConstituentRecord] = Field(default_factory=list)


SECTOR_CATALOG: list[dict[str, str]] = [
    {
        "index_name": "NIFTY BANK",
        "sector": "Banking",
        "description": "12 most liquid Indian banking stocks",
    },
    {
        "index_name": "NIFTY IT",
        "sector": "Information Technology",
        "description": "Top Indian IT software and services companies",
    },
    {
        "index_name": "NIFTY AUTO",
        "sector": "Automotive",
        "description": "Automobile OEMs and auto ancillaries",
    },
    {
        "index_name": "NIFTY PHARMA",
        "sector": "Pharmaceuticals",
        "description": "Pharmaceuticals and healthcare companies",
    },
    {
        "index_name": "NIFTY FMCG",
        "sector": "FMCG",
        "description": "Fast Moving Consumer Goods manufacturers",
    },
    {
        "index_name": "NIFTY METAL",
        "sector": "Metals & Mining",
        "description": "Steel, aluminum, and mining producers",
    },
    {
        "index_name": "NIFTY ENERGY",
        "sector": "Energy",
        "description": "Petroleum, gas, power utilities, and renewables",
    },
    {
        "index_name": "NIFTY REALTY",
        "sector": "Real Estate",
        "description": "Real estate developers and infrastructure",
    },
    {
        "index_name": "NIFTY 50",
        "sector": "Diversified Large Cap",
        "description": "Flagship 50 Indian blue chip companies",
    },
    {
        "index_name": "NIFTY NEXT 50",
        "sector": "Diversified Large Cap",
        "description": "Next 50 large cap companies (Nifty 51-100)",
    },
]


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


@router.get("/sectors/catalog")
def get_sector_catalog() -> list[dict[str, str]]:
    """Return catalog of recognized Indian market sectors and corresponding indices."""
    return SECTOR_CATALOG


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


@router.get("/{index_name}/drill-in", response_model=IndexDrillInSummary)
def get_index_drill_in(
    engine: DbEngineDep,
    index_name: str,
    as_of: Annotated[
        str | None, Query(description="Historical date as of (YYYY-MM-DD); defaults to latest")
    ] = None,
) -> IndexDrillInSummary:
    """Retrieve constituent drill-in summary with transparent provenance and sector distribution."""
    records = get_constituents_at_date(engine, index_name=index_name, as_of=as_of)
    sources = sorted(list({r.source for r in records}))
    has_fallback = any("FALLBACK" in r.source.upper() for r in records)

    sector_weights: dict[str, float] = {}
    for r in records:
        sec = r.sector or "Unclassified"
        wt = float(r.weight) if r.weight is not None else 0.0
        sector_weights[sec] = round(sector_weights.get(sec, 0.0) + wt, 2)

    return IndexDrillInSummary(
        index_name=index_name,
        as_of=as_of,
        total_constituents=len(records),
        has_fallback=has_fallback,
        provenance_sources=sources,
        sector_weights=sector_weights,
        constituents=records,
    )


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
