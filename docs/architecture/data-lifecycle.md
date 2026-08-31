# Data Lifecycle, Versioning, Backup, and Capacity Policy

## 1. Path contract

### 1.1 Primary root

The default is `<repository>\data` (`F:\ShreeNexa\data` in the audited checkout). Runtime code resolves the repository root first and appends `data`; it does not scatter hard-coded absolute paths through modules.

An optional `SHREENEXA_DATA_ROOT` override is valid only when all checks pass:

1. Expand environment syntax and resolve symlinks/junctions to a canonical absolute Windows path.
2. Reject a relative path, drive root, UNC/network share unless separately approved, Windows temporary directory, repository source root, or any ancestor of the repository.
3. Reject the legacy-project path, its ancestors, and its descendants.
4. Require every derived write target to remain a descendant of the canonical data root after resolution.
5. On first initialization, create an ownership marker only after explicit confirmation by the owning feature. On later use, require the existing marker to match this project.

Marker contract:

```json
{
  "format_version": 1,
  "project": "shreenexa-terminal",
  "root_id": "UUID generated once",
  "created_at": "UTC RFC3339 timestamp"
}
```

The marker contains no username, token, account identifier, or secret. M0.3 does not create it.

### 1.2 Backup root

`SHREENEXA_BACKUP_ROOT`, when introduced, must resolve outside the primary data root and repository. A directory on the same physical disk may be a convenient export but is not a disaster-recovery backup. Epic 13 selects an encrypted destination in a separate failure domain and proves restore.

## 2. Directory ownership

```text
<data-root>/
  .shreenexa-data-root.json       ownership marker
  raw/                            immutable provider response artifacts
  staging/                        incomplete downloads/transforms; never queryable
  warehouse/
    manifests/                    immutable version manifests
    versions/<warehouse-id>/      immutable published partition trees
    current.json                  atomically replaced validated-version pointer
  quarantine/                     failed hash/schema/provenance validation
  services/
    postgres/                     local Postgres persistence, when configured
    redis/                        reconstructible local Redis persistence
  exports/                        user-requested, reproducible exports
  cache/                          reconstructible local acceleration
  tmp/                            bounded same-volume temporary work
```

| Path | Writer | Mutation rule | Durable class |
|---|---|---|---|
| `raw/` | `worker` | Append new ingest only | Durable, backed up |
| `staging/` | `worker` | Mutable while leased; never read as published data | Reconstructible |
| `warehouse/manifests/` | `worker` | Create once | Durable, backed up |
| `warehouse/versions/` | `worker` | Publish once; immutable afterwards | Durable, backed up |
| `warehouse/current.json` | `worker` | Atomic pointer replacement only | Durable metadata, backed up |
| `quarantine/` | `worker` | Append evidence; manual disposition | Diagnostic until reviewed |
| `services/postgres/` | Postgres | Database-managed | Durable through tested database backup |
| `services/redis/` | Redis | Reconstructible | Not a backup source |
| `exports/`, `cache/`, `tmp/` | Owning job | Replaceable and bounded | Excluded unless explicitly promoted |

## 3. Immutable raw-ingest contract

Each completed ingest receives an ID such as `ri-20260831T170501Z-7f3a2c1d` and contains:

```text
raw/<provider>/<dataset>/<YYYY>/<MM>/<ingest-id>/
  payload.<source-extension>       exact successful response bytes
  metadata.json                    redacted provenance
```

Required metadata fields:

- format version and ingest ID;
- provider, documented endpoint class, dataset, and non-secret request parameters;
- requested and observed time ranges;
- acquisition start/finish UTC timestamps;
- HTTP/status classification and provider schema/version when available;
- payload byte count and SHA-256;
- code commit, client/adapter version, retry lineage, and optional parent ingest ID;
- explicit redaction list proving authorization headers, cookies, client IDs, tokens, and signed URLs were not persisted.

The flow is `requested -> staging -> verified -> committed` or `requested -> staging -> quarantined/failed`. There is no transition from `committed` back to a mutable state. An upstream correction creates a new ingest ID and links to the prior artifact.

## 4. Warehouse version contract

### 4.1 Identity and manifest

A warehouse version ID is unique and sortable, for example `wv-20260831T172000Z-a12f09c4`. Reproducible identity is the full SHA-256 of the canonical manifest bytes; the human-readable ID alone is not sufficient.

Every immutable manifest records:

```json
{
  "format_version": 1,
  "warehouse_version": "wv-20260831T172000Z-a12f09c4",
  "parent_version": "wv-... or null",
  "created_at": "UTC RFC3339 timestamp",
  "code_commit": "full Git commit",
  "schema_versions": {"bars": 1, "options": 1},
  "source_ingest_ids": ["ri-..."],
  "corrections": [{"reason": "...", "replaces_partition_digest": "..."}],
  "partitions": [{
    "relative_path": "bars/segment=NSE_EQ/.../part-000.parquet",
    "sha256": "full digest",
    "bytes": 0,
    "rows": 0,
    "min_ts": "...",
    "max_ts": "..."
  }]
}
```

Canonical serialization, field ordering, timestamp normalization, and digest calculation are specified in F1.1 tests. Manifests never contain credentials or absolute machine-specific source paths.

### 4.2 Publication

1. Acquire the single-writer publication lease.
2. Calculate peak space: source download, transformed staging, final version, validation scratch, and safety reserve.
3. Write into same-volume `staging/`; close handles, hash files, verify schema/count/range/duplicates, and reconcile manifest totals.
4. Move the completed version directory atomically into `warehouse/versions/<id>` without overwriting an existing directory.
5. Write the canonical manifest once and verify its digest.
6. Write `current.json.tmp`, flush it, then atomically replace `current.json` on the same filesystem.
7. Release the lease and emit an audit event.

Readers open `current.json` once, pin its version ID and manifest digest for the entire operation, and never follow a pointer change mid-query.

### 4.3 Failure and rollback

- Failure before step 4 leaves only leased staging data and does not expose a version.
- Failure after step 4 but before pointer replacement leaves an unreferenced complete candidate; validation/recovery may publish it or quarantine it, never partially expose it.
- Pointer replacement failure keeps the previous current version.
- Rollback verifies the target manifest and partitions, writes a new pointer generation referencing the earlier version, and records actor/reason/time. It never edits either version.
- A version referenced by a backtest, paper reconciliation, audit record, or backup cannot be deleted by routine cleanup.

`current.json` contains `format_version`, `warehouse_version`, `manifest_sha256`, `pointer_generation`, `changed_at`, `actor`, and `reason`.

## 5. Backup boundary

| Artifact | Normal backup | Restore requirement |
|---|---:|---|
| Postgres logical/base backup, including audit records | Yes | Schema/version check plus record-count and sample reconciliation |
| Raw payloads and metadata | Yes | SHA-256 verification and provenance link check |
| Warehouse manifests, published partitions, and current pointer history | Yes | All manifest/partition hashes and ranges reconcile |
| Data-root ownership marker | Yes | Project/root identity matches restore target procedure |
| Reviewed `config/`, migrations, and operational runbooks | Yes, secret-free | Match the restored application version |
| Redis data | No | Rebuild/resubscribe/requeue from authoritative state |
| Staging, cache, temporary files | No | Reconstruct or discard after lease validation |
| Logs | No by default | Retain separately only when required by an audit policy |
| User exports | No by default | Promote explicitly if irreplaceable |
| Credentials, `.env`, tokens, private keys | Never in normal backup | Separate approved secrets-recovery procedure |

A successful copy is only a backup candidate. It becomes a validated backup after an isolated restore verifies digests, database reconciliation, application compatibility, and a recorded restore report.

## 6. Capacity alarms and write admission

For a filesystem with total capacity `C`, calculate free-space reserves:

- warning reserve: `max(20 GiB, 15% of C)`;
- critical reserve: `max(10 GiB, 8% of C)`;
- hard write-stop reserve: `max(5 GiB, 5% of C)`.

These formulas remain strictly ordered for ordinary volumes: warning > critical > stop. F13.5 may raise them after measured growth; lowering them requires review.

| State | Trigger | Required behavior |
|---|---|---|
| Healthy | Free space above warning reserve | Admit writes after projected-peak check |
| Warning | Free space at/below warning reserve | Alert once with trend and largest owned categories; continue admitted work |
| Critical | Free space at/below critical reserve | Pause new bulk backfills, warehouse rebuilds, and backup exports; reads continue |
| Write stop | Free space at/below stop reserve, or projected peak crosses it | Reject the write before download/transform; preserve existing data; emit blocking health state |

Write admission uses projected **peak** consumption rather than final output size. Unknown size uses a conservative endpoint-specific ceiling and expansion factor. Monitoring covers the primary data volume, Windows/Docker database volume, temporary-write volume, and backup destination independently.

Capacity handling never automatically deletes raw ingests, published versions, Postgres data, audit history, or backups. Cleanup is an explicit reviewed operation using reference counts, active leases, backup evidence, and a dry-run list of exact targets.

## 7. Retention classes

- Raw ingests, published manifests/versions, audit records, and version references: retain indefinitely until a later accepted retention ADR supplies safe deletion proofs.
- Quarantine: retain until the failure is reviewed and disposition is recorded.
- Staging/tmp/cache: reconstructible, but cleanup automation is deferred until leases and exact-target safety checks exist.
- Backups: retention is defined and restore-tested in F13.4.

No M0.3 action creates, moves, or deletes runtime data.
