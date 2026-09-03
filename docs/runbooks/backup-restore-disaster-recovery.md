# Operational Runbook: Backups, Retention, and Disaster Recovery Restoration (F13.4)

## Overview

This runbook outlines the operational procedures for nightly backups, cryptographic integrity validation, retention policy pruning, and clean-box disaster recovery restoration for ShreeNexa Terminal.

---

## 1. Backup Scope & Topology

Nightly backups capture all three authoritative state stores of ShreeNexa:

1. **Postgres Transactional State**:
   - Master ledger, trade orders, positions, risk journals, paper deployment accounts, and audit records.
   - Dumped with exact row counts and deterministic content digests stored in `manifest.json`.
2. **DuckDB Parquet Historical Warehouse**:
   - Immutable minute/daily market bars, order book snapshots, and calibrated option chains under `data/warehouse/`.
   - Recorded with file-level SHA-256 hashes and byte counts.
3. **Configuration & Strategy Definitions**:
   - Metric grading scorecards, trading calendar definitions, Caddy reverse-proxy topology, and manifest files.
   - Credentials and broker secrets are strictly redacted prior to archiving.

---

## 2. Nightly Backup Schedule & Systemd Timer

On the AWS Lightsail host (`ap-south-1`), backups execute nightly at **02:00 IST** (20:30 UTC):

```bash
# Verify systemd timer status
systemctl status shreenexa-backup.timer

# Run manual on-demand backup
/opt/shreenexa/infra/lightsail/backup.sh
```

---

## 3. Retention Policy & Pruning

- **Daily Retention**: 30 daily snapshots retained locally.
- **Minimum Retained**: The latest 5 snapshots are permanently protected against accidental deletion.
- **Pruning Command**:
  ```python
  from pathlib import Path
  from app.backup.pruning import prune_backups, PruningPolicy

  prune_backups(Path("/opt/shreenexa/backups"), PruningPolicy(max_daily=30, min_retained=5))
  ```

---

## 4. Step-by-Step Clean-Box Disaster Recovery Restoration

When provisioning a clean staging instance or recovering from catastrophic hardware failure:

### Step 1: Transfer Backup Bundle
Transfer the desired `backup_<timestamp>.tar.gz` and its companion `.manifest.json` to the target server.

### Step 2: Verify Archive Checksum
```bash
sha256sum backup_20260903_020000.tar.gz
# Compare against the recorded "archive_sha256" in backup_20260903_020000.manifest.json
```

### Step 3: Execute Restoration Engine
```python
from pathlib import Path
from app.backup.restore import RestoreEngine

report = RestoreEngine.restore_and_verify(
    archive_path=Path("/opt/shreenexa/backups/backup_20260903_020000.tar.gz"),
    target_dir=Path("/opt/shreenexa/data_restored"),
)

if not report.all_matched:
    raise RuntimeError(f"Restoration failed reconciliation: {report.discrepancies}")
print("100% of tables, rows, files, and cryptographic hashes reconciled successfully!")
```

### Step 4: Reconcile Postgres & DuckDB
- Load restored SQL/JSON table dumps into Postgres.
- Re-link `/opt/shreenexa/data/warehouse` to the restored Parquet partitions.
- Start services via systemd (`shreenexa-engine`, `shreenexa-feedd`, `shreenexa-worker`, `shreenexa-caddy`).
