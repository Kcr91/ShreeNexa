"""Warehouse reader: DuckDB-powered analytical queries with partition pruning."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa

from app.warehouse.manifest import CurrentPointer, PartitionMetadata, WarehouseManifest
from app.warehouse.schema import BAR_SCHEMA_PYARROW

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


def _normalize_iso(val: datetime | str | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        ts = val if val.tzinfo is not None else val.replace(tzinfo=UTC)
        return ts.isoformat()
    return str(val)


class WarehouseReader:
    """Read-only query engine over published immutable Parquet partitions using DuckDB."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_root = Path(data_root).resolve() if data_root else DEFAULT_DATA_ROOT.resolve()

    def get_current_pointer(self) -> CurrentPointer | None:
        """Read and parse the current active version pointer."""
        pointer_path = self.data_root / "warehouse" / "current.json"
        if not pointer_path.is_file():
            return None
        try:
            data = json.loads(pointer_path.read_text(encoding="utf-8"))
            return CurrentPointer.model_validate(data)
        except Exception as exc:
            logger.error("Failed to parse current pointer at %s: %s", pointer_path, exc)
            return None

    def get_manifest(self, warehouse_version: str | None = None) -> WarehouseManifest:
        """Retrieve manifest for a specific warehouse version or the current active version."""
        version = warehouse_version
        if not version:
            pointer = self.get_current_pointer()
            if not pointer:
                raise FileNotFoundError("No active warehouse version published")
            version = pointer.warehouse_version

        manifest_path = self.data_root / "warehouse" / "manifests" / f"manifest-{version}.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Manifest not found for warehouse version: {version}")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return WarehouseManifest.model_validate(data)

    def prune_partitions(
        self,
        manifest: WarehouseManifest,
        symbols: list[str] | None = None,
        segment: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[PartitionMetadata]:
        """Prune manifest partitions based on query filters."""
        matched: list[PartitionMetadata] = []
        sym_set = {s.upper() for s in symbols} if symbols else None

        for part in manifest.partitions:
            if segment and part.exchange_segment.upper() != segment.upper():
                continue

            if sym_set and not (set(part.symbols) & sym_set):
                continue

            if start_time and part.max_ts < start_time:
                continue

            if end_time and part.min_ts > end_time:
                continue

            matched.append(part)

        return matched

    def query_bars(
        self,
        symbols: list[str] | None = None,
        segment: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        warehouse_version: str | None = None,
    ) -> pa.Table:
        """Query OHLCV bars across published partitions with partition pruning."""
        manifest = self.get_manifest(warehouse_version=warehouse_version)
        version = manifest.warehouse_version

        s_time_iso = _normalize_iso(start_time)
        e_time_iso = _normalize_iso(end_time)

        pruned = self.prune_partitions(
            manifest=manifest,
            symbols=symbols,
            segment=segment,
            start_time=s_time_iso,
            end_time=e_time_iso,
        )

        if not pruned:
            return pa.Table.from_arrays(
                [
                    pa.array([], type=pa.timestamp("ms", tz="UTC")),
                    pa.array([], type=pa.string()),
                    pa.array([], type=pa.string()),
                    pa.array([], type=pa.string()),
                    pa.array([], type=pa.float64()),
                    pa.array([], type=pa.float64()),
                    pa.array([], type=pa.float64()),
                    pa.array([], type=pa.float64()),
                    pa.array([], type=pa.int64()),
                    pa.array([], type=pa.int64()),
                ],
                schema=BAR_SCHEMA_PYARROW,
            )

        file_paths = [
            str(self.data_root / "warehouse" / "versions" / version / p.relative_path).replace(
                "\\", "/"
            )
            for p in pruned
        ]

        # Execute DuckDB query
        con = duckdb.connect(":memory:")
        try:
            # Build query with optional exact predicates
            query = "SELECT * FROM read_parquet(?)"
            predicates: list[str] = []
            params: list[Any] = [file_paths]

            if symbols:
                upper_syms = [s.upper() for s in symbols]
                predicates.append("symbol IN (" + ", ".join(["?"] * len(upper_syms)) + ")")
                params.extend(upper_syms)

            if segment:
                predicates.append("exchange_segment = ?")
                params.append(segment.upper())

            if s_time_iso:
                predicates.append("timestamp >= ?")
                params.append(s_time_iso)

            if e_time_iso:
                predicates.append("timestamp <= ?")
                params.append(e_time_iso)

            if predicates:
                query += " WHERE " + " AND ".join(predicates)

            query += " ORDER BY timestamp ASC, symbol ASC"

            arrow_table: pa.Table = con.execute(query, params).to_arrow_table()
            return arrow_table
        finally:
            con.close()
