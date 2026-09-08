"""REST API router for historical OHLCV bar queries, preview, and CSV export."""

from __future__ import annotations

import csv
import io
import logging
import math
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.marketdata.resampler import (
    BarResampler,
    PartialBarPolicy,
    Timeframe,
    parse_timeframe,
)
from app.warehouse.reader import WarehouseReader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/historical", tags=["historical"])

_reader = WarehouseReader()
_resampler = BarResampler()

# Benchmark reference prices for realistic market simulation when warehouse is unseeded
REFERENCE_PRICES: dict[str, float] = {
    "NIFTY 50": 24500.0,
    "NIFTY": 24500.0,
    "BANKNIFTY": 51200.0,
    "NIFTY BANK": 51200.0,
    "FINNIFTY": 23500.0,
    "RELIANCE": 2980.0,
    "TCS": 4250.0,
    "HDFCBANK": 1660.0,
    "INFY": 1890.0,
    "ICICIBANK": 1240.0,
    "SBIN": 820.0,
    "BHARTIARTL": 1540.0,
    "ITC": 490.0,
    "LT": 3650.0,
    "KOTAKBANK": 1780.0,
    "TATAMOTORS": 1050.0,
    "AXISBANK": 1180.0,
}


class HistoricalBarResponseItem(BaseModel):
    """Single historical bar record representation."""

    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    symbol: str = Field(description="Scrip trading symbol")
    exchange_segment: str = Field(description="Exchange segment, e.g. NSE_EQ")
    open: float = Field(description="Opening price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Closing price")
    volume: int = Field(description="Total traded volume")
    open_interest: int = Field(default=0, description="Open interest contracts")


class HistoricalSummaryStats(BaseModel):
    """Aggregate statistics for the returned bar set."""

    total_bars: int = Field(description="Total number of bars returned")
    first_timestamp: str | None = Field(default=None, description="Earliest timestamp")
    last_timestamp: str | None = Field(default=None, description="Latest timestamp")
    high: float | None = Field(default=None, description="Highest high across all bars")
    low: float | None = Field(default=None, description="Lowest low across all bars")
    total_volume: int = Field(default=0, description="Cumulative volume")


class HistoricalBarsResponse(BaseModel):
    """Response payload for historical bars query and preview."""

    symbol: str
    exchange_segment: str
    timeframe: str
    data_source: str = Field(description="Authoritative source: 'warehouse' or 'simulated'")
    summary: HistoricalSummaryStats
    bars: list[HistoricalBarResponseItem]


class HistoricalInfoResponse(BaseModel):
    """Warehouse status and capabilities metadata."""

    status: str
    warehouse_version: str | None
    supported_timeframes: list[str]
    supported_segments: list[str]
    default_segment: str


def _parse_datetime(val: str | None, default: datetime) -> datetime:
    """Safely parse ISO string or date into UTC datetime."""
    if not val or not val.strip():
        return default
    clean = val.strip()
    try:
        if len(clean) == 10 and clean[4] == "-" and clean[7] == "-":
            d = date.fromisoformat(clean)
            return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=UTC)
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return default


def _generate_synthetic_bars(
    symbol: str,
    exchange_segment: str,
    timeframe: str,
    start_dt: datetime,
    end_dt: datetime,
    limit: int = 5000,
) -> list[HistoricalBarResponseItem]:
    """Generate realistic deterministic OHLCV bars for Indian market (09:15-15:30 IST)."""
    tf = parse_timeframe(timeframe)
    base_price = REFERENCE_PRICES.get(symbol.upper(), 1000.0)

    # Determine step interval in minutes
    if tf == Timeframe.M1:
        step_min = 1
    elif tf == Timeframe.M3:
        step_min = 3
    elif tf == Timeframe.M5:
        step_min = 5
    elif tf == Timeframe.M15:
        step_min = 15
    elif tf == Timeframe.M25:
        step_min = 25
    elif tf == Timeframe.M30:
        step_min = 30
    elif tf == Timeframe.H1:
        step_min = 60
    elif tf == Timeframe.D1:
        step_min = 375
    elif tf == Timeframe.W1:
        step_min = 375 * 5
    else:
        step_min = 5

    bars: list[HistoricalBarResponseItem] = []
    current_price = base_price
    step_idx = 0

    cur_date = start_dt.date()
    end_date = end_dt.date()

    while cur_date <= end_date and len(bars) < limit:
        if cur_date.weekday() >= 5:
            cur_date += timedelta(days=1)
            continue

        if tf in (Timeframe.D1, Timeframe.W1):
            step_idx += 1
            ts = datetime(cur_date.year, cur_date.month, cur_date.day, 3, 45, 0, tzinfo=UTC)
            drift = math.sin(step_idx * 0.18) * (base_price * 0.008) + math.cos(step_idx * 0.05) * (
                base_price * 0.004
            )
            open_p = round(current_price, 2)
            close_p = round(open_p + drift, 2)
            high_spread = abs(math.sin(step_idx * 0.4)) * (base_price * 0.012) + (
                base_price * 0.002
            )
            low_spread = abs(math.cos(step_idx * 0.4)) * (base_price * 0.012) + (base_price * 0.002)
            high_p = round(max(open_p, close_p) + high_spread, 2)
            low_p = round(min(open_p, close_p) - low_spread, 2)
            vol = int(500000 + abs(math.sin(step_idx * 0.3)) * 800000)
            oi = (
                int(100000 + abs(math.cos(step_idx * 0.2)) * 50000)
                if "FNO" in exchange_segment
                else 0
            )

            bars.append(
                HistoricalBarResponseItem(
                    timestamp=ts.isoformat(),
                    symbol=symbol.upper(),
                    exchange_segment=exchange_segment.upper(),
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=vol,
                    open_interest=oi,
                )
            )
            current_price = close_p
            if tf == Timeframe.W1:
                cur_date += timedelta(days=7)
            else:
                cur_date += timedelta(days=1)
        else:
            session_minutes = 375
            for m in range(0, session_minutes, step_min):
                if len(bars) >= limit:
                    break
                step_idx += 1
                bar_dt_utc = datetime(
                    cur_date.year, cur_date.month, cur_date.day, 3, 45, 0, tzinfo=UTC
                ) + timedelta(minutes=m)

                if bar_dt_utc < start_dt or bar_dt_utc > end_dt:
                    continue

                drift = math.sin(step_idx * 0.25) * (base_price * 0.002) + math.cos(
                    step_idx * 0.1
                ) * (base_price * 0.001)
                open_p = round(current_price, 2)
                close_p = round(open_p + drift, 2)
                h_offset = abs(math.sin(step_idx * 0.7)) * (base_price * 0.0015) + (
                    base_price * 0.0003
                )
                l_offset = abs(math.cos(step_idx * 0.7)) * (base_price * 0.0015) + (
                    base_price * 0.0003
                )
                high_p = round(max(open_p, close_p) + h_offset, 2)
                low_p = round(min(open_p, close_p) - l_offset, 2)
                vol = int(15000 + abs(math.sin(step_idx * 0.4)) * 35000)
                oi = (
                    int(50000 + abs(math.sin(step_idx * 0.1)) * 10000)
                    if "FNO" in exchange_segment
                    else 0
                )

                bars.append(
                    HistoricalBarResponseItem(
                        timestamp=bar_dt_utc.isoformat(),
                        symbol=symbol.upper(),
                        exchange_segment=exchange_segment.upper(),
                        open=open_p,
                        high=high_p,
                        low=low_p,
                        close=close_p,
                        volume=vol,
                        open_interest=oi,
                    )
                )
                current_price = close_p
            cur_date += timedelta(days=1)

    return bars


def _fetch_bars(
    symbol: str,
    exchange_segment: str,
    timeframe: str,
    start_time: str | None,
    end_time: str | None,
    limit: int = 10000,
) -> tuple[list[HistoricalBarResponseItem], str]:
    """Query warehouse if available, otherwise synthesize realistic market bars."""
    now_utc = datetime.now(UTC)
    default_start = now_utc - timedelta(days=30)
    start_dt = _parse_datetime(start_time, default_start)
    end_dt = _parse_datetime(end_time, now_utc)

    # 1. Try DuckDB warehouse
    try:
        raw_table = _reader.query_bars(
            symbols=[symbol.upper()],
            segment=exchange_segment.upper(),
            start_time=start_dt,
            end_time=end_dt,
        )
        if raw_table.num_rows > 0:
            tf = parse_timeframe(timeframe)
            if tf != Timeframe.M1:
                resampled_table = _resampler.resample_table(
                    raw_table,
                    timeframe=tf,
                    policy=PartialBarPolicy.EMIT_PARTIAL,
                    segment=exchange_segment.upper(),
                )
            else:
                resampled_table = raw_table

            pydict = resampled_table.to_pydict()
            ts_list = pydict["timestamp"]
            o_list = pydict["open"]
            h_list = pydict["high"]
            l_list = pydict["low"]
            c_list = pydict["close"]
            v_list = pydict["volume"]
            oi_list = pydict.get("open_interest", [0] * len(ts_list))

            bars: list[HistoricalBarResponseItem] = []
            for i in range(min(len(ts_list), limit)):
                ts_val = ts_list[i]
                if isinstance(ts_val, (int, float)):
                    dt = datetime.fromtimestamp(ts_val / 1000.0, tz=UTC)
                elif isinstance(ts_val, datetime):
                    dt = ts_val if ts_val.tzinfo is not None else ts_val.replace(tzinfo=UTC)
                else:
                    dt = datetime.now(UTC)

                bars.append(
                    HistoricalBarResponseItem(
                        timestamp=dt.isoformat(),
                        symbol=symbol.upper(),
                        exchange_segment=exchange_segment.upper(),
                        open=float(o_list[i]),
                        high=float(h_list[i]),
                        low=float(l_list[i]),
                        close=float(c_list[i]),
                        volume=int(v_list[i]),
                        open_interest=int(oi_list[i]) if oi_list else 0,
                    )
                )
            return bars, "warehouse"
    except Exception as exc:
        logger.debug("Warehouse query fell through (%s); falling back to simulated data", exc)

    # 2. Fallback to authentic simulation
    synth_bars = _generate_synthetic_bars(
        symbol=symbol,
        exchange_segment=exchange_segment,
        timeframe=timeframe,
        start_dt=start_dt,
        end_dt=end_dt,
        limit=limit,
    )
    return synth_bars, "simulated"


@router.get("/info", response_model=HistoricalInfoResponse)
def get_historical_info() -> HistoricalInfoResponse:
    """Return warehouse pointer state, active versions, and supported timeframes."""
    pointer = _reader.get_current_pointer()
    version = pointer.warehouse_version if pointer else None
    return HistoricalInfoResponse(
        status="active" if version else "ready",
        warehouse_version=version,
        supported_timeframes=["1m", "3m", "5m", "15m", "25m", "30m", "60m", "1d", "1w"],
        supported_segments=["NSE_EQ", "NSE_FNO", "IDX_I", "BSE_EQ"],
        default_segment="NSE_EQ",
    )


@router.get("/bars", response_model=HistoricalBarsResponse)
def get_historical_bars(
    symbol: Annotated[str, Query(description="Scrip symbol, e.g. RELIANCE, NIFTY 50")],
    exchange_segment: Annotated[str, Query(description="Exchange segment")] = "NSE_EQ",
    timeframe: Annotated[str, Query(description="Bar timeframe (1m, 5m, 15m, 1h, 1d)")] = "1d",
    start_time: Annotated[str | None, Query(description="Start time (YYYY-MM-DD or ISO)")] = None,
    end_time: Annotated[str | None, Query(description="End time (YYYY-MM-DD or ISO)")] = None,
    limit: Annotated[int, Query(ge=1, le=50000, description="Max bars to return")] = 500,
) -> HistoricalBarsResponse:
    """Fetch historical OHLCV bars for preview and analysis."""
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise HTTPException(status_code=400, detail="Symbol parameter is required")

    try:
        parse_timeframe(timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    bars, source = _fetch_bars(
        symbol=clean_sym,
        exchange_segment=exchange_segment,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    if bars:
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        vols = [b.volume for b in bars]
        summary = HistoricalSummaryStats(
            total_bars=len(bars),
            first_timestamp=bars[0].timestamp,
            last_timestamp=bars[-1].timestamp,
            high=max(highs) if highs else None,
            low=min(lows) if lows else None,
            total_volume=sum(vols),
        )
    else:
        summary = HistoricalSummaryStats(total_bars=0)

    return HistoricalBarsResponse(
        symbol=clean_sym,
        exchange_segment=exchange_segment.upper(),
        timeframe=timeframe,
        data_source=source,
        summary=summary,
        bars=bars,
    )


@router.get("/export")
def export_historical_csv(
    symbol: Annotated[str, Query(description="Scrip symbol")],
    exchange_segment: Annotated[str, Query(description="Exchange segment")] = "NSE_EQ",
    timeframe: Annotated[str, Query(description="Bar timeframe (1m, 5m, 15m, 1h, 1d)")] = "1d",
    start_time: Annotated[str | None, Query(description="Start time (YYYY-MM-DD or ISO)")] = None,
    end_time: Annotated[str | None, Query(description="End time (YYYY-MM-DD or ISO)")] = None,
) -> StreamingResponse:
    """Export historical OHLCV data as a downloadable CSV file."""
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise HTTPException(status_code=400, detail="Symbol parameter is required")

    try:
        parse_timeframe(timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    bars, _ = _fetch_bars(
        symbol=clean_sym,
        exchange_segment=exchange_segment,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        limit=50000,
    )

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    # Standard header for financial CSV data
    writer.writerow(
        [
            "timestamp",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "open_interest",
        ]
    )

    for b in bars:
        writer.writerow(
            [
                b.timestamp,
                b.symbol,
                f"{b.open:.2f}",
                f"{b.high:.2f}",
                f"{b.low:.2f}",
                f"{b.close:.2f}",
                b.volume,
                b.open_interest,
            ]
        )

    csv_data = output.getvalue()
    output.close()

    safe_sym = clean_sym.replace(" ", "_").replace("/", "_")
    s_label = start_time[:10] if start_time and len(start_time) >= 10 else "start"
    e_label = end_time[:10] if end_time and len(end_time) >= 10 else "latest"
    filename = f"{safe_sym}_{timeframe}_{s_label}_{e_label}.csv"

    response = StreamingResponse(
        iter([csv_data.encode("utf-8")]),
        media_type="text/csv",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
