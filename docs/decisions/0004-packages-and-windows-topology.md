# ADR-0004: Package Names, Dependency Direction, and Windows Topology

- **Status:** Accepted
- **Date:** 2026-08-31
- **Feature:** M0.2

## Context

The repository needs stable names and dependency direction before scaffolding. The target computer already has Python 3.14 and Node 24, while Docker Desktop is absent and WSL has no distribution. Mixing Windows and WSL paths for one checkout creates file-watching, permissions, and tool-resolution failures.

## Decision

### Repository package names

| Area | Directory | Published/workspace name | Import or entry namespace |
|---|---|---|---|
| Backend | `backend/` | `shreenexa-backend` | Python package `app` |
| Frontend | `frontend/` | `@shreenexa/frontend` | TypeScript source under `frontend/src` |
| Build metadata/orchestration | `build/` | Repository-local, not published | Python module/CLI namespace `build` when introduced in M0.5 |
| Infrastructure | `infra/` | Not a package | Compose, Caddy, and deployment assets only |
| Configuration | `config/` | Not a package | Reviewed versioned YAML/TOML configuration |

The four runtime command names are `api`, `engine`, `feedd`, and `worker`. Concrete console-script wiring is implemented in F0.3 without renaming these roles.

### Backend capability namespaces

The approved backend namespaces are `app.api`, `app.ws`, `app.cli`, `app.dhan`, `app.marketdata`, `app.analytics`, `app.ir`, `app.engine`, `app.backtest`, `app.screener`, `app.compose`, `app.builders`, `app.investing`, and `app.ai`. Shared domain types and cross-process messages belong in dependency-light `app.domain` and `app.contracts` namespaces created only when a feature needs them.

Dependencies point inward toward contracts/domain and never toward a process entry point. The binding graph and topological proof are in [`docs/architecture/module-dependency-map.md`](../architecture/module-dependency-map.md).

### Windows development topology

1. The working tree and developer tools run natively on Windows from `F:\ShreeNexa`.
2. Python target: CPython 3.14; the project environment will be `F:\ShreeNexa\.venv` in F0.1.
3. Node target: Node.js 24 with the package manager and lockfile selected in F0.1.
4. Frontend, backend processes, tests, Git, and editors all use the Windows path. The checkout is not opened or executed through `/mnt/f`.
5. Docker Desktop is the selected local-services path for Postgres and Redis, with explicit resource limits. Its installation is a separately approved prerequisite before F0.2.
6. WSL2 remains a documented fallback only. It must not run a second Postgres/Redis stack for the same checkout, and switching to it requires a superseding decision or an implementation record in F0.2.
7. DuckDB runs embedded in the Python process that performs a query; Parquet files live in the ShreeNexa data root defined by M0.3.
8. Ports, credentials, container resources, and supervisor tooling remain configurable and are finalized by their owning features.

## Rejected alternatives

- A Python/Node split across native Windows and WSL for the same checkout: rejected due to path, watcher, and permission inconsistency.
- A monorepo package that lets frontend or process entry points import each other: rejected because it hides service boundaries and creates cycles.

## Consequences

- F0.1 must create these workspace/package names and verify Python 3.14 binary-wheel compatibility.
- F0.2 is blocked until Docker Desktop is installed or this decision is explicitly superseded with the WSL fallback.
- Import-boundary tests should be added when the corresponding modules exist.
