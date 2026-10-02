"""Parquet partition archiver and DuckDB storage manager for high-speed historical analytics."""

from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MARKET_DATA_DIR = REPO_ROOT / "data" / "market"

# Canonical Arrow Schemas
EQUITY_SCHEMA = pa.schema(
    [
        ("datetime_ist", pa.timestamp("us", tz="Asia/Kolkata")),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),
    ]
)

FUTURES_SCHEMA = pa.schema(
    [
        ("datetime_ist", pa.timestamp("us", tz="Asia/Kolkata")),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),
        ("oi", pa.int64()),
        ("underlying_spot", pa.float64()),
    ]
)

OPTIONS_SCHEMA = pa.schema(
    [
        ("datetime_ist", pa.timestamp("us", tz="Asia/Kolkata")),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),
        ("oi", pa.int64()),
        ("iv", pa.float64()),
        ("underlying_spot", pa.float64()),
    ]
)


class ParquetArchiver:
    """Manages appending and partitioning 1-min OHLCV bars into structured Parquet directories."""

    def __init__(self, base_data_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_data_dir) if base_data_dir else DEFAULT_MARKET_DATA_DIR
        self.equity_dir = self.base_dir / "equity"
        self.futures_dir = self.base_dir / "futures"
        self.options_dir = self.base_dir / "options"

    def write_equity_candles(
        self,
        symbol: str,
        year: int | str,
        month: int | str,
        table: pa.Table,
    ) -> Path:
        """Write or append monthly equity partition: equity/{SYMBOL}/{YEAR}/{MM}.parquet."""
        mm = f"{int(month):02d}"
        target_dir = self.equity_dir / symbol.upper() / str(year)
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{mm}.parquet"

        if file_path.exists():
            existing_table = pq.read_table(file_path)
            combined = pa.concat_tables([existing_table, table]).combine_chunks()
            # De-duplicate by datetime_ist
            df = (
                combined.to_pandas()
                .drop_duplicates(subset=["datetime_ist"])
                .sort_values("datetime_ist")
            )
            final_table = pa.Table.from_pandas(df, schema=EQUITY_SCHEMA, preserve_index=False)
            pq.write_table(final_table, file_path, compression="zstd")
        else:
            pq.write_table(table, file_path, compression="zstd")

        return file_path

    def write_futures_candles(
        self,
        symbol: str,
        expiry_folder: str,
        table: pa.Table,
    ) -> Path:
        """Write or append futures partition: futures/{SYMBOL}/{EXPIRY}/candles.parquet."""
        target_dir = self.futures_dir / symbol.upper() / expiry_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / "candles.parquet"

        if file_path.exists():
            existing_table = pq.read_table(file_path)
            combined = pa.concat_tables([existing_table, table]).combine_chunks()
            df = (
                combined.to_pandas()
                .drop_duplicates(subset=["datetime_ist"])
                .sort_values("datetime_ist")
            )
            final_table = pa.Table.from_pandas(df, schema=FUTURES_SCHEMA, preserve_index=False)
            pq.write_table(final_table, file_path, compression="zstd")
        else:
            pq.write_table(table, file_path, compression="zstd")

        return file_path

    def write_options_candles(
        self,
        symbol: str,
        expiry_folder: str,
        strike_file: str,
        table: pa.Table,
    ) -> Path:
        """Write or append options partition: options/{SYMBOL}/{EXPIRY}/{STRIKE}.parquet."""
        target_dir = self.options_dir / symbol.upper() / expiry_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = strike_file if strike_file.endswith(".parquet") else f"{strike_file}.parquet"
        file_path = target_dir / file_name

        if file_path.exists():
            existing_table = pq.read_table(file_path)
            combined = pa.concat_tables([existing_table, table]).combine_chunks()
            df = (
                combined.to_pandas()
                .drop_duplicates(subset=["datetime_ist"])
                .sort_values("datetime_ist")
            )
            final_table = pa.Table.from_pandas(df, schema=OPTIONS_SCHEMA, preserve_index=False)
            pq.write_table(final_table, file_path, compression="zstd")
        else:
            pq.write_table(table, file_path, compression="zstd")

        return file_path
