# Architecture Index

The approved technical specification is the product source of truth. This directory provides concise implementation boundaries derived from it.

Repository workflow, gates, protected paths, and completion evidence are indexed in [`docs/qa/README.md`](../qa/README.md).

## M0.2 baseline

- [Module and dependency map](module-dependency-map.md)
- [M0.2 acceptance contract](../qa/acceptance/M0.2.md)

## M0.3 data lifecycle

- [Data lifecycle, versioning, backup, and capacity policy](data-lifecycle.md)
- [M0.3 acceptance contract](../qa/acceptance/M0.3.md)

## Accepted decisions

- [ADR-0001 — Greenfield repository boundary](../decisions/0001-greenfield-repository-boundary.md)
- [ADR-0002 — Four-process runtime](../decisions/0002-four-process-runtime.md)
- [ADR-0003 — Storage ownership](../decisions/0003-storage-ownership.md)
- [ADR-0004 — Packages and Windows topology](../decisions/0004-packages-and-windows-topology.md)
- [ADR-0005 — Data root and lifecycle](../decisions/0005-data-root-and-lifecycle.md)
- [ADR-0006 — Controlled local autopilot and Dhan local credentials](../decisions/0006-controlled-local-autopilot-and-dhan-credentials.md)

## Binding invariants

1. The repository is independent of the legacy project.
2. `api`, `engine`, `feedd`, and `worker` are independently supervised process roles.
3. Postgres is the transactional system of record; Redis is reconstructible hot state; DuckDB/Parquet is the immutable historical warehouse.
4. Code dependencies point inward and process entry points are composition roots.
5. Native Windows is the development environment for this checkout; Docker Desktop is the selected Postgres/Redis path once separately installed.
6. Live trading remains absent and unauthorized until its explicit late-stage gate.
7. Raw downloads and published warehouse versions are immutable; publication and rollback move only a validated pointer.
