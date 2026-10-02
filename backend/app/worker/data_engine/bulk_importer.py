"""High-speed CSV bulk importer parsing local directory hierarchy into PostgreSQL and Parquet."""

from __future__ import annotations

import csv
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
from app.worker.data_engine.models import (
    mkt_download_state_table,
    mkt_ohlcv_equity_table,
    mkt_ohlcv_futures_table,
    mkt_ohlcv_options_table,
)
from app.worker.data_engine.parquet_archiver import (
    EQUITY_SCHEMA,
    FUTURES_SCHEMA,
    OPTIONS_SCHEMA,
    ParquetArchiver,
)
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class ParsedPathMetadata(BaseModel):
    """Metadata derived from directory and file structure."""

    symbol: str
    instrument_type: str  # EQ, FUT, CE, PE
    expiry_period: str | None = None  # e.g., Month_1, Week_2
    strike_offset: int = 0
    option_type: str | None = None  # CE or PE
    file_path: Path


def parse_csv_path(file_path: Path | str) -> ParsedPathMetadata | None:
    """Derive symbol, instrument type, expiry, and strike offset from CSV path structure."""
    p = Path(file_path)
    parts = p.parts
    filename = p.name

    if not filename.lower().endswith(".csv"):
        return None

    # Case 1: Root equity spot file (e.g. RELIANCE.csv, NIFTY.csv)
    if (
        len(parts) >= 1
        and filename.upper().endswith(".CSV")
        and not any(k in filename.upper() for k in ["CALL", "PUT", "FUT", "ATM"])
    ):
        symbol = filename.replace(".csv", "").replace(".CSV", "").upper()
        return ParsedPathMetadata(
            symbol=symbol,
            instrument_type="EQ",
            file_path=p,
        )

    # Case 2: Nested options directory structure
    # (e.g. RELIANCE/Month_1/ATM_Call.csv, NIFTY/Week_1/ATM+2_Call.csv)
    # Search backwards for symbol and expiry folder
    # Example parts: [..., "RELIANCE", "Month_1", "ATM+1_Call.csv"]
    for i in range(len(parts) - 1, 0, -1):
        parent = parts[i - 1]
        grandparent = parts[i - 2] if i >= 2 else None

        if "MONTH_" in parent.upper() or "WEEK_" in parent.upper():
            symbol = (grandparent or "UNKNOWN").upper()
            expiry_period = parent

            # Parse option right (Call -> CE, Put -> PE)
            fn_upper = filename.upper()
            opt_type = "CE" if "CALL" in fn_upper else ("PE" if "PUT" in fn_upper else None)
            inst_type = opt_type or "OPT"

            # Parse offset
            offset = 0
            offset_match = re.search(r"ATM([+-]\d+)", fn_upper)
            if offset_match:
                offset = int(offset_match.group(1))

            return ParsedPathMetadata(
                symbol=symbol,
                instrument_type=inst_type,
                expiry_period=expiry_period,
                strike_offset=offset,
                option_type=opt_type,
                file_path=p,
            )

    # Case 3: Direct futures or options naming (e.g. NIFTY_FUT.csv, RELIANCE_2500_CE.csv)
    fn_no_ext = filename[:-4].upper()
    if "_FUT" in fn_no_ext:
        sym = fn_no_ext.split("_FUT")[0]
        return ParsedPathMetadata(symbol=sym, instrument_type="FUT", file_path=p)

    if "_CE" in fn_no_ext or "_PE" in fn_no_ext:
        opt_type = "CE" if "_CE" in fn_no_ext else "PE"
        sym = fn_no_ext.split("_")[0]
        return ParsedPathMetadata(
            symbol=sym, instrument_type=opt_type, option_type=opt_type, file_path=p
        )

    # Fallback to EQ
    return ParsedPathMetadata(
        symbol=fn_no_ext,
        instrument_type="EQ",
        file_path=p,
    )


def _parse_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw CSV row values."""
    dt_str = row.get("datetime_ist") or row.get("timestamp") or row.get("date")
    if isinstance(dt_str, (int, float)):
        # Epoch ms
        dt = datetime.fromtimestamp(dt_str / 1000.0, tz=UTC)
    else:
        dt_str_clean = str(dt_str).replace("+05:30", "").strip()
        try:
            dt = datetime.fromisoformat(dt_str_clean).replace(tzinfo=UTC)
        except Exception:
            dt = datetime.strptime(dt_str_clean.split(".")[0], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=UTC
            )

    open_val = float(row.get("open", 0.0))
    high_val = float(row.get("high", 0.0))
    low_val = float(row.get("low", 0.0))
    close_val = float(row.get("close", 0.0))
    volume_val = int(float(row.get("volume", 0) or 0))
    oi_val = int(float(row.get("open_interest", row.get("oi", 0)) or 0))
    iv_val = float(row.get("iv", 0.0)) if row.get("iv") not in [None, ""] else None
    spot_val = (
        float(row.get("spot", row.get("underlying_spot", 0.0)))
        if row.get("spot") or row.get("underlying_spot")
        else None
    )

    return {
        "datetime_ist": dt,
        "open": open_val,
        "high": high_val,
        "low": low_val,
        "close": close_val,
        "volume": volume_val,
        "oi": oi_val,
        "iv": iv_val,
        "underlying_spot": spot_val,
    }


class BulkImporter:
    """Scans and bulk-imports 5-year OHLCV CSV data into PostgreSQL and Parquet."""

    def __init__(
        self,
        engine: Engine,
        archiver: ParquetArchiver | None = None,
        batch_size: int = 5000,
    ) -> None:
        self.engine = engine
        self.archiver = archiver or ParquetArchiver()
        self.batch_size = batch_size

    def import_csv_file(
        self,
        file_path: Path | str,
        security_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Import a single CSV file into Postgres and append to Parquet warehouse."""
        p = Path(file_path)
        meta = parse_csv_path(p)
        if not meta:
            logger.warning("Could not parse metadata from path: %s", p)
            return 0

        sec_id = security_id or f"{meta.symbol}_{meta.instrument_type}_{meta.strike_offset}"
        rows: list[dict[str, Any]] = []

        with open(p, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                parsed = _parse_row(raw_row)
                parsed["security_id"] = sec_id
                parsed["symbol"] = meta.symbol
                parsed["exchange_segment"] = "NSE_EQ" if meta.instrument_type == "EQ" else "NSE_FNO"
                rows.append(parsed)

        if not rows:
            return 0

        if dry_run:
            logger.info("Dry run: parsed %d rows from %s", len(rows), p)
            return len(rows)

        # 1. Batch upsert into PostgreSQL
        table = (
            mkt_ohlcv_equity_table
            if meta.instrument_type == "EQ"
            else (
                mkt_ohlcv_futures_table
                if meta.instrument_type == "FUT"
                else mkt_ohlcv_options_table
            )
        )

        total_upserted = 0
        with self.engine.begin() as conn:
            for i in range(0, len(rows), self.batch_size):
                chunk = rows[i : i + self.batch_size]
                if meta.instrument_type == "EQ":
                    db_chunk = [
                        {
                            "security_id": r["security_id"],
                            "exchange_segment": r["exchange_segment"],
                            "symbol": r["symbol"],
                            "datetime_ist": r["datetime_ist"],
                            "open": r["open"],
                            "high": r["high"],
                            "low": r["low"],
                            "close": r["close"],
                            "volume": r["volume"],
                        }
                        for r in chunk
                    ]
                elif meta.instrument_type == "FUT":
                    db_chunk = [
                        {
                            "security_id": r["security_id"],
                            "exchange_segment": r["exchange_segment"],
                            "symbol": r["symbol"],
                            "datetime_ist": r["datetime_ist"],
                            "open": r["open"],
                            "high": r["high"],
                            "low": r["low"],
                            "close": r["close"],
                            "volume": r["volume"],
                            "oi": r["oi"],
                            "underlying_spot": r["underlying_spot"],
                        }
                        for r in chunk
                    ]
                else:
                    db_chunk = [
                        {
                            "security_id": r["security_id"],
                            "exchange_segment": r["exchange_segment"],
                            "symbol": r["symbol"],
                            "datetime_ist": r["datetime_ist"],
                            "open": r["open"],
                            "high": r["high"],
                            "low": r["low"],
                            "close": r["close"],
                            "volume": r["volume"],
                            "oi": r["oi"],
                            "iv": r["iv"],
                            "underlying_spot": r["underlying_spot"],
                        }
                        for r in chunk
                    ]

                ins_stmt = pg_insert(table).values(db_chunk)
                upsert_stmt = ins_stmt.on_conflict_do_update(
                    index_elements=["exchange_segment", "security_id", "datetime_ist"],
                    set_={"close": ins_stmt.excluded.close, "volume": ins_stmt.excluded.volume},
                )
                conn.execute(upsert_stmt)
                total_upserted += len(chunk)

            # Update mkt_download_state
            last_dt = max(r["datetime_ist"] for r in rows)
            state_ins = pg_insert(mkt_download_state_table).values(
                security_id=sec_id,
                exchange_segment=rows[0]["exchange_segment"],
                symbol=meta.symbol,
                instrument_type=meta.instrument_type,
                last_candle_ts=last_dt,
                last_sync_at=datetime.now(UTC),
                sync_status="DONE",
                total_candles=len(rows),
                api_requests_used=0,
            )
            state_upsert = state_ins.on_conflict_do_update(
                index_elements=["exchange_segment", "security_id"],
                set_={
                    "last_candle_ts": state_ins.excluded.last_candle_ts,
                    "last_sync_at": state_ins.excluded.last_sync_at,
                    "sync_status": "DONE",
                    "total_candles": mkt_download_state_table.c.total_candles + len(rows),
                },
            )
            conn.execute(state_upsert)

        # 2. Append to Parquet partitions
        if meta.instrument_type == "EQ":
            # Group by year and month
            by_year_month: dict[tuple[int, int], list[dict[str, Any]]] = {}
            for r in rows:
                key = (r["datetime_ist"].year, r["datetime_ist"].month)
                by_year_month.setdefault(key, []).append(r)

            for (yr, mo), items in by_year_month.items():
                arrow_data = {
                    "datetime_ist": [it["datetime_ist"] for it in items],
                    "open": [it["open"] for it in items],
                    "high": [it["high"] for it in items],
                    "low": [it["low"] for it in items],
                    "close": [it["close"] for it in items],
                    "volume": [it["volume"] for it in items],
                }
                arrow_table = pa.Table.from_pydict(arrow_data, schema=EQUITY_SCHEMA)
                self.archiver.write_equity_candles(meta.symbol, yr, mo, arrow_table)

        elif meta.instrument_type == "FUT":
            exp_folder = meta.expiry_period or "active"
            arrow_data = {
                "datetime_ist": [it["datetime_ist"] for it in rows],
                "open": [it["open"] for it in rows],
                "high": [it["high"] for it in rows],
                "low": [it["low"] for it in rows],
                "close": [it["close"] for it in rows],
                "volume": [it["volume"] for it in rows],
                "oi": [it["oi"] for it in rows],
                "underlying_spot": [it["underlying_spot"] or 0.0 for it in rows],
            }
            arrow_table = pa.Table.from_pydict(arrow_data, schema=FUTURES_SCHEMA)
            self.archiver.write_futures_candles(meta.symbol, exp_folder, arrow_table)

        else:
            exp_folder = meta.expiry_period or "Month_1"
            sign = "+" if meta.strike_offset > 0 else ""
            offset_str = f"{sign}{meta.strike_offset}" if meta.strike_offset != 0 else ""
            strike_file = f"ATM{offset_str}_{meta.option_type}"
            arrow_data = {
                "datetime_ist": [it["datetime_ist"] for it in rows],
                "open": [it["open"] for it in rows],
                "high": [it["high"] for it in rows],
                "low": [it["low"] for it in rows],
                "close": [it["close"] for it in rows],
                "volume": [it["volume"] for it in rows],
                "oi": [it["oi"] for it in rows],
                "iv": [it["iv"] or 0.0 for it in rows],
                "underlying_spot": [it["underlying_spot"] or 0.0 for it in rows],
            }
            arrow_table = pa.Table.from_pydict(arrow_data, schema=OPTIONS_SCHEMA)
            self.archiver.write_options_candles(meta.symbol, exp_folder, strike_file, arrow_table)

        logger.info("Successfully imported %d rows for %s from %s", total_upserted, meta.symbol, p)
        return total_upserted

    def import_directory_recursive(
        self,
        base_dir: Path | str,
        dry_run: bool = False,
    ) -> int:
        """Scan directory and import all CSV files found."""
        p = Path(base_dir)
        if not p.is_dir():
            logger.warning("Directory does not exist: %s", p)
            return 0

        csv_files = sorted(list(p.rglob("*.csv")))
        total_rows = 0
        for f in csv_files:
            try:
                count = self.import_csv_file(f, dry_run=dry_run)
                total_rows += count
            except Exception as exc:
                logger.error("Failed importing CSV %s: %s", f, exc)

        return total_rows
