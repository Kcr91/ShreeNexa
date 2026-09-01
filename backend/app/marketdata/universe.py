"""Index constituent ingestion, effective-interval tracking, and point-in-time membership."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    DATE,
    NUMERIC,
    Column,
    MetaData,
    Table,
    Text,
    and_,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FALLBACK_PATH = REPO_ROOT / "config" / "index_constituents_fallback.yaml"

metadata = MetaData()

index_constituent_table = Table(
    "index_constituent",
    metadata,
    Column("index_name", Text, primary_key=True),
    Column("symbol", Text, primary_key=True),
    Column("weight", NUMERIC(8, 4), nullable=True),
    Column("sector", Text, nullable=True),
    Column("valid_from", DATE, primary_key=True),
    Column("valid_to", DATE, nullable=True),
    Column("source_date", DATE, nullable=False),
    Column("source", Text, nullable=False),
)


class ConstituentInput(BaseModel):
    """Input specification for an index constituent."""

    symbol: str
    weight: Decimal | float | None = None
    sector: str | None = None


class IndexConstituentRecord(BaseModel):
    """Pydantic representation of an effective index constituent record."""

    model_config = ConfigDict(from_attributes=True)

    index_name: str
    symbol: str
    weight: Decimal | float | None = None
    sector: str | None = None
    valid_from: date
    valid_to: date | None = None
    source_date: date
    source: str


class IndexMembershipResult(BaseModel):
    """Result of point-in-time index membership verification."""

    index_name: str
    symbol: str
    is_member: bool
    as_of: date
    weight: Decimal | float | None = None
    sector: str | None = None
    source: str | None = None
    source_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class ManualOverrideRequest(BaseModel):
    """Request payload for manual constituent additions or removals."""

    index_name: str
    symbol: str
    is_member: bool = True
    effective_date: date = Field(default_factory=lambda: datetime.now(UTC).date())
    weight: Decimal | float | None = None
    sector: str | None = None


def _normalize_date(val: date | str | None) -> date:
    if val is None:
        return datetime.now(UTC).date()
    if isinstance(val, date):
        return val
    return datetime.strptime(str(val).split()[0], "%Y-%m-%d").date()


def ingest_index_snapshot(
    engine: Engine,
    index_name: str,
    constituents: list[ConstituentInput],
    source_date: date | str,
    valid_from: date | str,
    source: str = "official_snapshot",
) -> int:
    """Ingest index constituent snapshot with effective interval tracking [valid_from, valid_to].

    If constituents have been removed since previous active intervals, their `valid_to`
    is updated to `valid_from - 1 day`. New constituents are inserted with `[valid_from, NULL]`.
    """
    s_date = _normalize_date(source_date)
    v_from = _normalize_date(valid_from)
    prev_day = v_from - timedelta(days=1)

    new_symbols = {c.symbol.upper(): c for c in constituents}
    upserted_count = 0

    with engine.begin() as conn:
        # Fetch currently active constituents for this index
        stmt = select(index_constituent_table).where(
            and_(
                index_constituent_table.c.index_name == index_name,
                or_(
                    index_constituent_table.c.valid_to.is_(None),
                    index_constituent_table.c.valid_to >= v_from,
                ),
            )
        )
        active_rows = conn.execute(stmt).fetchall()
        active_by_symbol = {row.symbol: row for row in active_rows}

        # 1. Close intervals for dropped constituents
        for sym, row in active_by_symbol.items():
            if sym not in new_symbols:
                # Set valid_to to prev_day if valid_from <= prev_day, otherwise remove if same day
                if row.valid_from <= prev_day:
                    conn.execute(
                        update(index_constituent_table)
                        .where(
                            and_(
                                index_constituent_table.c.index_name == index_name,
                                index_constituent_table.c.symbol == sym,
                                index_constituent_table.c.valid_from == row.valid_from,
                            )
                        )
                        .values(valid_to=prev_day)
                    )
                upserted_count += 1

        # 2. Insert or update current constituents
        for sym, item in new_symbols.items():
            w_val = Decimal(str(item.weight)) if item.weight is not None else None
            existing = active_by_symbol.get(sym)

            if existing is not None and existing.valid_from == v_from:
                # Same valid_from date: update in place
                conn.execute(
                    update(index_constituent_table)
                    .where(
                        and_(
                            index_constituent_table.c.index_name == index_name,
                            index_constituent_table.c.symbol == sym,
                            index_constituent_table.c.valid_from == v_from,
                        )
                    )
                    .values(
                        weight=w_val,
                        sector=item.sector,
                        valid_to=None,
                        source_date=s_date,
                        source=source,
                    )
                )
                upserted_count += 1
            else:
                if existing is not None and existing.valid_from < v_from:
                    # Close previous interval
                    conn.execute(
                        update(index_constituent_table)
                        .where(
                            and_(
                                index_constituent_table.c.index_name == index_name,
                                index_constituent_table.c.symbol == sym,
                                index_constituent_table.c.valid_from == existing.valid_from,
                            )
                        )
                        .values(valid_to=prev_day)
                    )

                # Insert new interval starting from v_from
                ins_stmt = pg_insert(index_constituent_table).values(
                    index_name=index_name,
                    symbol=sym,
                    weight=w_val,
                    sector=item.sector,
                    valid_from=v_from,
                    valid_to=None,
                    source_date=s_date,
                    source=source,
                )
                upsert_stmt = ins_stmt.on_conflict_do_update(
                    index_elements=["index_name", "symbol", "valid_from"],
                    set_={
                        "weight": ins_stmt.excluded.weight,
                        "sector": ins_stmt.excluded.sector,
                        "valid_to": None,
                        "source_date": ins_stmt.excluded.source_date,
                        "source": ins_stmt.excluded.source,
                    },
                )
                conn.execute(upsert_stmt)
                upserted_count += 1

    return upserted_count


def load_fallback_config(config_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load committed index constituent fallback configurations."""
    target_path = Path(config_path) if config_path else DEFAULT_FALLBACK_PATH
    if not target_path.is_file():
        logger.warning("Fallback constituent config file not found: %s", target_path)
        return []

    try:
        content = target_path.read_text(encoding="utf-8")
        parsed: Any = yaml.safe_load(content)
        if isinstance(parsed, dict) and "indices" in parsed and isinstance(parsed["indices"], list):
            return list(parsed["indices"])
        return []
    except Exception as exc:
        logger.error("Failed loading fallback constituent config: %s", exc)
        return []


def ingest_fallback_constituents(engine: Engine, config_path: Path | str | None = None) -> int:
    """Ingest all committed index fallback snapshots into PostgreSQL."""
    indices = load_fallback_config(config_path)
    total_ingested = 0

    for idx in indices:
        index_name = idx.get("index_name")
        source_date = idx.get("source_date", "2026-08-01")
        valid_from = idx.get("valid_from", "2026-08-01")
        raw_constituents = idx.get("constituents", [])

        if not index_name or not isinstance(raw_constituents, list):
            continue

        constituents = [
            ConstituentInput(
                symbol=item.get("symbol", ""),
                weight=item.get("weight"),
                sector=item.get("sector"),
            )
            for item in raw_constituents
            if item.get("symbol")
        ]

        count = ingest_index_snapshot(
            engine,
            index_name=index_name,
            constituents=constituents,
            source_date=source_date,
            valid_from=valid_from,
            source="fallback",
        )
        total_ingested += count

    return total_ingested


def apply_manual_override(
    engine: Engine,
    index_name: str,
    symbol: str,
    is_member: bool,
    effective_date: date | str,
    weight: Decimal | float | None = None,
    sector: str | None = None,
) -> None:
    """Apply manual constituent addition or deletion with source='manual'."""
    eff_date = _normalize_date(effective_date)
    sym = symbol.strip().upper()
    prev_day = eff_date - timedelta(days=1)
    w_val = Decimal(str(weight)) if weight is not None else None

    with engine.begin() as conn:
        stmt = select(index_constituent_table).where(
            and_(
                index_constituent_table.c.index_name == index_name,
                index_constituent_table.c.symbol == sym,
                or_(
                    index_constituent_table.c.valid_to.is_(None),
                    index_constituent_table.c.valid_to >= eff_date,
                ),
            )
        )
        existing = conn.execute(stmt).first()

        if is_member:
            if existing is not None and existing.valid_from < eff_date:
                conn.execute(
                    update(index_constituent_table)
                    .where(
                        and_(
                            index_constituent_table.c.index_name == index_name,
                            index_constituent_table.c.symbol == sym,
                            index_constituent_table.c.valid_from == existing.valid_from,
                        )
                    )
                    .values(valid_to=prev_day)
                )

            ins_stmt = pg_insert(index_constituent_table).values(
                index_name=index_name,
                symbol=sym,
                weight=w_val,
                sector=sector or (existing.sector if existing else None),
                valid_from=eff_date,
                valid_to=None,
                source_date=eff_date,
                source="manual",
            )
            upsert_stmt = ins_stmt.on_conflict_do_update(
                index_elements=["index_name", "symbol", "valid_from"],
                set_={
                    "weight": ins_stmt.excluded.weight,
                    "sector": ins_stmt.excluded.sector,
                    "valid_to": None,
                    "source_date": ins_stmt.excluded.source_date,
                    "source": "manual",
                },
            )
            conn.execute(upsert_stmt)
        else:
            if existing is not None and existing.valid_from <= prev_day:
                conn.execute(
                    update(index_constituent_table)
                    .where(
                        and_(
                            index_constituent_table.c.index_name == index_name,
                            index_constituent_table.c.symbol == sym,
                            index_constituent_table.c.valid_from == existing.valid_from,
                        )
                    )
                    .values(valid_to=prev_day)
                )


def get_constituents_at_date(
    engine: Engine,
    index_name: str,
    as_of: date | str | None = None,
) -> list[IndexConstituentRecord]:
    """Retrieve all effective constituents of an index as of a specific historical date."""
    target_date = _normalize_date(as_of)
    stmt = (
        select(index_constituent_table)
        .where(
            and_(
                index_constituent_table.c.index_name == index_name,
                index_constituent_table.c.valid_from <= target_date,
                or_(
                    index_constituent_table.c.valid_to.is_(None),
                    index_constituent_table.c.valid_to >= target_date,
                ),
            )
        )
        .order_by(
            index_constituent_table.c.weight.desc().nulls_last(),
            index_constituent_table.c.symbol.asc(),
        )
    )

    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [IndexConstituentRecord.model_validate(dict(row._mapping)) for row in result]


def is_member_at_date(
    engine: Engine,
    index_name: str,
    symbol: str,
    as_of: date | str | None = None,
) -> IndexMembershipResult:
    """Verify point-in-time index membership for a symbol on date `as_of`."""
    target_date = _normalize_date(as_of)
    sym = symbol.strip().upper()

    stmt = select(index_constituent_table).where(
        and_(
            index_constituent_table.c.index_name == index_name,
            index_constituent_table.c.symbol == sym,
            index_constituent_table.c.valid_from <= target_date,
            or_(
                index_constituent_table.c.valid_to.is_(None),
                index_constituent_table.c.valid_to >= target_date,
            ),
        )
    )

    with engine.connect() as conn:
        row = conn.execute(stmt).first()
        if row is None:
            return IndexMembershipResult(
                index_name=index_name,
                symbol=sym,
                is_member=False,
                as_of=target_date,
            )

        return IndexMembershipResult(
            index_name=index_name,
            symbol=sym,
            is_member=True,
            as_of=target_date,
            weight=row.weight,
            sector=row.sector,
            source=row.source,
            source_date=row.source_date,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
        )


def list_available_indices(engine: Engine) -> list[str]:
    """Return distinct index names present in the database."""
    stmt = (
        select(index_constituent_table.c.index_name)
        .distinct()
        .order_by(index_constituent_table.c.index_name.asc())
    )
    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [row[0] for row in result]
