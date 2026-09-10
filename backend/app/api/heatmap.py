"""Heatmaps backed exclusively by verified Dhan quotes in the feedd hot cache."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.api.ws import get_market_data_fanout_manager
from app.contracts import heartbeat as hb
from app.dhan.instruments import instrument_table
from app.dhan.live_feed_service import DHAN_TO_SEGMENT
from app.feedd.cache import CachedQuote, MarketDataState
from app.marketdata.universe import IndexConstituentRecord, get_constituents_at_date

OFFICIAL_CONSTITUENTS_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "nifty_official_constituents.json"
)


def load_official_records_for_index(index_name: str) -> list[IndexConstituentRecord]:
    """Load identity and membership only from the checked-in NSE catalog."""
    if not OFFICIAL_CONSTITUENTS_PATH.is_file():
        return []
    try:
        with OFFICIAL_CONSTITUENTS_PATH.open(encoding="utf-8") as source:
            data = json.load(source)
    except OSError, json.JSONDecodeError:
        return []

    clean = index_name.upper().strip()
    entry = data.get(clean)
    if not entry or not entry.get("stocks"):
        return []
    stocks = entry["stocks"]
    return [
        IndexConstituentRecord(
            index_name=clean,
            symbol=str(stock.get("symbol", "")).strip().upper(),
            weight=None,
            sector=stock.get("industry") or entry.get("category") or "Equities",
            valid_from=date(2026, 1, 1),
            valid_to=None,
            source_date=date(2026, 9, 1),
            source="OFFICIAL_NSE",
        )
        for stock in stocks
        if str(stock.get("symbol", "")).strip()
    ]


router = APIRouter(prefix="/api/v1/heatmap", tags=["heatmap"])


def get_db_engine() -> Engine:
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


class MarketBreadth(BaseModel):
    total_count: int
    advances: int
    declines: int
    unchanged: int
    advance_decline_ratio: float
    pct_above_prev_close: float
    weighted_breadth: float
    sentiment_posture: str


class IndexHeatmapCell(BaseModel):
    index_name: str
    sector: str
    weight: float
    security_id: str | None = None
    segment: str | None = None
    change_pct: float | None = None
    ltp: float | None = None
    advances: int | None = None
    declines: int | None = None
    unchanged: int | None = None
    futures_basis: float | None = None
    oi_change_pct: float | None = None
    category: str = "SECTORAL"
    constituent_count: int | None = None
    weighting_source: str = "OFFICIAL_NSE"
    market_state: MarketDataState = "UNAVAILABLE"
    source: str | None = None
    received_at: float | None = None
    error: str | None = None


class ConstituentHeatmapCell(BaseModel):
    symbol: str
    sector: str
    weight: float
    security_id: str | None = None
    segment: str | None = None
    is_weight_fallback: bool = False
    weighting_source: str = "OFFICIAL_NSE"
    change_pct: float | None = None
    ltp: float | None = None
    previous_close: float | None = None
    volume: int | None = None
    market_state: MarketDataState = "UNAVAILABLE"
    source: str | None = None
    received_at: float | None = None
    error: str | None = None


class ConstituentHeatmapResponse(BaseModel):
    index_name: str
    breadth: MarketBreadth
    cell_total_weight: float
    market_state: MarketDataState
    error: str | None = None
    constituents: list[ConstituentHeatmapCell] = Field(default_factory=list)


# Static metadata is allowed; market values are always populated from Dhan.
INDEX_CATALOG: list[dict[str, Any]] = [
    {
        "index_name": "NIFTY 50",
        "sector": "Large Cap Benchmark",
        "weight": 25.0,
        "security_id": "13",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY BANK",
        "sector": "Banking",
        "weight": 20.0,
        "security_id": "25",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 12,
    },
    {
        "index_name": "NIFTY FIN SERVICE",
        "sector": "Financial Services",
        "weight": 15.0,
        "security_id": "27",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 20,
    },
    {
        "index_name": "NIFTY MID SELECT",
        "sector": "Mid Cap Select",
        "weight": 10.0,
        "security_id": "28",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 25,
    },
    {
        "index_name": "NIFTY IT",
        "sector": "Information Technology",
        "weight": 15.0,
        "security_id": "29",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 10,
    },
    {
        "index_name": "NIFTY AUTO",
        "sector": "Automotive",
        "weight": 10.0,
        "security_id": "30",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 15,
    },
]


def _change_pct(quote: CachedQuote) -> float | None:
    previous_close = quote.previous_close
    if quote.ltp is None or previous_close is None or previous_close == 0.0:
        return None
    return round((quote.ltp - previous_close) / previous_close * 100.0, 2)


def _quote_fields(quote: CachedQuote | None) -> dict[str, Any]:
    if quote is None:
        return {
            "market_state": "UNAVAILABLE",
            "error": "No verified Dhan quote is available",
        }
    return {
        "ltp": quote.ltp,
        "previous_close": quote.previous_close,
        "change_pct": _change_pct(quote),
        "volume": quote.volume,
        "market_state": quote.market_state,
        "source": quote.source,
        "received_at": quote.received_at,
        "error": quote.error,
    }


@router.get("/indices", response_model=list[IndexHeatmapCell])
def get_index_heatmap(category: str | None = None) -> list[IndexHeatmapCell]:
    """Return direct Dhan index levels; only percentage/color inputs are derived."""
    selected = INDEX_CATALOG
    if category:
        clean = category.strip().upper()
        selected = [item for item in selected if item["category"] == clean]
    instruments = [(str(item["segment"]), str(item["security_id"])) for item in selected]
    cache = get_market_data_fanout_manager().hot_cache
    quotes = cache.get_multi_quotes(instruments)
    cells: list[IndexHeatmapCell] = []
    for item in selected:
        instrument = (str(item["segment"]), str(item["security_id"]))
        fields = _quote_fields(quotes.get(instrument))
        fields.pop("previous_close", None)
        fields.pop("volume", None)
        cells.append(IndexHeatmapCell(**item, **fields))
    return cells


def _instrument_map(engine: Engine, symbols: list[str]) -> dict[str, tuple[str, str]]:
    if not symbols:
        return {}
    statement = select(
        instrument_table.c.symbol,
        instrument_table.c.exchange_segment,
        instrument_table.c.security_id,
    ).where(
        instrument_table.c.symbol.in_(symbols),
        instrument_table.c.exchange_segment.in_(["NSE_EQ", "BSE_EQ"]),
        instrument_table.c.is_active.is_(True),
    )
    resolved: dict[str, tuple[str, str]] = {}
    with engine.connect() as connection:
        for row in connection.execute(statement).mappings():
            segment = DHAN_TO_SEGMENT.get(str(row["exchange_segment"]))
            if segment is not None:
                resolved.setdefault(str(row["symbol"]).upper(), (segment, str(row["security_id"])))
    return resolved


@router.get("/{index_name}/constituents", response_model=ConstituentHeatmapResponse)
def get_constituent_heatmap(engine: DbEngineDep, index_name: str) -> ConstituentHeatmapResponse:
    """Return membership metadata plus direct Dhan constituent values."""
    records = get_constituents_at_date(engine, index_name=index_name)
    if not records:
        records = load_official_records_for_index(index_name)

    total_known = sum(float(record.weight) for record in records if record.weight)
    unweighted = [record for record in records if not record.weight]
    fallback_weight = 0.0
    if unweighted:
        remaining = max(0.0, 100.0 - total_known)
        fallback_weight = round(
            (remaining / len(unweighted)) if remaining else (100.0 / len(records)), 4
        )

    instruments = _instrument_map(engine, [record.symbol.upper() for record in records])
    requested = list(instruments.values())
    cache = get_market_data_fanout_manager().hot_cache
    quotes = cache.get_multi_quotes(requested)
    cells: list[ConstituentHeatmapCell] = []
    for record in records:
        symbol = record.symbol.upper()
        instrument = instruments.get(symbol)
        quote = quotes.get(instrument) if instrument else None
        is_fallback = not record.weight
        fields = _quote_fields(quote)
        cells.append(
            ConstituentHeatmapCell(
                symbol=symbol,
                sector=record.sector or "General",
                weight=round(float(record.weight) if record.weight else fallback_weight, 2),
                security_id=instrument[1] if instrument else None,
                segment=instrument[0] if instrument else None,
                is_weight_fallback=is_fallback,
                weighting_source="FALLBACK_EQUAL_WEIGHT" if is_fallback else "OFFICIAL_NSE",
                **fields,
            )
        )

    current_total = sum(cell.weight for cell in cells)
    if current_total and abs(current_total - 100.0) > 0.01:
        scale = 100.0 / current_total
        for cell in cells:
            cell.weight = round(cell.weight * scale, 2)
        largest = max(range(len(cells)), key=lambda index: cells[index].weight)
        cells[largest].weight += round(100.0 - sum(cell.weight for cell in cells), 2)

    valued = [cell for cell in cells if cell.change_pct is not None]
    advances = sum(1 for cell in valued if cell.change_pct and cell.change_pct > 0)
    declines = sum(1 for cell in valued if cell.change_pct and cell.change_pct < 0)
    unchanged = sum(1 for cell in valued if cell.change_pct == 0)
    pct_positive = round(advances / len(valued) * 100.0, 1) if valued else 0.0
    weighted_breadth = round(
        sum(cell.weight * (cell.change_pct or 0.0) for cell in valued) / 100.0, 2
    )
    posture = (
        "Unavailable"
        if not valued
        else "Strong Bullish"
        if pct_positive >= 70
        else "Moderate Bullish"
        if pct_positive >= 55
        else "Neutral"
        if pct_positive >= 45
        else "Moderate Bearish"
        if pct_positive >= 30
        else "Strong Bearish"
    )
    states = {cell.market_state for cell in cells}
    overall: MarketDataState = (
        "LIVE"
        if "LIVE" in states
        else "MARKET_CLOSED"
        if "MARKET_CLOSED" in states
        else "STALE"
        if "STALE" in states
        else "ERROR"
        if "ERROR" in states
        else "UNAVAILABLE"
    )
    return ConstituentHeatmapResponse(
        index_name=index_name,
        breadth=MarketBreadth(
            total_count=len(valued),
            advances=advances,
            declines=declines,
            unchanged=unchanged,
            advance_decline_ratio=round(advances / max(declines, 1), 2),
            pct_above_prev_close=pct_positive,
            weighted_breadth=weighted_breadth,
            sentiment_posture=posture,
        ),
        cell_total_weight=round(sum(cell.weight for cell in cells), 2),
        market_state=overall,
        error=None if valued else "No verified Dhan constituent quotes are available",
        constituents=cells,
    )
