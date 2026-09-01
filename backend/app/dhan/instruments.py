"""Dhan detailed instrument master parser, PostgreSQL ingestion, and typed search."""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BOOLEAN,
    DATE,
    INTEGER,
    NUMERIC,
    TIMESTAMP,
    Column,
    MetaData,
    Table,
    Text,
    and_,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

metadata = MetaData()

instrument_table = Table(
    "instrument",
    metadata,
    Column("security_id", Text, primary_key=True),
    Column("exchange_segment", Text, primary_key=True),
    Column("instrument_type", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("trading_symbol", Text, nullable=False),
    Column("isin", Text, nullable=True),
    Column("lot_size", INTEGER, nullable=True),
    Column("tick_size", NUMERIC(12, 4), nullable=True),
    Column("expiry_date", DATE, nullable=True),
    Column("strike_price", NUMERIC(14, 4), nullable=True),
    Column("option_type", Text, nullable=True),
    Column("underlying_id", Text, nullable=True),
    Column("is_active", BOOLEAN, nullable=False, default=True),
    Column("raw", JSONB, nullable=True),
    Column("synced_at", TIMESTAMP(timezone=True), nullable=False),
)


class InstrumentRecord(BaseModel):
    """Pydantic model representing a single financial instrument record."""

    model_config = ConfigDict(from_attributes=True)

    security_id: str
    exchange_segment: str
    instrument_type: str
    symbol: str
    trading_symbol: str
    isin: str | None = None
    lot_size: int | None = None
    tick_size: Decimal | float | None = None
    expiry_date: date | None = None
    strike_price: Decimal | float | None = None
    option_type: str | None = None
    underlying_id: str | None = None
    is_active: bool = True
    raw: dict[str, Any] | None = None
    synced_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InstrumentSearchQuery(BaseModel):
    """Query parameters for searching instruments."""

    query: str | None = Field(
        default=None,
        description="Search substring or prefix against symbol, trading_symbol, or security_id",
    )
    exchange_segment: str | None = Field(default=None, description="Filter by exchange segment")
    instrument_type: str | None = Field(default=None, description="Filter by instrument type")
    underlying_id: str | None = Field(default=None, description="Filter by underlying security ID")
    expiry_date: date | str | None = Field(default=None, description="Filter by expiry date")
    strike_price: float | Decimal | None = Field(default=None, description="Filter by strike price")
    option_type: str | None = Field(default=None, description="Filter by option type (CE or PE)")
    is_active_only: bool = Field(default=True, description="Filter active instruments only")
    limit: int = Field(default=50, ge=1, le=500, description="Max results")
    offset: int = Field(default=0, ge=0, description="Result offset")


class IngestSummary(BaseModel):
    """Result summary of an instrument master ingestion operation."""

    total_rows: int = 0
    inserted_or_updated: int = 0
    skipped: int = 0
    distinct_segments: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def resolve_exchange_segment(exch_id: str | None, segment: str | None) -> str:
    """Resolve and normalize exchange segment without hardcoding assumptions.

    Supports both numeric and textual codes for all Indian exchanges:
    - IDX_I / 0: Index
    - NSE_EQ / 1: NSE Equity Cash
    - NSE_FNO / 2: NSE Futures & Options
    - NSE_CURRENCY / 3: NSE Currency
    - BSE_EQ / 4: BSE Equity Cash
    - MCX_COMM / 5: MCX Commodity
    - BSE_CURRENCY / 7: BSE Currency
    - BSE_FNO / 8: BSE Futures & Options
    """
    raw_exch = (exch_id or "").strip().upper()
    raw_seg = (segment or "").strip().upper()

    # Direct combined match
    combined = f"{raw_exch}_{raw_seg}" if raw_seg else raw_exch
    known_segments = {
        "NSE_EQ": "NSE_EQ",
        "NSE_E": "NSE_EQ",
        "1": "NSE_EQ",
        "NSE_FNO": "NSE_FNO",
        "NSE_D": "NSE_FNO",
        "NSE_F": "NSE_FNO",
        "2": "NSE_FNO",
        "IDX_I": "IDX_I",
        "NSE_I": "IDX_I",
        "BSE_I": "IDX_I",
        "0": "IDX_I",
        "NSE_CURRENCY": "NSE_CURRENCY",
        "NSE_C": "NSE_CURRENCY",
        "3": "NSE_CURRENCY",
        "BSE_EQ": "BSE_EQ",
        "BSE_E": "BSE_EQ",
        "4": "BSE_EQ",
        "MCX_COMM": "MCX_COMM",
        "MCX_M": "MCX_COMM",
        "MCX_C": "MCX_COMM",
        "5": "MCX_COMM",
        "BSE_CURRENCY": "BSE_CURRENCY",
        "BSE_C": "BSE_CURRENCY",
        "7": "BSE_CURRENCY",
        "BSE_FNO": "BSE_FNO",
        "BSE_D": "BSE_FNO",
        "BSE_F": "BSE_FNO",
        "8": "BSE_FNO",
    }

    if combined in known_segments:
        return known_segments[combined]
    if raw_exch in known_segments:
        return known_segments[raw_exch]

    # Dynamic fallback to ensure unannounced segments do not crash
    if raw_exch and raw_seg:
        return f"{raw_exch}_{raw_seg}"
    return raw_exch or "UNKNOWN"


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return None if s in ("", "NA", "null", "NULL", "None", "-") else s


def _parse_date(val: Any) -> date | None:
    s = _clean_str(val)
    if not s:
        return None
    # Strip timestamp component if present e.g. "2026-08-28 15:30:00"
    date_part = s.split()[0]
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(val: Any) -> Decimal | None:
    s = _clean_str(val)
    if not s:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def _parse_int(val: Any) -> int | None:
    s = _clean_str(val)
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _parse_bool(val: Any, default: bool = True) -> bool:
    s = _clean_str(val)
    if s is None:
        return default
    return s.upper() in ("Y", "YES", "TRUE", "1", "T", "ACTIVE")


# Aliases for CSV column mapping to handle schema drift
COLUMN_ALIASES: dict[str, list[str]] = {
    "security_id": ["SEM_SMST_SECURITY_ID", "SECURITY_ID", "security_id", "SEM_SECURITY_ID"],
    "exch_id": ["SEM_EXM_EXCH_ID", "EXCH_ID", "EXCHANGE", "exchange_segment", "EXCHANGE_SEGMENT"],
    "segment": ["SEM_SEGMENT", "SEGMENT", "segment"],
    "instrument_type": [
        "SEM_INSTRUMENT_NAME",
        "INSTRUMENT_TYPE",
        "instrument_type",
        "INSTRUMENT_NAME",
    ],
    "symbol": ["SEM_CUSTOM_SYMBOL", "SYMBOL", "symbol", "SEM_SYMBOL"],
    "trading_symbol": ["SEM_TRADING_SYMBOL", "TRADING_SYMBOL", "trading_symbol"],
    "isin": ["SEM_ISIN", "ISIN", "isin"],
    "lot_size": ["SEM_LOT_UNITS", "LOT_SIZE", "lot_size", "SEM_LOT_SIZE"],
    "tick_size": ["SEM_TICK_SIZE", "TICK_SIZE", "tick_size"],
    "expiry_date": ["SEM_EXPIRY_DATE", "EXPIRY_DATE", "expiry_date"],
    "strike_price": ["SEM_STRIKE_PRICE", "STRIKE_PRICE", "strike_price"],
    "option_type": ["SEM_OPTION_TYPE", "OPTION_TYPE", "option_type"],
    "underlying_id": [
        "SEM_UNDERLYING_SECURITY_ID",
        "UNDERLYING_SECURITY_ID",
        "underlying_id",
        "UNDERLYING_ID",
    ],
    "is_active": ["SEM_IS_ACTIVE", "IS_ACTIVE", "is_active", "ACTIVE"],
}


def _resolve_header_map(fieldnames: Sequence[str]) -> dict[str, str]:
    """Map canonical field name to matching CSV header name."""
    header_map: dict[str, str] = {}
    normalized_headers = {h.strip(): h for h in fieldnames if h}

    for canonical_field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_headers:
                header_map[canonical_field] = normalized_headers[alias]
                break
    return header_map


def parse_scrip_master_csv(
    csv_source: str | bytes | Path | io.StringIO | io.BytesIO,
    synced_at: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse Dhan scrip master CSV with alias mapping, type conversion, and drift tolerance."""
    active_synced_at = synced_at or datetime.now(UTC)

    if isinstance(csv_source, Path):
        text_content = csv_source.read_text(encoding="utf-8")
        reader_io: io.StringIO = io.StringIO(text_content)
    elif isinstance(csv_source, bytes):
        reader_io = io.StringIO(csv_source.decode("utf-8", errors="replace"))
    elif isinstance(csv_source, str):
        reader_io = io.StringIO(csv_source)
    else:
        reader_io = csv_source  # type: ignore[assignment]

    csv_reader = csv.DictReader(reader_io)
    if not csv_reader.fieldnames:
        return [], ["Empty or invalid CSV source"]

    header_map = _resolve_header_map(csv_reader.fieldnames)
    records: list[dict[str, Any]] = []
    errors: list[str] = []

    for row_num, row in enumerate(csv_reader, start=1):
        try:
            sec_id_col = header_map.get("security_id")
            raw_sec_id = row.get(sec_id_col) if sec_id_col else None
            security_id = _clean_str(raw_sec_id)
            if not security_id:
                errors.append(f"Row {row_num}: missing security_id")
                continue

            exch_col = header_map.get("exch_id")
            seg_col = header_map.get("segment")
            raw_exch = row.get(exch_col) if exch_col else None
            raw_seg = row.get(seg_col) if seg_col else None
            exchange_segment = resolve_exchange_segment(raw_exch, raw_seg)

            inst_col = header_map.get("instrument_type")
            instrument_type = _clean_str(row.get(inst_col)) if inst_col else None
            instrument_type = instrument_type or "EQUITY"

            sym_col = header_map.get("symbol")
            symbol = _clean_str(row.get(sym_col)) if sym_col else None

            tsym_col = header_map.get("trading_symbol")
            trading_symbol = _clean_str(row.get(tsym_col)) if tsym_col else None

            symbol = symbol or trading_symbol or security_id
            trading_symbol = trading_symbol or symbol

            isin_col = header_map.get("isin")
            isin = _clean_str(row.get(isin_col)) if isin_col else None

            lot_col = header_map.get("lot_size")
            lot_size = _parse_int(row.get(lot_col)) if lot_col else 1

            tick_col = header_map.get("tick_size")
            tick_size = _parse_decimal(row.get(tick_col)) if tick_col else Decimal("0.05")

            exp_col = header_map.get("expiry_date")
            expiry_date = _parse_date(row.get(exp_col)) if exp_col else None

            strk_col = header_map.get("strike_price")
            strike_price = _parse_decimal(row.get(strk_col)) if strk_col else None
            is_option_type = instrument_type in ("OPTIDX", "OPTSTK", "OPTCUR", "OPTCOM")
            if strike_price is not None and (strike_price <= Decimal(0) or not is_option_type):
                if strike_price == Decimal(0):
                    strike_price = None

            opt_col = header_map.get("option_type")
            option_type = _clean_str(row.get(opt_col)) if opt_col else None
            if option_type and option_type.upper() in ("XX", "NA", "0"):
                option_type = None

            und_col = header_map.get("underlying_id")
            underlying_id = _clean_str(row.get(und_col)) if und_col else None

            act_col = header_map.get("is_active")
            is_active = _parse_bool(row.get(act_col), default=True) if act_col else True

            record: dict[str, Any] = {
                "security_id": security_id,
                "exchange_segment": exchange_segment,
                "instrument_type": instrument_type,
                "symbol": symbol,
                "trading_symbol": trading_symbol,
                "isin": isin,
                "lot_size": lot_size,
                "tick_size": tick_size,
                "expiry_date": expiry_date,
                "strike_price": strike_price,
                "option_type": option_type,
                "underlying_id": underlying_id,
                "is_active": is_active,
                "raw": dict(row),
                "synced_at": active_synced_at,
            }
            records.append(record)
        except Exception as exc:
            errors.append(f"Row {row_num} failed to parse: {exc}")

    return records, errors


def ingest_instruments(
    engine: Engine,
    csv_source: str | bytes | Path | io.StringIO | io.BytesIO,
    batch_size: int = 1000,
    synced_at: datetime | None = None,
) -> IngestSummary:
    """Ingest Dhan detailed scrip master CSV into PostgreSQL with ON CONFLICT DO UPDATE."""
    active_synced_at = synced_at or datetime.now(UTC)
    records, errors = parse_scrip_master_csv(csv_source, synced_at=active_synced_at)

    if not records:
        return IngestSummary(
            total_rows=0,
            inserted_or_updated=0,
            skipped=len(errors),
            distinct_segments=[],
            errors=errors,
        )

    # Deduplicate within batch keeping latest entry per (exchange_segment, security_id)
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        deduped[(r["exchange_segment"], r["security_id"])] = r

    unique_records = list(deduped.values())
    distinct_segments = sorted({r["exchange_segment"] for r in unique_records})

    total_upserted = 0
    with engine.begin() as conn:
        for i in range(0, len(unique_records), batch_size):
            batch = unique_records[i : i + batch_size]
            stmt = pg_insert(instrument_table).values(batch)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["exchange_segment", "security_id"],
                set_={
                    "instrument_type": stmt.excluded.instrument_type,
                    "symbol": stmt.excluded.symbol,
                    "trading_symbol": stmt.excluded.trading_symbol,
                    "isin": stmt.excluded.isin,
                    "lot_size": stmt.excluded.lot_size,
                    "tick_size": stmt.excluded.tick_size,
                    "expiry_date": stmt.excluded.expiry_date,
                    "strike_price": stmt.excluded.strike_price,
                    "option_type": stmt.excluded.option_type,
                    "underlying_id": stmt.excluded.underlying_id,
                    "is_active": stmt.excluded.is_active,
                    "raw": stmt.excluded.raw,
                    "synced_at": stmt.excluded.synced_at,
                },
            )
            conn.execute(upsert_stmt)
            total_upserted += len(batch)

    return IngestSummary(
        total_rows=len(records),
        inserted_or_updated=total_upserted,
        skipped=len(errors) + (len(records) - len(unique_records)),
        distinct_segments=distinct_segments,
        errors=errors,
    )


def search_instruments(engine: Engine, query: InstrumentSearchQuery) -> list[InstrumentRecord]:
    """Execute typed search query against the instrument table."""
    stmt = select(instrument_table)
    conditions: list[Any] = []

    if query.is_active_only:
        conditions.append(instrument_table.c.is_active.is_(True))

    if query.exchange_segment:
        conditions.append(instrument_table.c.exchange_segment == query.exchange_segment)

    if query.instrument_type:
        conditions.append(instrument_table.c.instrument_type == query.instrument_type)

    if query.underlying_id:
        conditions.append(instrument_table.c.underlying_id == str(query.underlying_id))

    if query.expiry_date:
        exp = (
            query.expiry_date
            if isinstance(query.expiry_date, date)
            else _parse_date(query.expiry_date)
        )
        if exp:
            conditions.append(instrument_table.c.expiry_date == exp)

    if query.strike_price is not None:
        conditions.append(instrument_table.c.strike_price == Decimal(str(query.strike_price)))

    if query.option_type:
        conditions.append(instrument_table.c.option_type == query.option_type.upper())

    if query.query:
        q_str = query.query.strip()
        pattern = f"%{q_str}%"
        conditions.append(
            or_(
                instrument_table.c.symbol.ilike(pattern),
                instrument_table.c.trading_symbol.ilike(pattern),
                instrument_table.c.security_id == q_str,
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = (
        stmt.order_by(
            instrument_table.c.symbol.asc(),
            instrument_table.c.strike_price.asc().nulls_last(),
            instrument_table.c.option_type.asc().nulls_last(),
        )
        .limit(query.limit)
        .offset(query.offset)
    )

    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [InstrumentRecord.model_validate(dict(row._mapping)) for row in result]


def get_instrument(
    engine: Engine, exchange_segment: str, security_id: str
) -> InstrumentRecord | None:
    """Look up an exact instrument by (exchange_segment, security_id)."""
    stmt = select(instrument_table).where(
        and_(
            instrument_table.c.exchange_segment == exchange_segment,
            instrument_table.c.security_id == security_id,
        )
    )
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
        if row is None:
            return None
        return InstrumentRecord.model_validate(dict(row._mapping))


def get_option_chain_instruments(
    engine: Engine,
    underlying_id: str,
    expiry_date: date | str,
    exchange_segment: str = "NSE_FNO",
) -> list[InstrumentRecord]:
    """Retrieve all options for an underlying ID and expiry date ordered by strike."""
    exp = expiry_date if isinstance(expiry_date, date) else _parse_date(expiry_date)
    if not exp:
        return []

    stmt = (
        select(instrument_table)
        .where(
            and_(
                instrument_table.c.underlying_id == str(underlying_id),
                instrument_table.c.expiry_date == exp,
                instrument_table.c.exchange_segment == exchange_segment,
                instrument_table.c.option_type.isnot(None),
                instrument_table.c.is_active.is_(True),
            )
        )
        .order_by(
            instrument_table.c.strike_price.asc(),
            instrument_table.c.option_type.asc(),
        )
    )
    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [InstrumentRecord.model_validate(dict(row._mapping)) for row in result]


def get_distinct_segments(engine: Engine) -> list[str]:
    """Return all distinct exchange segments present in the instrument table."""
    stmt = (
        select(instrument_table.c.exchange_segment)
        .distinct()
        .order_by(instrument_table.c.exchange_segment.asc())
    )
    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [row[0] for row in result]


def get_expiries_for_underlying(
    engine: Engine,
    underlying_id: str,
    exchange_segment: str = "NSE_FNO",
) -> list[date]:
    """Return distinct active expiry dates for an underlying security."""
    stmt = (
        select(instrument_table.c.expiry_date)
        .where(
            and_(
                instrument_table.c.underlying_id == str(underlying_id),
                instrument_table.c.exchange_segment == exchange_segment,
                instrument_table.c.expiry_date.isnot(None),
                instrument_table.c.is_active.is_(True),
            )
        )
        .distinct()
        .order_by(instrument_table.c.expiry_date.asc())
    )
    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [row[0] for row in result if row[0] is not None]
