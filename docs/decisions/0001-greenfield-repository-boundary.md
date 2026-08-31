# ADR-0001: Greenfield Repository Boundary

- **Status:** Accepted
- **Date:** 2026-08-31
- **Feature:** M0.2

## Context

ShreeNexa is a new terminal with its own architecture, data lifecycle, dependencies, and safety controls. Reusing the older trading project's code or data paths would make provenance unclear, couple migrations to an unrelated system, and undermine the greenfield acceptance criteria.

## Decision

1. `F:\ShreeNexa` is the only repository root for ShreeNexa source, configuration, documentation, and repository-managed fixtures.
2. `F:\Algotrading` is outside the repository boundary. ShreeNexa must not import from it, execute it, write to it, copy its architecture, or use it as an implicit data source.
3. Mentions of the legacy path are allowed only in policy and architecture documentation that enforces this prohibition.
4. Runtime data must live under a ShreeNexa-owned path. M0.3 will select the exact data-root configuration, immutable-download rules, versioning, backup boundary, and disk alarms.
5. A future historical import, if ever requested, must be a separately approved, read-only adapter with explicit provenance. It is not an architectural dependency and is not part of the current plan.
6. Secrets, credentials, downloaded market data, generated output, and runtime state are never committed.

## Boundary test

A clean checkout must be understandable, buildable, and testable without the legacy project existing on the machine. Removing access to the legacy path must not change any ShreeNexa behavior.

## Consequences

- Every dependency and data source must be declared within ShreeNexa.
- Historical fixtures must be synthetic, independently sourced, or captured specifically for ShreeNexa with provenance.
- No migration path from the legacy project is implied.
- M0.3 must finish the new data-root and backup decisions before storage implementation begins.
