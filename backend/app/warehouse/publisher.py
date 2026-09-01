"""Warehouse publisher: staging, validation, atomic promotion, manifests, and pointer updates."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from app.warehouse.manifest import (
    CorrectionMetadata,
    CurrentPointer,
    PartitionMetadata,
    WarehouseManifest,
)
from app.warehouse.schema import BarRecord, bars_to_arrow_table

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


class WarehousePublisher:
    """Publishes versioned immutable Parquet partitions and maintains the atomic version pointer."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_root = Path(data_root).resolve() if data_root else DEFAULT_DATA_ROOT.resolve()
        self.ensure_data_root()

    def ensure_data_root(self) -> None:
        """Initialize data root directory, marker, and required subdirectories."""
        self.data_root.mkdir(parents=True, exist_ok=True)
        marker_path = self.data_root / ".shreenexa-data-root.json"
        if not marker_path.exists():
            marker_data = {
                "format_version": 1,
                "project": "shreenexa-terminal",
                "root_id": uuid.uuid4().hex,
                "created_at": datetime.now(UTC).isoformat(),
            }
            marker_path.write_text(json.dumps(marker_data, indent=2), encoding="utf-8")

        (self.data_root / "raw").mkdir(exist_ok=True)
        (self.data_root / "staging").mkdir(exist_ok=True)
        (self.data_root / "warehouse" / "manifests").mkdir(parents=True, exist_ok=True)
        (self.data_root / "warehouse" / "versions").mkdir(parents=True, exist_ok=True)
        (self.data_root / "quarantine").mkdir(exist_ok=True)
        (self.data_root / "exports").mkdir(exist_ok=True)
        (self.data_root / "cache").mkdir(exist_ok=True)
        (self.data_root / "tmp").mkdir(exist_ok=True)

    def stage_partition(
        self,
        warehouse_version: str,
        data: pa.Table | list[BarRecord],
        relative_path: str,
    ) -> PartitionMetadata:
        """Write a partition Parquet file into staging and compute its metadata."""
        if isinstance(data, list):
            table = bars_to_arrow_table(data)
        else:
            table = data

        target_file = self.data_root / "staging" / warehouse_version / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        pq.write_table(table, target_file, compression="zstd")

        # Compute SHA-256 and byte size
        file_bytes = target_file.read_bytes()
        digest = hashlib.sha256(file_bytes).hexdigest()
        byte_size = len(file_bytes)
        row_count = table.num_rows

        if row_count > 0:
            ts_col = table.column("timestamp")
            # Convert pyarrow timestamps to ISO strings
            min_ts = ts_col[0].as_py()
            max_ts = ts_col[-1].as_py()
            min_ts_str = min_ts.isoformat() if hasattr(min_ts, "isoformat") else str(min_ts)
            max_ts_str = max_ts.isoformat() if hasattr(max_ts, "isoformat") else str(max_ts)

            segment_col = table.column("exchange_segment")
            segments = sorted(set(segment_col.to_pylist()))
            exchange_segment = segments[0] if segments else "UNKNOWN"

            symbol_col = table.column("symbol")
            symbols = sorted(set(symbol_col.to_pylist()))
        else:
            now_iso = datetime.now(UTC).isoformat()
            min_ts_str = now_iso
            max_ts_str = now_iso
            exchange_segment = "UNKNOWN"
            symbols = []

        return PartitionMetadata(
            relative_path=relative_path.replace("\\", "/"),
            sha256=digest,
            bytes=byte_size,
            rows=row_count,
            min_ts=min_ts_str,
            max_ts=max_ts_str,
            exchange_segment=exchange_segment,
            symbols=symbols,
        )

    def publish_version(
        self,
        warehouse_version: str,
        partitions: list[PartitionMetadata],
        parent_version: str | None = None,
        source_ingest_ids: list[str] | None = None,
        corrections: list[CorrectionMetadata] | None = None,
        code_commit: str | None = None,
        actor: str = "worker",
        reason: str = "initial_publish",
    ) -> CurrentPointer:
        """Promote staging directory atomically, write manifest, and replace active pointer."""
        staging_dir = self.data_root / "staging" / warehouse_version
        version_dir = self.data_root / "warehouse" / "versions" / warehouse_version

        if not staging_dir.is_dir():
            raise FileNotFoundError(f"Staging directory for version {warehouse_version} not found")

        # Verify staged files match partition metadata digests
        for part in partitions:
            p_file = staging_dir / part.relative_path
            if not p_file.is_file():
                raise FileNotFoundError(f"Missing staged partition file: {p_file}")
            actual_digest = hashlib.sha256(p_file.read_bytes()).hexdigest()
            if actual_digest != part.sha256:
                raise ValueError(
                    f"Checksum mismatch on {part.relative_path}: "
                    f"expected {part.sha256}, got {actual_digest}"
                )

        # Atomic move from staging to warehouse/versions
        version_dir.parent.mkdir(parents=True, exist_ok=True)
        if version_dir.exists():
            raise FileExistsError(f"Warehouse version {warehouse_version} already published")

        shutil.move(str(staging_dir), str(version_dir))

        # Build and write manifest
        manifest = WarehouseManifest(
            warehouse_version=warehouse_version,
            parent_version=parent_version,
            created_at=datetime.now(UTC).isoformat(),
            code_commit=code_commit or "dev_local",
            source_ingest_ids=source_ingest_ids or [],
            corrections=corrections or [],
            partitions=partitions,
        )
        manifest_digest = manifest.compute_sha256()
        manifest_file = (
            self.data_root / "warehouse" / "manifests" / f"manifest-{warehouse_version}.json"
        )
        manifest_file.write_text(manifest.to_canonical_json(), encoding="utf-8")

        # Determine pointer generation
        current_pointer_file = self.data_root / "warehouse" / "current.json"
        generation = 1
        if current_pointer_file.exists():
            try:
                prev_data = json.loads(current_pointer_file.read_text(encoding="utf-8"))
                generation = int(prev_data.get("pointer_generation", 0)) + 1
            except Exception:
                generation = 1

        pointer = CurrentPointer(
            warehouse_version=warehouse_version,
            manifest_sha256=manifest_digest,
            pointer_generation=generation,
            changed_at=datetime.now(UTC).isoformat(),
            actor=actor,
            reason=reason,
        )

        # Atomic pointer file replacement
        tmp_pointer = self.data_root / "warehouse" / "current.json.tmp"
        tmp_pointer.write_text(pointer.to_json(), encoding="utf-8")
        os.replace(tmp_pointer, current_pointer_file)

        logger.info(
            "Successfully published warehouse version %s (generation %d, partitions %d)",
            warehouse_version,
            generation,
            len(partitions),
        )
        return pointer

    def rollback_to(
        self,
        target_version: str,
        actor: str = "worker",
        reason: str = "rollback",
    ) -> CurrentPointer:
        """Rollback active version pointer to an existing validated historical warehouse version."""
        manifest_file = (
            self.data_root / "warehouse" / "manifests" / f"manifest-{target_version}.json"
        )
        version_dir = self.data_root / "warehouse" / "versions" / target_version

        if not manifest_file.is_file():
            raise FileNotFoundError(f"Manifest for version {target_version} not found")
        if not version_dir.is_dir():
            raise FileNotFoundError(f"Version directory for {target_version} not found")

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest = WarehouseManifest.model_validate(manifest_data)
        manifest_digest = manifest.compute_sha256()

        current_pointer_file = self.data_root / "warehouse" / "current.json"
        generation = 1
        if current_pointer_file.exists():
            try:
                prev_data = json.loads(current_pointer_file.read_text(encoding="utf-8"))
                generation = int(prev_data.get("pointer_generation", 0)) + 1
            except Exception:
                generation = 1

        pointer = CurrentPointer(
            warehouse_version=target_version,
            manifest_sha256=manifest_digest,
            pointer_generation=generation,
            changed_at=datetime.now(UTC).isoformat(),
            actor=actor,
            reason=reason,
        )

        tmp_pointer = self.data_root / "warehouse" / "current.json.tmp"
        tmp_pointer.write_text(pointer.to_json(), encoding="utf-8")
        os.replace(tmp_pointer, current_pointer_file)

        logger.info(
            "Rolled back warehouse to version %s (generation %d)",
            target_version,
            generation,
        )
        return pointer
