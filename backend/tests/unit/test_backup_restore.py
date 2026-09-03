"""Unit tests for F13.4: Nightly Postgres/Parquet/config backups, retention,
encryption, integrity checks, and clean-box restore.

Proves:
1. Complete backup creation of DB tables, Parquet partitions, and configs.
2. Clean staging box restoration with 100% count and SHA-256 hash reconciliation.
3. Cryptographic tamper detection fails closed on modified bits.
4. Pruning policy removes expired backups while protecting retention threshold.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from app.backup.engine import BackupEngine
from app.backup.pruning import PruningPolicy, prune_backups
from app.backup.restore import IntegrityCheckFailedError, RestoreEngine


@pytest.fixture
def mock_staging_data(tmp_path: Path) -> tuple[dict[str, list[dict[str, Any]]], Path, Path]:
    """Generate synthetic database tables, warehouse Parquet files, and configurations."""
    # Synthetic database state
    db_tables: dict[str, list[dict[str, Any]]] = {
        "orders": [
            {
                "order_id": f"ord_{i}",
                "symbol": "INFY",
                "quantity": 10 * i,
                "price": 1820.5 + i,
                "status": "FILLED",
            }
            for i in range(1, 11)
        ],
        "trades": [
            {
                "trade_id": f"trd_{j}",
                "symbol": "TCS",
                "quantity": 5 * j,
                "price": 3950.0 + j,
            }
            for j in range(1, 6)
        ],
        "paper_accounts": [
            {"account_id": "acc_01", "balance": 1_000_000.0, "currency": "INR"},
            {"account_id": "acc_02", "balance": 500_000.0, "currency": "INR"},
        ],
    }

    # Synthetic Parquet warehouse files
    warehouse_dir = tmp_path / "source_warehouse"
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    (warehouse_dir / "minute").mkdir(parents=True, exist_ok=True)

    (warehouse_dir / "minute" / "NIFTY_20260901.parquet").write_bytes(
        b"PAR1_MOCK_PARQUET_DATA_NIFTY_INDEX_BARS_12345"
    )
    (warehouse_dir / "minute" / "BANKNIFTY_20260901.parquet").write_bytes(
        b"PAR1_MOCK_PARQUET_DATA_BANKNIFTY_INDEX_BARS_67890"
    )

    # Synthetic configuration files
    config_dir = tmp_path / "source_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "grading.yaml").write_text(
        "version: 4\nprofiles:\n  intraday:\n    sharpe: 1.5\n"
    )
    (config_dir / "calendar.yaml").write_text("holidays:\n  - '2026-01-26'\n  - '2026-08-15'\n")

    return db_tables, warehouse_dir, config_dir


def test_clean_box_restore_and_reconciliation(
    tmp_path: Path,
    mock_staging_data: tuple[dict[str, list[dict[str, Any]]], Path, Path],
) -> None:
    """Proof: Restore into a clean staging box succeeds and reconciles counts/hashes."""
    db_tables, warehouse_dir, config_dir = mock_staging_data
    backup_dest = tmp_path / "backups"

    # Step 1: Create backup bundle
    archive_path, manifest = BackupEngine.create_backup(
        backup_dest,
        db_tables=db_tables,
        warehouse_dir=warehouse_dir,
        config_dir=config_dir,
        git_commit="a09b7b8",
        backup_id="backup_proof_01",
    )
    assert archive_path.exists()
    assert manifest.archive_sha256 is not None
    assert len(manifest.tables) == 3
    assert len(manifest.warehouse_files) == 2
    assert len(manifest.config_files) == 2

    # Step 2: Restore into clean target directory (simulating empty staging box)
    clean_box_target = tmp_path / "clean_staging_box"
    report = RestoreEngine.restore_and_verify(
        archive_path,
        clean_box_target,
        expected_manifest=manifest,
    )

    # Step 3: Verify 100% reconciliation
    assert report.all_matched is True
    assert len(report.discrepancies) == 0
    assert report.total_items_checked == 7  # 3 tables + 2 warehouse + 2 configs

    # Reconcile counts
    table_reports = {item.name: item for item in report.items if item.kind == "table"}
    assert table_reports["orders"].restored_count == 10
    assert table_reports["orders"].manifest_count == 10
    assert table_reports["orders"].matches is True

    assert table_reports["trades"].restored_count == 5
    assert table_reports["trades"].manifest_count == 5
    assert table_reports["trades"].matches is True

    assert table_reports["paper_accounts"].restored_count == 2
    assert table_reports["paper_accounts"].matches is True

    # Reconcile Parquet files
    wh_reports = {item.name: item for item in report.items if item.kind == "warehouse_file"}
    assert "minute/NIFTY_20260901.parquet" in wh_reports
    assert wh_reports["minute/NIFTY_20260901.parquet"].matches is True


def test_tamper_detection_fails_closed(
    tmp_path: Path,
    mock_staging_data: tuple[dict[str, list[dict[str, Any]]], Path, Path],
) -> None:
    """Proof: Tampered archive fails integrity check immediately."""
    db_tables, warehouse_dir, config_dir = mock_staging_data
    backup_dest = tmp_path / "backups_tamper"

    archive_path, manifest = BackupEngine.create_backup(
        backup_dest,
        db_tables=db_tables,
        warehouse_dir=warehouse_dir,
        config_dir=config_dir,
        git_commit="a09b7b8",
    )

    # Tamper with archive: mutate last byte of the file
    content = bytearray(archive_path.read_bytes())
    content[-1] = (content[-1] + 1) % 256
    archive_path.write_bytes(bytes(content))

    # Restore must raise IntegrityCheckFailedError
    with pytest.raises(IntegrityCheckFailedError) as exc_info:
        RestoreEngine.restore_and_verify(
            archive_path,
            tmp_path / "tampered_target",
            expected_manifest=manifest,
        )
    assert "Archive hash mismatch" in str(exc_info.value)


def test_backup_retention_pruning(tmp_path: Path) -> None:
    """Proof: Pruner enforces max_daily retention while preserving min_retained snapshots."""
    backup_dir = tmp_path / "retention_dir"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create 8 dummy backup archives with artificial mtimes
    archives: list[Path] = []
    base_time = time.time() - 86400 * 10
    for idx in range(8):
        arch = backup_dir / f"backup_snapshot_{idx:02d}.tar.gz"
        arch.write_bytes(b"MOCK_ARCHIVE_DATA")
        manifest = backup_dir / f"backup_snapshot_{idx:02d}.manifest.json"
        manifest.write_text("{}", encoding="utf-8")

        # Artificial timestamp: newer snapshots have larger mtime
        mtime = base_time + idx * 3600
        os.utime(arch, (mtime, mtime))
        archives.append(arch)

    # Retention policy: keep 5 latest, min_retained=3
    deleted = prune_backups(backup_dir, PruningPolicy(max_daily=5, min_retained=3))

    assert len(deleted) == 3
    remaining = [f for f in backup_dir.iterdir() if f.name.endswith(".tar.gz")]
    assert len(remaining) == 5

    # Newest snapshots (indices 3, 4, 5, 6, 7) must remain intact
    for idx in range(3, 8):
        assert (backup_dir / f"backup_snapshot_{idx:02d}.tar.gz").exists()
        assert (backup_dir / f"backup_snapshot_{idx:02d}.manifest.json").exists()

    # Oldest snapshots (indices 0, 1, 2) must have been safely pruned
    for idx in range(3):
        assert not (backup_dir / f"backup_snapshot_{idx:02d}.tar.gz").exists()
        assert not (backup_dir / f"backup_snapshot_{idx:02d}.manifest.json").exists()
