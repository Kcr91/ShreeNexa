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
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from app.warehouse import paths
from app.warehouse.manifest import (
    CorrectionMetadata,
    CurrentPointer,
    PartitionMetadata,
    WarehouseManifest,
)
from app.warehouse.schema import BarRecord, bars_to_arrow_table

logger = logging.getLogger(__name__)

REPO_ROOT = paths.REPO_ROOT
# Re-exported for backwards compatibility; resolve_data_root is the real entry point.
DEFAULT_DATA_ROOT = paths.DEFAULT_DATA_ROOT


class WarehousePublisher:
    """Publishes versioned immutable Parquet partitions and maintains the atomic version pointer."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_root = paths.resolve_data_root(data_root)
        self._batch_version: str | None = None
        self._batch_partitions: list[PartitionMetadata] = []
        self._batch_ingest_ids: list[str] = []
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

    def begin_batch(self, warehouse_version: str) -> None:
        """Collect subsequent publishes into one version instead of publishing each.

        Publishing once per window rewrites the whole manifest every time, which is
        quadratic in the number of partitions. Batching turns N manifest rewrites into
        one. Nothing is durable until flush_batch succeeds, so callers must not
        checkpoint work until then.
        """
        self._batch_version = warehouse_version
        self._batch_partitions = []
        self._batch_ingest_ids = []

    def batch_is_open(self) -> bool:
        """Whether publishes are currently being accumulated."""
        return self._batch_version is not None

    def batch_size(self) -> int:
        """Partitions staged into the open batch so far."""
        return len(self._batch_partitions)

    def flush_batch(
        self,
        actor: str = "worker",
        reason: str = "batched_append",
        code_commit: str | None = None,
    ) -> CurrentPointer | None:
        """Publish everything accumulated since begin_batch, then close the batch."""
        version = self._batch_version
        partitions = list(self._batch_partitions)
        ingest_ids = list(self._batch_ingest_ids)
        self._batch_version = None
        self._batch_partitions = []
        self._batch_ingest_ids = []

        if version is None or not partitions:
            return None

        return self.publish_version(
            warehouse_version=version,
            partitions=partitions,
            source_ingest_ids=ingest_ids,
            code_commit=code_commit,
            merge_with_current=True,
            actor=actor,
            reason=reason,
        )

    def abandon_batch(self) -> None:
        """Drop an open batch without publishing. Staged files are left for cleanup."""
        self._batch_version = None
        self._batch_partitions = []
        self._batch_ingest_ids = []

    def _merge_with_current(
        self,
        new_version: str,
        new_partitions: list[PartitionMetadata],
        parent_version: str | None,
    ) -> tuple[list[PartitionMetadata], str | None]:
        """Carry the current manifest's partitions forward into a new version.

        Returns the merged partition list and the parent version to record. New
        partitions win on a relative-path collision so a corrected window supersedes
        the original rather than being stored twice.
        """
        pointer_file = self.data_root / "warehouse" / "current.json"
        if not pointer_file.is_file():
            return list(new_partitions), parent_version

        try:
            pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
            current_version = str(pointer["warehouse_version"])
            manifest_file = (
                self.data_root / "warehouse" / "manifests" / f"manifest-{current_version}.json"
            )
            previous = WarehouseManifest.model_validate(
                json.loads(manifest_file.read_text(encoding="utf-8"))
            )
        except (OSError, KeyError, ValueError) as exc:
            # A missing or unreadable predecessor must not silently drop history.
            raise RuntimeError(
                f"Cannot append to warehouse version {new_version}: the current manifest "
                f"could not be read ({exc}). Refusing to publish a manifest that would "
                "orphan previously published partitions."
            ) from exc

        merged: dict[str, PartitionMetadata] = {}
        for part in previous.partitions:
            merged[part.relative_path] = part.model_copy(
                update={"source_version": part.source_version or previous.warehouse_version}
            )
        for part in new_partitions:
            merged[part.relative_path] = part

        return list(merged.values()), parent_version or current_version

    def append_to_current(
        self,
        warehouse_version: str,
        partitions: list[PartitionMetadata],
        **kwargs: Any,
    ) -> CurrentPointer | None:
        """Publish a version that accumulates on top of the current one.

        Returns None while a batch is open, in which case the partitions are recorded
        for the eventual flush_batch rather than published immediately.
        """
        kwargs.setdefault("reason", "append")
        return self.publish_version(
            warehouse_version, partitions, merge_with_current=True, **kwargs
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
        merge_with_current: bool = False,
    ) -> CurrentPointer | None:
        """Promote staging atomically, write the manifest, and replace the active pointer.

        With ``merge_with_current`` the new manifest also carries forward every partition
        from the currently published version. Without it each publish supersedes the last,
        so a backfill that publishes once per window leaves only the final window
        reachable - which is exactly what happened on the first live run: 527,758 rows on
        disk across 41 versions, of which a query returned 23,663.

        Carried-forward partitions are referenced in place via ``source_version``; nothing
        is copied. A new partition sharing a relative path with an old one supersedes it,
        so re-fetching a corrected window replaces rather than duplicates it.
        """
        if self._batch_version is not None:
            # A batch is open: record the partitions and defer the manifest rewrite.
            self._batch_partitions.extend(partitions)
            self._batch_ingest_ids.extend(source_ingest_ids or [])
            return None

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

        effective_parent = parent_version
        merged_partitions = list(partitions)
        if merge_with_current:
            merged_partitions, effective_parent = self._merge_with_current(
                warehouse_version, partitions, parent_version
            )

        # Build and write manifest
        manifest = WarehouseManifest(
            warehouse_version=warehouse_version,
            parent_version=effective_parent,
            created_at=datetime.now(UTC).isoformat(),
            code_commit=code_commit or "dev_local",
            source_ingest_ids=source_ingest_ids or [],
            corrections=corrections or [],
            partitions=merged_partitions,
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
