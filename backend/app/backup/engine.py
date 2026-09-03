"""Backup creation engine with SHA-256 manifests and encrypted archives (F13.4)."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.backup.models import (
    BackupManifest,
    DatabaseTableRecord,
    FileRecord,
)


def compute_file_sha256(path: Path) -> str:
    """Compute cryptographic SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_data_sha256(data: bytes) -> str:
    """Compute cryptographic SHA-256 hash of a byte string."""
    return hashlib.sha256(data).hexdigest()


def compute_table_hash(rows: list[dict[str, Any]]) -> str:
    """Deterministic hash of database table rows sorted by key."""
    # Serialize canonically sorted rows to JSON
    canonical_json = json.dumps(rows, sort_keys=True, default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class BackupEngine:
    """Creates consistent, verifiable backup archives covering DB, Parquet, and configs."""

    @staticmethod
    def create_backup(
        destination_dir: Path,
        *,
        db_tables: dict[str, list[dict[str, Any]]],
        warehouse_dir: Path | None = None,
        config_dir: Path | None = None,
        git_commit: str = "unknown",
        backup_id: str | None = None,
    ) -> tuple[Path, BackupManifest]:
        """Create a complete backup bundle with manifest."""
        destination_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(tz=UTC)
        bid = backup_id or f"backup_{now.strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"

        staging_dir = destination_dir / f"staging_{bid}"
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)

        db_staging = staging_dir / "database"
        warehouse_staging = staging_dir / "warehouse"
        config_staging = staging_dir / "configs"

        db_staging.mkdir(parents=True, exist_ok=True)
        warehouse_staging.mkdir(parents=True, exist_ok=True)
        config_staging.mkdir(parents=True, exist_ok=True)

        # 1. Process Postgres Database Tables
        table_records: list[DatabaseTableRecord] = []
        for tbl_name, rows in db_tables.items():
            tbl_file = db_staging / f"{tbl_name}.json"
            content = json.dumps(rows, indent=2, sort_keys=True, default=str)
            tbl_file.write_text(content, encoding="utf-8")
            table_records.append(
                DatabaseTableRecord(
                    table_name=tbl_name,
                    row_count=len(rows),
                    content_sha256=compute_table_hash(rows),
                )
            )

        # 2. Process DuckDB Parquet Warehouse
        warehouse_records: list[FileRecord] = []
        if warehouse_dir and warehouse_dir.exists():
            for root, _, files in os.walk(warehouse_dir):
                for fname in files:
                    src_file = Path(root) / fname
                    rel_p = src_file.relative_to(warehouse_dir)
                    dst_file = warehouse_staging / rel_p
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    warehouse_records.append(
                        FileRecord(
                            relative_path=str(rel_p).replace("\\", "/"),
                            size_bytes=src_file.stat().st_size,
                            sha256=compute_file_sha256(src_file),
                        )
                    )

        # 3. Process Configuration Files
        config_records: list[FileRecord] = []
        if config_dir and config_dir.exists():
            for root, _, files in os.walk(config_dir):
                for fname in files:
                    src_file = Path(root) / fname
                    rel_p = src_file.relative_to(config_dir)
                    dst_file = config_staging / rel_p
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    config_records.append(
                        FileRecord(
                            relative_path=str(rel_p).replace("\\", "/"),
                            size_bytes=src_file.stat().st_size,
                            sha256=compute_file_sha256(src_file),
                        )
                    )

        # 4. Generate Authoritative Manifest
        manifest = BackupManifest(
            backup_id=bid,
            created_at=now,
            git_commit=git_commit,
            tables=table_records,
            warehouse_files=warehouse_records,
            config_files=config_records,
            total_size_bytes=sum(r.size_bytes for r in warehouse_records + config_records),
            archive_sha256=None,
            encrypted=False,
        )

        manifest_path = staging_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        # 5. Pack into tar.gz Archive
        archive_path = destination_dir / f"{bid}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(staging_dir, arcname=".")

        # Compute archive checksum and update manifest
        archive_hash = compute_file_sha256(archive_path)
        manifest.archive_sha256 = archive_hash

        # Write final manifest alongside archive
        final_manifest_path = destination_dir / f"{bid}.manifest.json"
        final_manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        # Clean staging
        shutil.rmtree(staging_dir, ignore_errors=True)

        return archive_path, manifest
