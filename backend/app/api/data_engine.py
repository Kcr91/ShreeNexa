"""FastAPI REST API router for the Data Engine & Market Storage Pipeline."""

from __future__ import annotations

import csv
import io
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.worker.data_engine.incremental_updater import IncrementalUpdater, SyncProgress
from app.worker.data_engine.models import (
    ApiQuotaRecord,
    DownloadStateRecord,
    OHLCVRecord,
    SegmentSummary,
    mkt_download_state_table,
    mkt_ohlcv_equity_table,
    mkt_ohlcv_futures_table,
    mkt_ohlcv_options_table,
)
from app.worker.data_engine.quota_manager import QuotaManager
from app.worker.data_engine.segment_seeder import (
    get_all_segments,
    get_segment_constituents,
    seed_nse_segments,
)

router = APIRouter(prefix="/api/v1/data", tags=["Data Engine & Storage"])

# Global singleton updater instance
_GLOBAL_UPDATER: IncrementalUpdater | None = None


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


def get_updater(engine: DbEngineDep) -> IncrementalUpdater:
    """Dependency providing the singleton incremental sync engine."""
    global _GLOBAL_UPDATER
    if _GLOBAL_UPDATER is None:
        _GLOBAL_UPDATER = IncrementalUpdater(engine=engine)
    return _GLOBAL_UPDATER


UpdaterDep = Annotated[IncrementalUpdater, Depends(get_updater)]


@router.get("/instruments", response_model=list[DownloadStateRecord])
def list_instruments(
    engine: DbEngineDep,
    segment: Annotated[
        str | None, Query(description="Filter by segment code (e.g. NSE_EQ, NSE_FNO)")
    ] = None,
    instrument_type: Annotated[
        str | None, Query(description="Filter by type (EQ, FUT, CE, PE)")
    ] = None,
    symbol: Annotated[str | None, Query(description="Search by symbol substring")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[DownloadStateRecord]:
    """List data engine tracked instruments with current download states."""
    stmt = select(mkt_download_state_table)
    if segment:
        stmt = stmt.where(mkt_download_state_table.c.exchange_segment == segment)
    if instrument_type:
        stmt = stmt.where(mkt_download_state_table.c.instrument_type == instrument_type.upper())
    if symbol:
        stmt = stmt.where(mkt_download_state_table.c.symbol.ilike(f"%{symbol}%"))

    stmt = stmt.order_by(mkt_download_state_table.c.symbol.asc()).limit(limit)

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()
        return [DownloadStateRecord.model_validate(dict(r._mapping)) for r in rows]


@router.get("/instruments/{symbol}", response_model=DownloadStateRecord)
def get_instrument_detail(
    engine: DbEngineDep,
    symbol: str,
    exchange_segment: str = "NSE_EQ",
) -> DownloadStateRecord:
    """Get detailed download state and last stored candle timestamp for a symbol."""
    stmt = select(mkt_download_state_table).where(
        mkt_download_state_table.c.symbol == symbol.upper(),
        mkt_download_state_table.c.exchange_segment == exchange_segment,
    )
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument '{symbol}' not found in download state registry",
            )
        return DownloadStateRecord.model_validate(dict(row._mapping))


@router.get("/candles/{symbol}", response_model=list[OHLCVRecord])
def get_candles(
    engine: DbEngineDep,
    symbol: str,
    type: Literal["EQ", "FUT", "CE", "PE"] = "EQ",
    from_date: Annotated[str | None, Query(description="Start date (YYYY-MM-DD)")] = None,
    to_date: Annotated[str | None, Query(description="End date (YYYY-MM-DD)")] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> list[OHLCVRecord]:
    """Retrieve historical 1-minute OHLCV candles from PostgreSQL."""
    table = (
        mkt_ohlcv_equity_table
        if type == "EQ"
        else (mkt_ohlcv_futures_table if type == "FUT" else mkt_ohlcv_options_table)
    )
    stmt = select(table).where(table.c.symbol == symbol.upper())
    if from_date:
        stmt = stmt.where(
            table.c.datetime_ist >= datetime.fromisoformat(from_date).replace(tzinfo=UTC)
        )
    if to_date:
        stmt = stmt.where(
            table.c.datetime_ist <= datetime.fromisoformat(to_date).replace(tzinfo=UTC)
        )

    stmt = stmt.order_by(table.c.datetime_ist.asc()).limit(limit)

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()
        return [OHLCVRecord.model_validate(dict(r._mapping)) for r in rows]


@router.get("/segments", response_model=list[SegmentSummary])
def get_segments(engine: DbEngineDep) -> list[SegmentSummary]:
    """List all 27 NSE segments with constituent counts."""
    segments = get_all_segments(engine)
    if not segments:
        # Seed if empty
        seed_nse_segments(engine)
        segments = get_all_segments(engine)
    return segments


@router.get("/segments/{code}/stocks", response_model=list[str])
def get_segment_stocks(engine: DbEngineDep, code: str) -> list[str]:
    """Get all constituent stock symbols belonging to a segment code."""
    return get_segment_constituents(engine, code)


@router.post("/sync/start")
def start_sync(
    updater: UpdaterDep,
    background_tasks: BackgroundTasks,
    symbols: list[str] | None = None,
) -> dict[str, str]:
    """Trigger manual background incremental sync job."""
    background_tasks.add_task(updater.sync_universe, symbols)
    return {"status": "started", "message": "Incremental sync task initiated"}


@router.post("/sync/pause")
def pause_sync(updater: UpdaterDep) -> dict[str, str]:
    """Pause currently executing incremental sync job."""
    updater.pause()
    return {"status": "paused", "message": "Incremental sync task paused"}


@router.post("/sync/resume")
def resume_sync(updater: UpdaterDep, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Resume paused incremental sync job."""
    updater.resume()
    background_tasks.add_task(updater.sync_universe)
    return {"status": "resumed", "message": "Incremental sync task resumed"}


@router.get("/sync/status", response_model=SyncProgress)
def get_sync_status(updater: UpdaterDep) -> SyncProgress:
    """Retrieve live progress of the incremental sync engine."""
    return updater.get_progress()


@router.get("/quota", response_model=ApiQuotaRecord)
def get_api_quota(engine: DbEngineDep) -> ApiQuotaRecord:
    """Get today's API budget ledger (limit, historical used, live used, remaining)."""
    qm = QuotaManager(db_engine=engine)
    return qm.get_quota_status()


@router.get("/export")
def export_csv(
    engine: DbEngineDep,
    symbol: str,
    type: Literal["EQ", "FUT", "CE", "PE"] = "EQ",
    from_date: Annotated[
        str | None, Query(alias="from", description="Start date (YYYY-MM-DD)")
    ] = None,
    to_date: Annotated[str | None, Query(alias="to", description="End date (YYYY-MM-DD)")] = None,
) -> StreamingResponse:
    """Stream OHLCV historical candle records as a downloadable CSV file."""
    table = (
        mkt_ohlcv_equity_table
        if type == "EQ"
        else (mkt_ohlcv_futures_table if type == "FUT" else mkt_ohlcv_options_table)
    )
    stmt = select(table).where(table.c.symbol == symbol.upper())
    if from_date:
        stmt = stmt.where(
            table.c.datetime_ist >= datetime.fromisoformat(from_date).replace(tzinfo=UTC)
        )
    if to_date:
        stmt = stmt.where(
            table.c.datetime_ist <= datetime.fromisoformat(to_date).replace(tzinfo=UTC)
        )

    stmt = stmt.order_by(table.c.datetime_ist.asc())

    def csv_generator() -> Generator[str]:
        output = io.StringIO()
        writer = csv.writer(output)
        # Header
        headers = ["datetime_ist", "open", "high", "low", "close", "volume"]
        if type in ["FUT", "CE", "PE"]:
            headers.append("oi")
        if type in ["CE", "PE"]:
            headers.append("iv")
        if type in ["FUT", "CE", "PE"]:
            headers.append("underlying_spot")

        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        with engine.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                r_dict = dict(row._mapping)
                row_vals = [
                    r_dict["datetime_ist"].isoformat() if r_dict.get("datetime_ist") else "",
                    r_dict.get("open", ""),
                    r_dict.get("high", ""),
                    r_dict.get("low", ""),
                    r_dict.get("close", ""),
                    r_dict.get("volume", ""),
                ]
                if "oi" in headers:
                    row_vals.append(r_dict.get("oi", ""))
                if "iv" in headers:
                    row_vals.append(r_dict.get("iv", ""))
                if "underlying_spot" in headers:
                    row_vals.append(r_dict.get("underlying_spot", ""))

                writer.writerow(row_vals)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    filename = f"{symbol}_{type}_{from_date or 'start'}_to_{to_date or 'now'}.csv"
    return StreamingResponse(
        csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
