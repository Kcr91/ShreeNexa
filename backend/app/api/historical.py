"""REST API for historical OHLCV bar queries, coverage discovery, and CSV export.

This router previously fell back to `_generate_synthetic_bars` whenever the warehouse
returned nothing, seeded from a hardcoded price table. It labelled the response
`data_source: "simulated"`, but the CSV download carried no such marker - so an empty
warehouse produced fabricated candles that were indistinguishable from real data once
downloaded. A back-test fed that looks like it works.

An empty warehouse is now an explicit 404 naming what coverage exists instead.
"""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.contracts import heartbeat as hb
from app.marketdata.resampler import (
    BarResampler,
    PartialBarPolicy,
    Timeframe,
    parse_timeframe,
)
from app.warehouse.reader import WarehouseReader
from app.warehouse.report import build_report, missing_months
from app.worker.backfill_queue import bar_coverage_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/historical", tags=["historical"])

_reader = WarehouseReader()
_resampler = BarResampler()

Dataset = Literal["equity", "index", "futures", "options", "daily"]

SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "25m", "30m", "60m", "1d", "1w"]
SUPPORTED_SEGMENTS = ["NSE_EQ", "NSE_FNO", "BSE_EQ", "BSE_FNO", "IDX_I", "MCX_COMM"]

# Rows streamed per CSV chunk. A five-year 1-minute export is ~470k rows, which the
# previous implementation accumulated in a single StringIO before sending.
CSV_CHUNK_ROWS = 5000

CSV_HEADER = [
    "timestamp",
    "symbol",
    "exchange_segment",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "open_interest",
]


class CoverageUnavailableError(RuntimeError):
    """Raised when the coverage catalogue cannot be read at all."""


def get_db_engine() -> Engine:
    """Engine for coverage lookups, matching the pattern used by the other routers."""
    return hb.make_engine()


class HistoricalBarResponseItem(BaseModel):
    """Single historical bar record."""

    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    symbol: str = Field(description="Scrip trading symbol")
    exchange_segment: str = Field(description="Exchange segment, e.g. NSE_EQ")
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: int = Field(default=0, description="Open interest contracts")


class HistoricalSummaryStats(BaseModel):
    """Aggregate statistics for the returned bar set."""

    total_bars: int
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    high: float | None = None
    low: float | None = None
    total_volume: int = 0


class HistoricalBarsResponse(BaseModel):
    """Response payload for a historical bars query."""

    symbol: str
    exchange_segment: str
    timeframe: str
    data_source: str = Field(description="Always 'warehouse'; synthetic data is never served")
    summary: HistoricalSummaryStats
    bars: list[HistoricalBarResponseItem]


class CoverageItem(BaseModel):
    """What the warehouse actually holds for one series."""

    dataset: str
    symbol: str
    exchange_segment: str
    interval: str
    security_id: str | None = None
    underlying_symbol: str | None = None
    first_date: str | None = None
    last_date: str | None = None
    rows: int = 0
    last_verified_at: str | None = None


class CoverageResponse(BaseModel):
    """Coverage catalogue, driving the export UI's range and dataset controls."""

    symbol: str | None
    items: list[CoverageItem]
    total_series: int


class HistoricalInfoResponse(BaseModel):
    """Warehouse status and capabilities metadata."""

    status: str
    warehouse_version: str | None
    supported_timeframes: list[str]
    supported_segments: list[str]
    supported_datasets: list[str]
    default_segment: str


def _parse_datetime(val: str | None, default: datetime) -> datetime:
    """Parse an ISO string or plain date into an aware UTC datetime."""
    if not val or not val.strip():
        return default
    clean = val.strip()
    try:
        if len(clean) == 10 and clean[4] == "-" and clean[7] == "-":
            d = date.fromisoformat(clean)
            return datetime(d.year, d.month, d.day, tzinfo=UTC)
        dt = datetime.fromisoformat(clean)
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unparseable datetime {val!r}: {exc}") from exc


def _coverage_rows(
    symbol: str | None = None,
    dataset: str | None = None,
    interval: str | None = None,
) -> list[dict[str, Any]]:
    """Read the coverage catalogue written by the backfill runner."""
    t = bar_coverage_table
    stmt = select(t)
    conditions = []
    if symbol:
        conditions.append(t.c.symbol == symbol.upper())
    if dataset:
        conditions.append(t.c.dataset == dataset)
    if interval:
        conditions.append(t.c.interval == interval)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            return [
                dict(r) for r in conn.execute(stmt.order_by(t.c.symbol, t.c.interval)).mappings()
            ]
    except SQLAlchemyError as exc:
        # An unreachable catalogue is not the same as an empty one. Reporting "run the
        # backfill" during a database outage would be the same class of misleading
        # answer this router was rewritten to remove.
        logger.warning("Coverage lookup failed: %s", exc)
        raise CoverageUnavailableError(str(exc)) from exc


def _resolve_range(
    symbol: str,
    start_time: str | None,
    end_time: str | None,
    use_max: bool,
) -> tuple[datetime, datetime]:
    """Resolve the requested window, expanding 'max' from the coverage catalogue."""
    now = datetime.now(UTC)
    if not use_max:
        return (
            _parse_datetime(start_time, now - timedelta(days=30)),
            _parse_datetime(end_time, now),
        )

    try:
        rows = _coverage_rows(symbol=symbol)
    except CoverageUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Coverage catalogue unavailable, cannot resolve the maximum range: {exc}",
        ) from exc
    starts = [r["min_ts"] for r in rows if r.get("min_ts")]
    ends = [r["max_ts"] for r in rows if r.get("max_ts")]
    if not starts or not ends:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No coverage recorded for {symbol}; run the backfill before "
                "requesting the maximum available range."
            ),
        )
    return min(starts), max(ends)


def _fetch_bars(
    symbol: str,
    exchange_segment: str,
    timeframe: str,
    start_dt: datetime,
    end_dt: datetime,
    limit: int,
) -> list[HistoricalBarResponseItem]:
    """Query the warehouse and resample. Returns an empty list when nothing is held."""
    try:
        raw_table = _reader.query_bars(
            symbols=[symbol.upper()],
            segment=exchange_segment.upper(),
            start_time=start_dt,
            end_time=end_dt,
        )
    except FileNotFoundError:
        # No current pointer yet: the warehouse has never been published to.
        return []
    if raw_table.num_rows == 0:
        return []

    tf = parse_timeframe(timeframe)
    table = (
        raw_table
        if tf == Timeframe.M1
        else _resampler.resample_table(
            raw_table,
            timeframe=tf,
            policy=PartialBarPolicy.EMIT_PARTIAL,
            segment=exchange_segment.upper(),
        )
    )

    pydict = table.to_pydict()
    ts_list = pydict["timestamp"]
    oi_list = pydict.get("open_interest") or [0] * len(ts_list)

    bars: list[HistoricalBarResponseItem] = []
    for i in range(min(len(ts_list), limit)):
        ts_val = ts_list[i]
        if isinstance(ts_val, datetime):
            dt = ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=UTC)
        else:
            dt = datetime.fromtimestamp(float(ts_val) / 1000.0, tz=UTC)
        bars.append(
            HistoricalBarResponseItem(
                timestamp=dt.isoformat(),
                symbol=symbol.upper(),
                exchange_segment=exchange_segment.upper(),
                open=float(pydict["open"][i]),
                high=float(pydict["high"][i]),
                low=float(pydict["low"][i]),
                close=float(pydict["close"][i]),
                volume=int(pydict["volume"][i]),
                open_interest=int(oi_list[i]) if oi_list else 0,
            )
        )
    return bars


def _no_data(symbol: str, exchange_segment: str) -> HTTPException:
    """404 that names what is actually held, rather than inventing bars."""
    try:
        rows = _coverage_rows(symbol=symbol)
    except CoverageUnavailableError:
        # Still a 404 for the bars themselves; just do not claim to know why.
        return HTTPException(
            status_code=404,
            detail=(
                f"No bars for {symbol} ({exchange_segment}), and the coverage "
                "catalogue could not be read to say what is held."
            ),
        )
    if rows:
        held = ", ".join(
            f"{r['dataset']}/{r['interval']} "
            f"({_as_date(r.get('min_ts'))} to {_as_date(r.get('max_ts'))})"
            for r in rows
        )
        detail = f"No bars for {symbol} in the requested range. Available: {held}."
    else:
        detail = (
            f"No warehouse data for {symbol} ({exchange_segment}). "
            "Run the backfill for this symbol first."
        )
    return HTTPException(status_code=404, detail=detail)


def _as_date(value: Any) -> str:
    return value.date().isoformat() if isinstance(value, datetime) else "unknown"


@router.get("/info", response_model=HistoricalInfoResponse)
def get_historical_info() -> HistoricalInfoResponse:
    """Return warehouse pointer state and supported query dimensions."""
    pointer = _reader.get_current_pointer()
    version = pointer.warehouse_version if pointer else None
    return HistoricalInfoResponse(
        status="active" if version else "empty",
        warehouse_version=version,
        supported_timeframes=SUPPORTED_TIMEFRAMES,
        supported_segments=SUPPORTED_SEGMENTS,
        supported_datasets=["equity", "index", "futures", "options", "daily"],
        default_segment="NSE_EQ",
    )


@router.get("/coverage", response_model=CoverageResponse)
def get_coverage(
    symbol: Annotated[str | None, Query(description="Filter to one symbol")] = None,
    dataset: Annotated[str | None, Query(description="Filter to one dataset")] = None,
    interval: Annotated[str | None, Query(description="Filter to one interval")] = None,
) -> CoverageResponse:
    """Report what the warehouse actually holds, for range and dataset controls."""
    try:
        rows = _coverage_rows(symbol=symbol, dataset=dataset, interval=interval)
    except CoverageUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail=f"Coverage catalogue unavailable: {exc}"
        ) from exc
    items = [
        CoverageItem(
            dataset=str(r["dataset"]),
            symbol=str(r["symbol"]),
            exchange_segment=str(r["exchange_segment"]),
            interval=str(r["interval"]),
            security_id=r.get("security_id"),
            underlying_symbol=r.get("underlying_symbol"),
            first_date=_as_date(r.get("min_ts")) if r.get("min_ts") else None,
            last_date=_as_date(r.get("max_ts")) if r.get("max_ts") else None,
            rows=int(r.get("rows") or 0),
            last_verified_at=(
                r["last_verified_at"].isoformat() if r.get("last_verified_at") else None
            ),
        )
        for r in rows
    ]
    return CoverageResponse(
        symbol=symbol.upper() if symbol else None,
        items=items,
        total_series=len(items),
    )


@router.get("/bars", response_model=HistoricalBarsResponse)
def get_historical_bars(
    symbol: Annotated[str, Query(description="Scrip symbol, e.g. RELIANCE, NIFTY 50")],
    exchange_segment: Annotated[str, Query(description="Exchange segment")] = "NSE_EQ",
    timeframe: Annotated[str, Query(description="Bar timeframe")] = "1d",
    start_time: Annotated[str | None, Query(description="Start (YYYY-MM-DD or ISO)")] = None,
    end_time: Annotated[str | None, Query(description="End (YYYY-MM-DD or ISO)")] = None,
    range_mode: Annotated[str, Query(description="'explicit' or 'max'")] = "explicit",
    limit: Annotated[int, Query(ge=1, le=50000, description="Max bars")] = 500,
) -> HistoricalBarsResponse:
    """Fetch warehouse bars. Returns 404 rather than fabricating data when empty."""
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise HTTPException(status_code=400, detail="Symbol parameter is required")

    try:
        parse_timeframe(timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start_dt, end_dt = _resolve_range(
        clean_sym, start_time, end_time, use_max=range_mode.lower() == "max"
    )
    bars = _fetch_bars(clean_sym, exchange_segment, timeframe, start_dt, end_dt, limit)
    if not bars:
        raise _no_data(clean_sym, exchange_segment)

    summary = HistoricalSummaryStats(
        total_bars=len(bars),
        first_timestamp=bars[0].timestamp,
        last_timestamp=bars[-1].timestamp,
        high=max(b.high for b in bars),
        low=min(b.low for b in bars),
        total_volume=sum(b.volume for b in bars),
    )
    return HistoricalBarsResponse(
        symbol=clean_sym,
        exchange_segment=exchange_segment.upper(),
        timeframe=timeframe,
        data_source="warehouse",
        summary=summary,
        bars=bars,
    )


def _csv_stream(bars: list[HistoricalBarResponseItem]) -> Iterator[bytes]:
    """Yield CSV in chunks so a multi-hundred-thousand-row export is not buffered."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)

    for index, bar in enumerate(bars, start=1):
        writer.writerow(
            [
                bar.timestamp,
                bar.symbol,
                bar.exchange_segment,
                f"{bar.open:.2f}",
                f"{bar.high:.2f}",
                f"{bar.low:.2f}",
                f"{bar.close:.2f}",
                bar.volume,
                bar.open_interest,
            ]
        )
        if index % CSV_CHUNK_ROWS == 0:
            yield buffer.getvalue().encode("utf-8")
            buffer.seek(0)
            buffer.truncate(0)

    remainder = buffer.getvalue()
    if remainder:
        yield remainder.encode("utf-8")


@router.get("/export")
def export_historical_csv(
    symbol: Annotated[str, Query(description="Scrip symbol")],
    exchange_segment: Annotated[str, Query(description="Exchange segment")] = "NSE_EQ",
    timeframe: Annotated[str, Query(description="Bar timeframe")] = "1d",
    start_time: Annotated[str | None, Query(description="Start (YYYY-MM-DD or ISO)")] = None,
    end_time: Annotated[str | None, Query(description="End (YYYY-MM-DD or ISO)")] = None,
    range_mode: Annotated[str, Query(description="'explicit' or 'max'")] = "explicit",
) -> StreamingResponse:
    """Stream warehouse bars as CSV. Never emits synthetic rows."""
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise HTTPException(status_code=400, detail="Symbol parameter is required")

    try:
        parse_timeframe(timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start_dt, end_dt = _resolve_range(
        clean_sym, start_time, end_time, use_max=range_mode.lower() == "max"
    )
    bars = _fetch_bars(clean_sym, exchange_segment, timeframe, start_dt, end_dt, limit=50000)
    if not bars:
        raise _no_data(clean_sym, exchange_segment)

    safe_sym = clean_sym.replace(" ", "_").replace("/", "_")
    filename = (
        f"{safe_sym}_{timeframe}_{start_dt.date().isoformat()}_{end_dt.date().isoformat()}.csv"
    )
    response = StreamingResponse(_csv_stream(bars), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    # Declares provenance on the download itself, which the previous CSV did not.
    response.headers["X-ShreeNexa-Data-Source"] = "warehouse"
    return response


class ReportResponse(BaseModel):
    """Per-series, per-month download report."""

    generated_at: str
    totals: dict[str, Any]
    series_returned: int
    series: list[dict[str, Any]]


@router.get("/report", response_model=ReportResponse)
def get_historic_data_report(
    symbol: Annotated[str | None, Query(description="Filter to one symbol")] = None,
    dataset: Annotated[str | None, Query(description="equity/index/futures/options/daily")] = None,
    tier: Annotated[int | None, Query(ge=1, le=8, description="Backfill tier")] = None,
    suspect_only: Annotated[bool, Query(description="Only months flagged as unusual")] = False,
    limit_series: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> ReportResponse:
    """Report what has been downloaded month by month, and what looked unusual.

    Read from the backfill window ledger, so a month is reported as never fetched,
    fetched-and-empty, or fetched-with-anomalies as three distinct facts rather than
    being guessed from gaps in the bars.
    """
    try:
        data = build_report(
            get_db_engine(),
            symbol=symbol,
            dataset=dataset,
            tier=tier,
            suspect_only=suspect_only,
            limit_series=limit_series,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Backfill ledger unavailable: {exc}") from exc
    return ReportResponse(**data)


@router.get("/report/missing")
def get_missing_months(
    symbol: Annotated[str, Query(description="Symbol to inspect")],
    dataset: Annotated[str | None, Query(description="Restrict to one dataset")] = None,
) -> dict[str, Any]:
    """List the months of a symbol that have not been settled yet."""
    try:
        months = missing_months(get_db_engine(), symbol=symbol, dataset=dataset)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Backfill ledger unavailable: {exc}") from exc
    return {"symbol": symbol.upper(), "dataset": dataset, "missing_months": months}
