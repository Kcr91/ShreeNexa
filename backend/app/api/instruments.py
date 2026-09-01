"""REST API routes for Dhan financial instrument master search and lookup."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.dhan.instruments import (
    InstrumentRecord,
    InstrumentSearchQuery,
    get_distinct_segments,
    get_expiries_for_underlying,
    get_instrument,
    get_option_chain_instruments,
    search_instruments,
)

router = APIRouter(prefix="/api/v1/instruments", tags=["instruments"])


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


@router.get("/search", response_model=list[InstrumentRecord])
def search(
    engine: DbEngineDep,
    query: Annotated[
        str | None,
        Query(description="Search prefix/substring against symbol, trading_symbol, or security_id"),
    ] = None,
    exchange_segment: Annotated[
        str | None, Query(description="Filter by exchange segment (e.g. NSE_EQ, NSE_FNO)")
    ] = None,
    instrument_type: Annotated[
        str | None, Query(description="Filter by instrument type (e.g. EQUITY, OPTIDX)")
    ] = None,
    underlying_id: Annotated[
        str | None, Query(description="Filter by underlying security ID")
    ] = None,
    expiry_date: Annotated[
        str | None, Query(description="Filter by expiry date (YYYY-MM-DD)")
    ] = None,
    strike_price: Annotated[Decimal | None, Query(description="Filter by strike price")] = None,
    option_type: Annotated[
        str | None, Query(description="Filter by option type (CE or PE)")
    ] = None,
    is_active_only: Annotated[bool, Query(description="Return only active instruments")] = True,
    limit: Annotated[int, Query(ge=1, le=500, description="Max results")] = 50,
    offset: Annotated[int, Query(ge=0, description="Result offset")] = 0,
) -> list[InstrumentRecord]:
    """Search instruments with filters across symbols, segments, types, and expiries."""
    search_query = InstrumentSearchQuery(
        query=query,
        exchange_segment=exchange_segment,
        instrument_type=instrument_type,
        underlying_id=underlying_id,
        expiry_date=expiry_date,
        strike_price=strike_price,
        option_type=option_type,
        is_active_only=is_active_only,
        limit=limit,
        offset=offset,
    )
    return search_instruments(engine, search_query)


@router.get("/segments", response_model=list[str])
def list_segments(engine: DbEngineDep) -> list[str]:
    """List all unique exchange segments dynamically present in the master."""
    return get_distinct_segments(engine)


@router.get("/options/chain", response_model=list[InstrumentRecord])
def get_option_chain(
    engine: DbEngineDep,
    underlying_id: Annotated[str, Query(description="Underlying security ID (e.g. 13 for NIFTY)")],
    expiry_date: Annotated[str, Query(description="Expiry date (YYYY-MM-DD)")],
    exchange_segment: Annotated[str, Query(description="Exchange segment")] = "NSE_FNO",
) -> list[InstrumentRecord]:
    """Retrieve all strike option contracts for an underlying on a given expiry date."""
    return get_option_chain_instruments(
        engine,
        underlying_id=underlying_id,
        expiry_date=expiry_date,
        exchange_segment=exchange_segment,
    )


@router.get("/options/expiries", response_model=list[date])
def get_expiries(
    engine: DbEngineDep,
    underlying_id: Annotated[str, Query(description="Underlying security ID")],
    exchange_segment: Annotated[str, Query(description="Exchange segment")] = "NSE_FNO",
) -> list[date]:
    """Retrieve distinct active expiry dates for an underlying security."""
    return get_expiries_for_underlying(
        engine,
        underlying_id=underlying_id,
        exchange_segment=exchange_segment,
    )


@router.get("/{exchange_segment}/{security_id}", response_model=InstrumentRecord)
def get_single_instrument(
    exchange_segment: str,
    security_id: str,
    engine: DbEngineDep,
) -> InstrumentRecord:
    """Retrieve a single instrument by exact exchange segment and security ID."""
    record = get_instrument(engine, exchange_segment=exchange_segment, security_id=security_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Instrument not found for '{exchange_segment}/{security_id}'",
        )
    return record
