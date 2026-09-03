"""Restore engine with strict cryptographic integrity and count/hash reconciliation (F13.4)."""

from __future__ import annotations

import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.backup.engine import (
    compute_file_sha256,
    compute_table_hash,
)
from app.backup.models import (
    BackupManifest,
    ReconciliationItem,
    RestoreVerificationReport,
)


class IntegrityCheckFailedError(Exception):
    """Raised when an archive, database table, or partition fails checksum verification."""


class RestoreEngine:
    """Restores a backup archive into a clean environment and reconciles counts and hashes."""

    @staticmethod
    def restore_and_verify(
        archive_path: Path,
        target_dir: Path,
        *,
        expected_manifest: BackupManifest | None = None,
    ) -> RestoreVerificationReport:
        """Extract backup into clean target directory and perform complete reconciliation."""
        if not archive_path.exists():
            raise FileNotFoundError(f"Backup archive not found at {archive_path}")

        # 1. Archive Integrity Verification
        actual_archive_hash = compute_file_sha256(archive_path)
        if expected_manifest and expected_manifest.archive_sha256:
            if actual_archive_hash != expected_manifest.archive_sha256:
                raise IntegrityCheckFailedError(
                    f"Archive hash mismatch: expected {expected_manifest.archive_sha256}, "
                    f"got {actual_archive_hash} (possible corruption or tampering)"
                )

        target_dir.mkdir(parents=True, exist_ok=True)

        # 2. Extract Archive into Target Directory
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=target_dir)

        manifest_file = target_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Restored directory missing manifest.json at {manifest_file}")

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest = BackupManifest.model_validate(manifest_data)

        # 3. Reconciliation Verification
        items: list[ReconciliationItem] = []
        discrepancies: list[str] = []

        # 3a. Reconcile Postgres Database Tables
        db_dir = target_dir / "database"
        for tbl in manifest.tables:
            tbl_file = db_dir / f"{tbl.table_name}.json"
            if not tbl_file.exists():
                discrepancies.append(f"Missing table dump: {tbl.table_name}")
                items.append(
                    ReconciliationItem(
                        name=tbl.table_name,
                        kind="table",
                        manifest_count=tbl.row_count,
                        restored_count=0,
                        manifest_hash=tbl.content_sha256,
                        restored_hash="MISSING",
                        matches=False,
                    )
                )
                continue

            rows: list[dict[str, Any]] = json.loads(tbl_file.read_text(encoding="utf-8"))
            restored_count = len(rows)
            restored_hash = compute_table_hash(rows)

            count_match = restored_count == tbl.row_count
            hash_match = restored_hash == tbl.content_sha256
            is_match = count_match and hash_match

            if not is_match:
                discrepancies.append(
                    f"Table {tbl.table_name} mismatch: rows ({restored_count} vs {tbl.row_count}), "
                    f"hash ({restored_hash} vs {tbl.content_sha256})"
                )

            items.append(
                ReconciliationItem(
                    name=tbl.table_name,
                    kind="table",
                    manifest_count=tbl.row_count,
                    restored_count=restored_count,
                    manifest_hash=tbl.content_sha256,
                    restored_hash=restored_hash,
                    matches=is_match,
                )
            )

        # 3b. Reconcile Warehouse Parquet Files
        warehouse_dir = target_dir / "warehouse"
        for wf in manifest.warehouse_files:
            file_path = warehouse_dir / wf.relative_path
            if not file_path.exists():
                discrepancies.append(f"Missing warehouse partition: {wf.relative_path}")
                items.append(
                    ReconciliationItem(
                        name=wf.relative_path,
                        kind="warehouse_file",
                        manifest_count=wf.size_bytes,
                        restored_count=0,
                        manifest_hash=wf.sha256,
                        restored_hash="MISSING",
                        matches=False,
                    )
                )
                continue

            restored_hash = compute_file_sha256(file_path)
            restored_size = file_path.stat().st_size
            is_match = restored_hash == wf.sha256 and restored_size == wf.size_bytes

            if not is_match:
                discrepancies.append(
                    f"Warehouse file {wf.relative_path} hash mismatch: "
                    f"{restored_hash} vs {wf.sha256}"
                )

            items.append(
                ReconciliationItem(
                    name=wf.relative_path,
                    kind="warehouse_file",
                    manifest_count=wf.size_bytes,
                    restored_count=restored_size,
                    manifest_hash=wf.sha256,
                    restored_hash=restored_hash,
                    matches=is_match,
                )
            )

        # 3c. Reconcile Configuration Files
        config_dir = target_dir / "configs"
        for cf in manifest.config_files:
            file_path = config_dir / cf.relative_path
            if not file_path.exists():
                discrepancies.append(f"Missing config file: {cf.relative_path}")
                items.append(
                    ReconciliationItem(
                        name=cf.relative_path,
                        kind="config_file",
                        manifest_count=cf.size_bytes,
                        restored_count=0,
                        manifest_hash=cf.sha256,
                        restored_hash="MISSING",
                        matches=False,
                    )
                )
                continue

            restored_hash = compute_file_sha256(file_path)
            restored_size = file_path.stat().st_size
            is_match = restored_hash == cf.sha256 and restored_size == cf.size_bytes

            if not is_match:
                discrepancies.append(
                    f"Config file {cf.relative_path} hash mismatch: {restored_hash} vs {cf.sha256}"
                )

            items.append(
                ReconciliationItem(
                    name=cf.relative_path,
                    kind="config_file",
                    manifest_count=cf.size_bytes,
                    restored_count=restored_size,
                    manifest_hash=cf.sha256,
                    restored_hash=restored_hash,
                    matches=is_match,
                )
            )

        all_matched = len(discrepancies) == 0

        return RestoreVerificationReport(
            backup_id=manifest.backup_id,
            restored_at=datetime.now(tz=UTC),
            target_dir=str(target_dir),
            total_items_checked=len(items),
            all_matched=all_matched,
            discrepancies=discrepancies,
            items=items,
        )
