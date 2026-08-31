# ShreeNexa Project Update

This file is the human-readable project progress log. It is updated after each major task. The machine-readable `build/state.json` remains deferred until M0.5 introduces its validated update helper.

## Current snapshot

| Item | Status |
|---|---|
| Current release wave | W0 — Greenfield baseline |
| Current feature | M0.2 — Ready for review |
| Current branch | `feature/M0.2-architecture-adrs` |
| Product runtime | Not implemented |
| Live trading | Not implemented and not authorized |
| Legacy project boundary | `F:\Algotrading` remains outside this repository |

## Feature status

| Feature | Status | Evidence / next action |
|---|---|---|
| M0.1 | Approved, pending user-controlled merge | Re-review declared `951ed5b` safe to merge; `main` has not been changed. |
| M0.2 | Review | Four ADRs, the acceptance contract, and dependency proof are complete; all documentation checks pass. |
| M0.3–M0.6 | Pending | Blocked on preceding M0 dependencies. |
| F0.1–F13.5 | Pending | Product feature work begins only after M0.6. |

## Major-task log

### 2026-08-31 — M0.1 review accepted

- Confirmed the complete bootstrap branch is safe to merge.
- Confirmed the focused fix changed only `.gitignore`.
- Confirmed the approved specification hashes were unchanged and the worktree was clean.
- No merge was performed; repository policy leaves merging under user control.

### 2026-08-31 — M0.2 started

- Reviewed the complete approved build plan and technical specification.
- Selected M0.2 as the next dependency-ready feature.
- Created `feature/M0.2-architecture-adrs` from the reviewed M0.1 tip because M0.1 is not yet merged.
- Recorded the M0.2 acceptance contract before architecture implementation.

### 2026-08-31 — M0.2 architecture baseline completed

- Accepted the greenfield repository boundary and prohibited legacy-project coupling.
- Fixed the independent responsibilities of `api`, `engine`, `feedd`, and `worker`.
- Assigned authoritative and write ownership across Postgres, Redis, and DuckDB/Parquet.
- Fixed backend/frontend/build package names and the native-Windows development topology.
- Added an explicit bottom-up dependency order proving the declared module graph is acyclic.
- Deferred data-root details to M0.3 and dependency/tool scaffolding to their owning features.

### 2026-08-31 — M0.2 verification completed

- Confirmed all local Markdown links resolve.
- Parsed the declared dependency graph: 12 nodes, 31 edges, all 12 nodes visited, no cycle.
- Confirmed the approved build-plan and technical-specification files are unchanged.
- Confirmed `git diff --check` passes and no secret-shaped value is present in the M0.2 files.
- M0.2 is ready for a separate review after M0.1 is merged; M0.3 has not been started.

## Known prerequisites and blockers

- Docker Desktop is not installed and WSL has no registered distribution. One local-services path must be selected before F0.2.
- M0.2 must be reviewed after M0.1 is merged so its diff is evaluated independently against `main`.
