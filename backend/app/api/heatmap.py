"""Heatmaps backed exclusively by verified Dhan quotes in the feedd hot cache."""

from __future__ import annotations

import json
import time
from datetime import date
from decimal import Decimal
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
    except (OSError, json.JSONDecodeError):
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
            weight=Decimal(str(stock["weight"])) if stock.get("weight") is not None else None,
            sector=(
                stock.get("sector")
                or stock.get("industry")
                or entry.get("category")
                or "Equities"
            ),
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
    # Broad Market Indices
    {
        "index_name": "NIFTY 50",
        "sector": "Large Cap Benchmark",
        "weight": 35.0,
        "security_id": "13",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY NEXT 50",
        "sector": "Large Cap Emerging",
        "weight": 12.0,
        "security_id": "38",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY MIDCAP 50",
        "sector": "Mid Cap Select",
        "weight": 6.0,
        "security_id": "20",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY MIDCAP 100",
        "sector": "Mid Cap Core",
        "weight": 8.0,
        "security_id": "37",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 100,
    },
    {
        "index_name": "NIFTY MIDCAP 150",
        "sector": "Mid Cap Broad",
        "weight": 10.0,
        "security_id": "1",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 150,
    },
    {
        "index_name": "NIFTY SMALLCAP 50",
        "sector": "Small Cap High Growth",
        "weight": 4.0,
        "security_id": "22",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY SMALLCAP 100",
        "sector": "Small Cap Core",
        "weight": 5.0,
        "security_id": "5",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 100,
    },
    {
        "index_name": "NIFTY SMALLCAP 250",
        "sector": "Small Cap Broad",
        "weight": 6.0,
        "security_id": "3",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 250,
    },
    {
        "index_name": "NIFTY 100",
        "sector": "Top 100 Large Cap",
        "weight": 20.0,
        "security_id": "17",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 100,
    },
    {
        "index_name": "NIFTY 200",
        "sector": "Large & Mid Cap 200",
        "weight": 15.0,
        "security_id": "18",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 200,
    },
    {
        "index_name": "NIFTY 500",
        "sector": "Broad 500 Equities",
        "weight": 14.0,
        "security_id": "19",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 500,
    },
    {
        "index_name": "NIFTY MID SELECT",
        "sector": "Mid Cap Select",
        "weight": 10.0,
        "security_id": "442",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 25,
    },
    {
        "index_name": "NIFTY TOTAL MARKET",
        "sector": "Entire NSE Listed Market",
        "weight": 10.0,
        "security_id": "443",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 750,
    },
    {
        "index_name": "NIFTY MICROCAP 250",
        "sector": "Emerging Microcaps",
        "weight": 3.0,
        "security_id": "444",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 250,
    },
    {
        "index_name": "NIFTY LARGEMIDCAP 250",
        "sector": "Large & Mid Blend",
        "weight": 9.0,
        "security_id": "6",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 250,
    },
    {
        "index_name": "NIFTY MIDSML 400",
        "sector": "Mid & Small Aggregate",
        "weight": 7.0,
        "security_id": "7",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 400,
    },
    {
        "index_name": "NIFTY500 MULTICAP 50:25:25",
        "sector": "Balanced Multicap",
        "weight": 8.0,
        "security_id": "467",
        "segment": "0",
        "category": "BROAD_MARKET",
        "constituent_count": 500,
    },
    # Sectoral Indices
    {
        "index_name": "NIFTY AUTO",
        "sector": "Automotive",
        "weight": 8.0,
        "security_id": "14",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY BANK",
        "sector": "Banking",
        "weight": 28.0,
        "security_id": "25",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 12,
    },
    {
        "index_name": "NIFTY FIN SERVICE",
        "sector": "Financial Services",
        "weight": 22.0,
        "security_id": "27",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 20,
    },
    {
        "index_name": "NIFTY FINSRV25/50",
        "sector": "Financial Services Cap",
        "weight": 8.0,
        "security_id": "469",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 20,
    },
    {
        "index_name": "NIFTY FMCG",
        "sector": "Fast Moving Consumer Goods",
        "weight": 9.0,
        "security_id": "28",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY IT",
        "sector": "Information Technology",
        "weight": 14.0,
        "security_id": "29",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 10,
    },
    {
        "index_name": "NIFTY MEDIA",
        "sector": "Media & Entertainment",
        "weight": 3.0,
        "security_id": "30",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 10,
    },
    {
        "index_name": "NIFTY METAL",
        "sector": "Metals & Mining",
        "weight": 6.0,
        "security_id": "31",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 11,
    },
    {
        "index_name": "NIFTY PHARMA",
        "sector": "Pharmaceuticals",
        "weight": 8.0,
        "security_id": "32",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 20,
    },
    {
        "index_name": "NIFTY PSU BANK",
        "sector": "Public Sector Banks",
        "weight": 5.0,
        "security_id": "33",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 12,
    },
    {
        "index_name": "NIFTY REALTY",
        "sector": "Real Estate",
        "weight": 4.0,
        "security_id": "34",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 7,
    },
    {
        "index_name": "NIFTY PVT BANK",
        "sector": "Private Sector Banks",
        "weight": 12.0,
        "security_id": "15",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 10,
    },
    {
        "index_name": "NIFTY HEALTHCARE",
        "sector": "Healthcare & Diagnostics",
        "weight": 6.0,
        "security_id": "447",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 20,
    },
    {
        "index_name": "NIFTY CONSR DURBL",
        "sector": "Consumer Durables",
        "weight": 5.0,
        "security_id": "466",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY OIL AND GAS",
        "sector": "Oil Gas & Petroleum",
        "weight": 7.0,
        "security_id": "470",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY MIDSML HLTH",
        "sector": "Mid & Small Healthcare",
        "weight": 4.0,
        "security_id": "471",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 25,
    },
    {
        "index_name": "NIFTY FINSERVIEXBK",
        "sector": "Fin Services Ex Banks",
        "weight": 5.0,
        "security_id": "495",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY MS FIN SERV",
        "sector": "Mid & Small Fin Services",
        "weight": 4.0,
        "security_id": "819",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY MS IT TELCOM",
        "sector": "Mid & Small IT & Telecom",
        "weight": 4.0,
        "security_id": "821",
        "segment": "0",
        "category": "SECTORAL",
        "constituent_count": 20,
    },
    # Thematic Indices
    {
        "index_name": "NIFTY COMMODITIES",
        "sector": "Commodities Producers",
        "weight": 5.0,
        "security_id": "39",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY CONSUMPTION",
        "sector": "Domestic Consumption",
        "weight": 6.0,
        "security_id": "40",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY CPSE",
        "sector": "Central Public Sector",
        "weight": 4.0,
        "security_id": "45",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 12,
    },
    {
        "index_name": "NIFTY ENERGY",
        "sector": "Power, Oil & Gas",
        "weight": 7.0,
        "security_id": "42",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 10,
    },
    {
        "index_name": "NIFTY INFRA",
        "sector": "Infrastructure",
        "weight": 6.0,
        "security_id": "43",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY MNC",
        "sector": "Multinational Corporations",
        "weight": 5.0,
        "security_id": "44",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY PSE",
        "sector": "Public Sector Enterprises",
        "weight": 4.0,
        "security_id": "41",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 20,
    },
    {
        "index_name": "NIFTY SERV SECTOR",
        "sector": "Services Ecosystem",
        "weight": 6.0,
        "security_id": "46",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY100 LIQ 15",
        "sector": "Top 15 Liquid Stocks",
        "weight": 5.0,
        "security_id": "35",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY IND DIGITAL",
        "sector": "India Digital Transformation",
        "weight": 5.0,
        "security_id": "473",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY100 ESG",
        "sector": "ESG Compliant Leaders",
        "weight": 5.0,
        "security_id": "478",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 64,
    },
    {
        "index_name": "NIFTY INDIA MFG",
        "sector": "Make in India Manufacturing",
        "weight": 5.0,
        "security_id": "474",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY TATA 25 CAP",
        "sector": "Tata Conglomerate Group",
        "weight": 4.0,
        "security_id": "475",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 25,
    },
    {
        "index_name": "NIFTY MULTI MFG",
        "sector": "Multi-Cap Manufacturing",
        "weight": 4.0,
        "security_id": "476",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY MULTI INFRA",
        "sector": "Multi-Cap Infrastructure",
        "weight": 4.0,
        "security_id": "477",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY IND DEFENCE",
        "sector": "Defence & Aerospace",
        "weight": 4.0,
        "security_id": "493",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 15,
    },
    {
        "index_name": "NIFTY EV",
        "sector": "Electric Vehicles & Tech",
        "weight": 4.0,
        "security_id": "491",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY HOUSING",
        "sector": "Broad Housing Ecosystem",
        "weight": 4.0,
        "security_id": "814",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY IPO",
        "sector": "Recently Listed Enterprises",
        "weight": 3.0,
        "security_id": "816",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 25,
    },
    {
        "index_name": "NIFTY MOBILITY",
        "sector": "Future Transportation",
        "weight": 4.0,
        "security_id": "818",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY RURAL",
        "sector": "Rural India Transformation",
        "weight": 4.0,
        "security_id": "825",
        "segment": "0",
        "category": "THEMATIC",
        "constituent_count": 30,
    },
    # Strategy Indices
    {
        "index_name": "NIFTY ALPHA 50",
        "sector": "High Alpha Factor",
        "weight": 8.0,
        "security_id": "12",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY50 EQL WGT",
        "sector": "Equal Weighted Nifty 50",
        "weight": 10.0,
        "security_id": "485",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY100 EQUAL WEIGHT",
        "sector": "Equal Weighted Top 100",
        "weight": 8.0,
        "security_id": "10",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 100,
    },
    {
        "index_name": "NIFTY100 LOW VOLATILITY 30",
        "sector": "Low Volatility Factor",
        "weight": 7.0,
        "security_id": "11",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY200 MOMENTUM 30",
        "sector": "Momentum Factor",
        "weight": 8.0,
        "security_id": "480",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY200 ALPHA 30",
        "sector": "Alpha Factor 200",
        "weight": 7.0,
        "security_id": "481",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY ALPHALOWVOL",
        "sector": "Alpha + Low Volatility",
        "weight": 6.0,
        "security_id": "482",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY200 QUALITY 30",
        "sector": "Quality Factor 200",
        "weight": 7.0,
        "security_id": "490",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 30,
    },
    {
        "index_name": "NIFTY500 VALUE 50",
        "sector": "Enhanced Value 50",
        "weight": 6.0,
        "security_id": "840",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY500 MOMENTUM 50",
        "sector": "Broad 500 Momentum",
        "weight": 7.0,
        "security_id": "498",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 50,
    },
    {
        "index_name": "NIFTY HIGH BETA 50",
        "sector": "High Beta 50",
        "weight": 5.0,
        "security_id": "813",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 50,
    },
    {
        "index_name": "INDIA VIX",
        "sector": "Market Volatility Gauge",
        "weight": 5.0,
        "security_id": "21",
        "segment": "0",
        "category": "STRATEGY",
        "constituent_count": 1,
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
    cache.request_subscriptions(instruments)
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
        instrument_table.c.exchange_segment == "NSE_EQ",
        instrument_table.c.is_active.is_(True),
    )
    resolved: dict[str, tuple[str, str]] = {}
    with engine.connect() as connection:
        for row in connection.execute(statement).mappings():
            sym = str(row["symbol"]).upper()
            resolved[sym] = ("1", str(row["security_id"]))

    # For any symbols still missing, resolve from the official NSE catalog
    missing = [s for s in symbols if s not in resolved]
    if missing and OFFICIAL_CONSTITUENTS_PATH.is_file():
        try:
            with OFFICIAL_CONSTITUENTS_PATH.open(encoding="utf-8") as source:
                cat_data = json.load(source)
            for entry in cat_data.values():
                for stock in entry.get("stocks", []):
                    st_sym = str(stock.get("symbol", "")).strip().upper()
                    sec_id = stock.get("securityId")
                    if st_sym in missing and st_sym not in resolved and sec_id:
                        resolved[st_sym] = ("1", str(sec_id))
        except Exception:
            pass

    return resolved


def _sync_quotes_on_demand(
    instruments: list[tuple[str, str]], cache: Any
) -> dict[tuple[str, str], CachedQuote]:
    """Fetch missing quotes synchronously from Dhan REST when cache is empty."""
    from app.dhan.client import DhanRestClient
    from app.dhan.credentials import resolve_dhan_credentials
    from app.dhan.live_feed_service import (
        _market_state_for_trade_time,
        _number,
        _quote_request_bodies,
    )

    creds = resolve_dhan_credentials()
    if not creds or not creds.access_token or not creds.client_id:
        return {}

    bodies = _quote_request_bodies(set(instruments))
    if not bodies:
        return {}

    fetched: dict[tuple[str, str], CachedQuote] = {}
    try:
        client = DhanRestClient(credentials=creds)
        for body in bodies:
            resp = client.get_quotes(body)
            for d_seg, s_quotes in resp.items():
                s_code = DHAN_TO_SEGMENT.get(str(d_seg))
                if s_code and isinstance(s_quotes, dict):
                    for sec_id, raw in s_quotes.items():
                        if isinstance(raw, dict):
                            ltp = _number(raw.get("last_price"))
                            net_change = _number(raw.get("net_change"))
                            prev_c = (
                                round(ltp - net_change, 2)
                                if (net_change is not None and ltp is not None)
                                else None
                            )
                            vol_raw = raw.get("volume")
                            vol = int(vol_raw) if vol_raw is not None else None
                            trade_time = raw.get("last_trade_time")
                            quote = CachedQuote(
                                segment=s_code,
                                security_id=str(sec_id),
                                ltp=ltp,
                                previous_close=prev_c,
                                volume=vol,
                                source="DHAN_REST",
                                received_at=time.time(),
                                market_state=_market_state_for_trade_time(
                                    trade_time, segment=s_code
                                ),
                            )
                            cache.set_quote(quote)
                            fetched[(s_code, str(sec_id))] = quote
    except Exception:
        pass
    return fetched


@router.get("/{index_name}/constituents", response_model=ConstituentHeatmapResponse)
def get_constituent_heatmap(engine: DbEngineDep, index_name: str) -> ConstituentHeatmapResponse:
    """Return membership metadata plus direct Dhan constituent values."""
    official_records = load_official_records_for_index(index_name)
    db_records = get_constituents_at_date(engine, index_name=index_name)

    # Use official records when they contain complete membership (e.g. 50 vs 15 in DB),
    # overlaying any specific weights from DB if present.
    if official_records and len(official_records) >= len(db_records):
        db_weights = {r.symbol.upper(): r.weight for r in db_records if r.weight is not None}
        records = []
        for rec in official_records:
            w = rec.weight if rec.weight is not None else db_weights.get(rec.symbol.upper())
            records.append(
                IndexConstituentRecord(
                    index_name=rec.index_name,
                    symbol=rec.symbol,
                    weight=w,
                    sector=rec.sector,
                    valid_from=rec.valid_from,
                    valid_to=rec.valid_to,
                    source_date=rec.source_date,
                    source=rec.source,
                )
            )
    else:
        records = db_records or official_records

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
    cache.request_subscriptions(requested)
    quotes = cache.get_multi_quotes(requested)
    if len(quotes) < len(requested):
        missing = [inst for inst in requested if inst not in quotes]
        fresh = _sync_quotes_on_demand(missing, cache)
        if fresh:
            quotes.update(fresh)
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
