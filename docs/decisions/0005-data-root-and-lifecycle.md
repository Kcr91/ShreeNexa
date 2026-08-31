# ADR-0005: Data Root and Lifecycle

- **Status:** Accepted
- **Date:** 2026-08-31
- **Feature:** M0.3

## Context

Historical inputs must remain reproducible after corrections, backfills, and rollbacks. The data volume is large enough that partial downloads, interrupted partition writes, and exhausted disks are normal operating risks. A loose collection of mutable files would make prior backtests impossible to reconstruct and could accidentally cross the greenfield repository boundary.

## Decision

1. The default data root is `<repository>\data`, currently `F:\ShreeNexa\data`. It is ignored by Git and is created only by an owning implementation feature.
2. `SHREENEXA_DATA_ROOT` may override the default only with an absolute, dedicated, local ShreeNexa path that passes containment checks and carries a `.shreenexa-data-root.json` ownership marker.
3. A custom root may not be a drive root, the source-repository root, a temporary directory, the legacy project, an ancestor of any of those paths, or a path owned by another application.
4. Raw upstream response bytes are immutable and content-hashed. Retrying or correcting a request creates another ingest artifact with new provenance; it never overwrites the earlier payload.
5. Warehouse versions are immutable sets of partitions plus a content-hashed manifest. A small atomic pointer identifies the current version. Backtests store both version ID and manifest digest.
6. Only `worker` may commit raw artifacts or publish warehouse versions. Readers use published versions and never write through their read path.
7. Publication verifies all partition hashes/counts/ranges before atomically replacing the current pointer. Rollback changes only that pointer to a prior validated version.
8. The backup boundary includes irreplaceable or expensive-to-reconstruct state and excludes caches, Redis hot state, staging, logs, and secrets. A backup is not considered healthy until a restore validation succeeds.
9. Every filesystem participating in primary data, temporary publication, database/container persistence, or backups is monitored. Projected writes are refused before they breach the hard reserve; no automatic cleanup may delete raw or published data.

The binding directory, manifest, state-transition, backup, and threshold details are in [`docs/architecture/data-lifecycle.md`](../architecture/data-lifecycle.md).

## Consequences

- M0.3 creates policy only, not directories or data.
- F0.4 will validate path settings and redact them where necessary; F1.1 will implement atomic warehouse publication.
- Every backfill must preserve redacted request/provenance metadata and exact payload hashes.
- Corrections consume additional disk because old versions remain available for reproducibility and rollback.
- Retention or compaction that deletes durable artifacts requires a later reviewed policy with dependency/reference checks.
- Epic 13 must place encrypted backups outside the primary failure domain and prove restore integrity.
