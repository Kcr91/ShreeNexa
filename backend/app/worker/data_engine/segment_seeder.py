"""Catalog and seeder for 27 NSE segment groups (indices, sectors, and F&O 208 stocks)."""

from __future__ import annotations

import logging

from app.worker.data_engine.models import (
    SegmentSummary,
    mkt_segment_constituent_table,
    mkt_segment_table,
)
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# 27 Recognized NSE Segments
NSE_SEGMENTS_CATALOG: list[dict[str, str]] = [
    # Benchmark / Broad Market Indices
    {
        "code": "INDEX_NIFTY50",
        "name": "Nifty 50",
        "category": "INDEX",
        "description": "Top 50 Indian blue chip companies",
    },
    {
        "code": "INDEX_NIFTY_NEXT50",
        "name": "Nifty Next 50",
        "category": "INDEX",
        "description": "Next 50 large cap companies (51-100)",
    },
    {
        "code": "INDEX_NIFTY500",
        "name": "Nifty 500",
        "category": "INDEX",
        "description": "Top 500 companies representing 96% market cap",
    },
    {
        "code": "INDEX_NIFTY_MIDCAP150",
        "name": "Nifty Midcap 150",
        "category": "INDEX",
        "description": "Midcap segment 101-250",
    },
    {
        "code": "INDEX_NIFTY_SMALLCAP250",
        "name": "Nifty Smallcap 250",
        "category": "INDEX",
        "description": "Smallcap segment 251-500",
    },
    {
        "code": "INDEX_NIFTY_MIDSMALLCAP400",
        "name": "Nifty MidSmallcap 400",
        "category": "INDEX",
        "description": "Combined Midcap 150 and Smallcap 250",
    },
    {
        "code": "INDEX_BANKNIFTY",
        "name": "Nifty Bank",
        "category": "INDEX",
        "description": "12 most liquid Indian banking stocks",
    },
    {
        "code": "INDEX_FINNIFTY",
        "name": "Nifty Financial Services",
        "category": "INDEX",
        "description": "20 financial services companies",
    },
    {
        "code": "INDEX_MIDCPNIFTY",
        "name": "Nifty Midcap Select",
        "category": "INDEX",
        "description": "Top 25 liquid midcap derivatives stocks",
    },
    {
        "code": "INDEX_SENSEX",
        "name": "BSE Sensex 30",
        "category": "INDEX",
        "description": "Flagship 30 BSE blue chip companies",
    },
    {
        "code": "INDEX_SENSEX50",
        "name": "BSE Sensex 50",
        "category": "INDEX",
        "description": "Top 50 BSE listed companies",
    },
    # F&O Universe
    {
        "code": "FNO_208",
        "name": "NSE F&O Universe",
        "category": "EQUITY",
        "description": "All 208 NSE derivatives-eligible equities",
    },
    # Sectoral Indices
    {
        "code": "SECTOR_BANK",
        "name": "Nifty Bank Sector",
        "category": "SECTOR",
        "description": "Banking sector leaders",
    },
    {
        "code": "SECTOR_IT",
        "name": "Nifty IT Sector",
        "category": "SECTOR",
        "description": "Information technology & software",
    },
    {
        "code": "SECTOR_AUTO",
        "name": "Nifty Auto Sector",
        "category": "SECTOR",
        "description": "Automobiles & auto ancillaries",
    },
    {
        "code": "SECTOR_PHARMA",
        "name": "Nifty Pharma Sector",
        "category": "SECTOR",
        "description": "Pharmaceuticals & healthcare",
    },
    {
        "code": "SECTOR_METAL",
        "name": "Nifty Metal Sector",
        "category": "SECTOR",
        "description": "Metals, mining & steel",
    },
    {
        "code": "SECTOR_ENERGY",
        "name": "Nifty Energy Sector",
        "category": "SECTOR",
        "description": "Oil, gas, power & renewables",
    },
    {
        "code": "SECTOR_FMCG",
        "name": "Nifty FMCG Sector",
        "category": "SECTOR",
        "description": "Fast-moving consumer goods",
    },
    {
        "code": "SECTOR_REALTY",
        "name": "Nifty Realty Sector",
        "category": "SECTOR",
        "description": "Real estate & construction",
    },
    {
        "code": "SECTOR_MEDIA",
        "name": "Nifty Media Sector",
        "category": "SECTOR",
        "description": "Media, broadcasting & entertainment",
    },
    {
        "code": "SECTOR_HEALTHCARE",
        "name": "Nifty Healthcare Sector",
        "category": "SECTOR",
        "description": "Hospitals, diagnostics & healthcare",
    },
    {
        "code": "SECTOR_INFRA",
        "name": "Nifty Infra Sector",
        "category": "SECTOR",
        "description": "Infrastructure, logistics & capital goods",
    },
    {
        "code": "SECTOR_PSE",
        "name": "Nifty PSE Sector",
        "category": "SECTOR",
        "description": "Public Sector Enterprises",
    },
    {
        "code": "SECTOR_PSU_BANK",
        "name": "Nifty PSU Bank",
        "category": "SECTOR",
        "description": "Public Sector Banks",
    },
    {
        "code": "SECTOR_PRIVATE_BANK",
        "name": "Nifty Private Bank",
        "category": "SECTOR",
        "description": "Private Sector Banks",
    },
    {
        "code": "SECTOR_MNC",
        "name": "Nifty MNC",
        "category": "SECTOR",
        "description": "Multinational Corporations in India",
    },
]

# Baseline Sector Mappings for Major F&O Stocks
DEFAULT_SEGMENT_CONSTITUENTS: dict[str, list[str]] = {
    "INDEX_NIFTY50": [
        "RELIANCE",
        "HDFCBANK",
        "ICICIBANK",
        "INFY",
        "ITC",
        "TCS",
        "LT",
        "AXISBANK",
        "KOTAKBANK",
        "BHARTIARTL",
        "SBIN",
        "HINDUNILVR",
        "BAJFINANCE",
        "M&M",
        "MARUTI",
        "SUNPHARMA",
        "TATAMOTORS",
        "TITAN",
        "NTPC",
        "POWERGRID",
        "TATASTEEL",
        "ASIANPAINT",
        "COALINDIA",
        "ADANIENT",
        "BAJAJFINSV",
        "ULTRACEMCO",
        "JSWSTEEL",
        "HCLTECH",
        "ONGC",
        "WIPRO",
        "NESTLEIND",
        "BPCL",
        "GRASIM",
        "TECHM",
        "EICHERMOT",
        "BRITANNIA",
        "CIPLA",
        "APOLLOHOSP",
        "DRREDDY",
        "HEROMOTOCO",
        "SHRIRAMFIN",
        "HINDALCO",
        "DIVISLAB",
        "TATACONSUM",
        "SBILIFE",
        "BAJAJ-AUTO",
        "INDUSINDBK",
        "BEL",
        "TRENT",
        "ADANIPORTS",
    ],
    "INDEX_BANKNIFTY": [
        "HDFCBANK",
        "ICICIBANK",
        "AXISBANK",
        "KOTAKBANK",
        "SBIN",
        "INDUSINDBK",
        "BANKBARODA",
        "PNB",
        "AUBANK",
        "FEDERALBNK",
        "IDFCFIRSTB",
        "BANDHANBNK",
    ],
    "SECTOR_IT": [
        "TCS",
        "INFY",
        "HCLTECH",
        "WIPRO",
        "TECHM",
        "LTIM",
        "PERSISTENT",
        "COFORGE",
        "MPHASIS",
        "LTTS",
    ],
    "SECTOR_AUTO": [
        "TATAMOTORS",
        "M&M",
        "MARUTI",
        "BAJAJ-AUTO",
        "EICHERMOT",
        "HEROMOTOCO",
        "TVSMOTOR",
        "BHARATFORG",
        "ASHOKLEY",
        "MOTHERSON",
        "BALKRISIND",
        "MRF",
        "BOSCHLTD",
        "EXIDEIND",
        "APOLLOTYRE",
    ],
    "SECTOR_PHARMA": [
        "SUNPHARMA",
        "CIPLA",
        "DRREDDY",
        "DIVISLAB",
        "ZYDUSLIFE",
        "LUPIN",
        "TORNTPHARM",
        "AUROPHARMA",
        "ALKEM",
        "BIOCON",
        "GLENMARK",
        "IPCALAB",
        "ABBOTINDIA",
        "LAURUSLABS",
        "GRANULES",
    ],
    "SECTOR_ENERGY": [
        "RELIANCE",
        "ONGC",
        "NTPC",
        "POWERGRID",
        "BPCL",
        "IOC",
        "GAIL",
        "TATAPOWER",
        "ADANIGREEN",
        "ADANITRANS",
        "OIL",
        "PETRONET",
        "IGL",
        "MGL",
        "GUJGASLTD",
    ],
    "SECTOR_METAL": [
        "TATASTEEL",
        "JSWSTEEL",
        "HINDALCO",
        "JINDALSTEL",
        "VEDL",
        "NMDC",
        "NATIONALUM",
        "SAIL",
        "APLAPOLLO",
        "HINDZINC",
        "RATNAMANI",
    ],
    "SECTOR_FMCG": [
        "ITC",
        "HINDUNILVR",
        "NESTLEIND",
        "BRITANNIA",
        "TATACONSUM",
        "GODREJCP",
        "DABUR",
        "MARICO",
        "VARUN",
        "COLPAL",
        "EMAMILTD",
        "UBL",
        "RADICO",
    ],
    "SECTOR_REALTY": [
        "DLF",
        "GODREJPROP",
        "MACROTECH",
        "OBEROREALTY",
        "PHOENIXLTD",
        "PRESTIGE",
        "BRIGADE",
        "SOBHA",
    ],
    "SECTOR_PSU_BANK": [
        "SBIN",
        "BANKBARODA",
        "PNB",
        "CANBK",
        "UNIONBANK",
        "INDIANB",
        "MAHABANK",
        "CENTRALBK",
        "IOB",
        "UCOBANK",
        "PSB",
    ],
    "SECTOR_PRIVATE_BANK": [
        "HDFCBANK",
        "ICICIBANK",
        "AXISBANK",
        "KOTAKBANK",
        "INDUSINDBK",
        "FEDERALBNK",
        "IDFCFIRSTB",
        "BANDHANBNK",
        "RBLBANK",
        "CITYUNIONB",
    ],
}


def seed_nse_segments(engine: Engine) -> int:
    """Seed the 27 NSE segment definitions and baseline constituents into database."""
    inserted_segments = 0
    inserted_constituents = 0
    is_sqlite = engine.dialect.name == "sqlite"

    with engine.begin() as conn:
        for seg in NSE_SEGMENTS_CATALOG:
            if is_sqlite:
                # Check if exists
                existing = conn.execute(
                    select(mkt_segment_table).where(mkt_segment_table.c.code == seg["code"])
                ).first()
                if not existing:
                    conn.execute(
                        insert(mkt_segment_table).values(
                            code=seg["code"],
                            name=seg["name"],
                            category=seg["category"],
                            description=seg.get("description"),
                        )
                    )
            else:
                ins = pg_insert(mkt_segment_table).values(
                    code=seg["code"],
                    name=seg["name"],
                    category=seg["category"],
                    description=seg.get("description"),
                )
                upsert = ins.on_conflict_do_update(
                    index_elements=["code"],
                    set_={
                        "name": ins.excluded.name,
                        "category": ins.excluded.category,
                        "description": ins.excluded.description,
                    },
                )
                conn.execute(upsert)
            inserted_segments += 1

        for seg_code, symbols in DEFAULT_SEGMENT_CONSTITUENTS.items():
            for sym in symbols:
                if is_sqlite:
                    c_exists = conn.execute(
                        select(mkt_segment_constituent_table).where(
                            (mkt_segment_constituent_table.c.segment_code == seg_code)
                            & (mkt_segment_constituent_table.c.symbol == sym.upper())
                        )
                    ).first()
                    if not c_exists:
                        conn.execute(
                            insert(mkt_segment_constituent_table).values(
                                segment_code=seg_code,
                                symbol=sym.upper(),
                                weight=None,
                            )
                        )
                else:
                    c_ins = pg_insert(mkt_segment_constituent_table).values(
                        segment_code=seg_code,
                        symbol=sym.upper(),
                        weight=None,
                    )
                    c_upsert = c_ins.on_conflict_do_nothing(
                        index_elements=["segment_code", "symbol"],
                    )
                    conn.execute(c_upsert)
                inserted_constituents += 1

    logger.info("Seeded %d segments and %d constituents", inserted_segments, inserted_constituents)
    return inserted_segments


def get_all_segments(engine: Engine) -> list[SegmentSummary]:
    """Retrieve all 27 segments with active constituent counts."""
    summaries: list[SegmentSummary] = []
    with engine.connect() as conn:
        stmt = select(mkt_segment_table).order_by(
            mkt_segment_table.c.category, mkt_segment_table.c.name
        )
        rows = conn.execute(stmt).fetchall()
        for r in rows:
            c_stmt = select(mkt_segment_constituent_table.c.symbol).where(
                mkt_segment_constituent_table.c.segment_code == r.code
            )
            constituents = conn.execute(c_stmt).fetchall()
            summaries.append(
                SegmentSummary(
                    code=r.code,
                    name=r.name,
                    category=r.category,
                    description=r.description,
                    constituent_count=len(constituents),
                )
            )
    return summaries


def get_segment_constituents(engine: Engine, segment_code: str) -> list[str]:
    """Retrieve all constituent symbols in a given segment."""
    with engine.connect() as conn:
        stmt = (
            select(mkt_segment_constituent_table.c.symbol)
            .where(mkt_segment_constituent_table.c.segment_code == segment_code.upper())
            .order_by(mkt_segment_constituent_table.c.symbol.asc())
        )
        return [row[0] for row in conn.execute(stmt).fetchall()]
