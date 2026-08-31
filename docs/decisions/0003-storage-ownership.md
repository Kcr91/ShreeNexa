# ADR-0003: Storage Roles, Authority, and Write Ownership

- **Status:** Accepted
- **Date:** 2026-08-31
- **Feature:** M0.2

## Context

ShreeNexa combines transactional trading state, high-frequency hot state, and large immutable historical datasets. Treating one storage engine as suitable for all three would either make analytical scans expensive or make transactional recovery unsafe.

## Decision

| Store | Role | Authoritative for | Not authoritative for |
|---|---|---|---|
| Postgres | Transactional system of record | Strategies and versions, configuration, instruments and memberships, jobs/results metadata, deployments, orders, fills, positions, dashboards, audit records | Tick fan-out, transient subscription state, historical bar payloads |
| Redis | Reconstructible hot state and coordination | No irreplaceable domain record | Strategies, orders, fills, positions, audit history, immutable bars |
| DuckDB over Parquet | Immutable analytical warehouse | Versioned historical bars/options partitions and their manifests | Mutable orders, user configuration, live deployment state |

DuckDB is the query engine over Parquet; Parquet partitions and their manifests are the durable warehouse artifacts. Redis loss may reduce availability or require resubscription/requeueing, but must not erase authoritative trading history.

## Write ownership

| State | Write owner | Readers |
|---|---|---|
| Strategies, watchlists, dashboards, user configuration | `api` | `api`, `engine`, `worker` |
| Instruments and effective-dated index membership | `worker` | `api`, `engine`, `worker` |
| Backfill/backtest/screener results | `worker` | `api` |
| Deployment commands | `api` | `engine`, `api` |
| Deployment runtime state, orders, fills, positions, paper/live daily P&L | `engine` | `api`, `worker` |
| Quotes, OI, depth, subscriptions, feed health | `feedd` | `api`, `engine`, `worker` |
| Historical Parquet partitions and manifests | `worker` | `api`, `engine`, `worker` |
| Audit log | Append-only from all authenticated processes | `api` and offline review tools |

Where more than one process appends to a table, the schema and transaction boundary must preserve an explicit actor and idempotency key. Ownership means responsibility for the state transition, not exclusive database credentials by default; credential separation is finalized with deployment security.

## Data invariants

1. Frontend code and browsers never connect directly to Postgres, Redis, DuckDB, or the filesystem.
2. Historical rows are immutable. Corrections publish a replacement partition atomically with new provenance/version metadata.
3. Warehouse readers are read-only; only `worker` may publish or replace partitions.
4. Redis queues and caches are reconstructible from Postgres, the warehouse, or upstream feeds. Queue delivery must be idempotent.
5. Postgres commits are the recovery boundary for execution state.
6. Backup scope includes Postgres, Parquet manifests/partitions, and reviewed configuration; Redis is rebuilt rather than treated as the sole backup source.

## Consequences

- M0.3 must define concrete paths, retention, version identifiers, rollback, backup boundaries, and capacity alarms.
- F0.2 provides Postgres/Redis infrastructure; F1.1 provides the warehouse atomic-write contract.
- Cross-store workflows require durable identifiers and reconciliation rather than distributed transactions hidden in process memory.
