# ShreeNexa Project Update

This file is the human-readable project progress log. It is updated after each major task. The machine-readable `build/state.json` remains deferred until M0.5 introduces its validated update helper.

## Current snapshot

| Item | Status |
|---|---|
| Current release wave | W0 — Greenfield baseline |
| Current feature | M0.4 — Review passed; merge authorized |
| Current branch | `feature/M0.4-repository-guidance` |
| Product runtime | Not implemented |
| Live trading | Not implemented and not authorized |
| Legacy project boundary | `F:\Algotrading` remains outside this repository |

## Feature status

| Feature | Status | Evidence / next action |
|---|---|---|
| M0.1 | Done | Fast-forwarded into `main` at `951ed5b` after the approved re-review. |
| M0.2 | Done | Reviewed and fast-forwarded into `main` at `74d5656`. |
| M0.3 | Done | Review finding fixed; full data-root and build-ignore regression probes pass. |
| M0.4 | Done | Repository guidance and Codex/QA configuration passed independent review with no findings. |
| M0.5–M0.6 | Pending | Blocked on preceding M0 dependencies. |
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

### 2026-08-31 — M0.1 merged and M0.2 review passed

- Fast-forwarded M0.1 into `main` at `951ed5b` after explicit user authorization.
- Reviewed M0.2 as an isolated nine-file diff against the updated `main`.
- Rechecked scope, specification stability, the declared dependency DAG, diff hygiene, and secret-shaped values.
- Found no architecture or correctness defects. Corrected this status file so it no longer reported M0.1 as unmerged.
- Authorized M0.2 for fast-forward merge; no product code or schema was changed.

### 2026-08-31 — M0.3 started

- Fast-forwarded the reviewed M0.2 branch into `main` at `74d5656`.
- Created `feature/M0.3-data-lifecycle` from the clean updated `main`.
- Recorded the M0.3 acceptance contract before writing the data-lifecycle decision.
- Kept runtime storage, dependencies, and data creation out of scope.

### 2026-08-31 — M0.3 lifecycle baseline completed

- Selected ignored `<repository>\data` as the default and defined strict validation for an optional dedicated override.
- Defined byte-for-byte immutable raw ingests with SHA-256 provenance and secret redaction.
- Defined immutable warehouse versions, canonical manifests, atomic publication, pinned readers, and pointer-only rollback.
- Classified backup inclusions/exclusions and required restore validation before a copy counts as healthy.
- Added ordered warning, critical, and hard write-stop reserves based on both GiB and filesystem percentage.
- Verified the threshold formulas remain ordered across representative filesystem capacities.

### 2026-08-31 — M0.3 implementation verification completed

- Confirmed all local documentation links resolve and the staged diff passes `git diff --check`.
- Confirmed threshold ordering at 10, 50, 100, 200, 1,000, and 10,000 GiB capacities.
- Confirmed the build plan and technical specification are unchanged.
- Confirmed no runtime `data/` directory, dependency, database, or secret-shaped value was introduced.
- M0.3 is ready for independent branch review; M0.4 has not been started.

### 2026-08-31 — M0.3 review finding and fix

- Review probes showed `data/warehouse`, `data/staging`, `data/services`, and `data/cache` were not covered by the existing partial data ignores.
- Replaced the partial rules with a root-only `/data/` ignore so every default runtime-data category stays out of Git.
- Tightened override validation: the canonical default is the only permitted data root inside the repository source tree.
- Clarified that pointer-change history is backed up through the Postgres audit record alongside the current pointer.
- Added representative ignore probes to the review rerun before merge.

### 2026-08-31 — M0.3 review rerun passed

- Confirmed raw, warehouse, current-pointer, staging, Postgres-service, and cache examples under root `data/` are ignored.
- Confirmed similarly named nested `data/` and `dataset/` paths outside the root are not over-ignored.
- Re-ran the M0.1 build-rule regression: root `build/manifest.yaml` remains trackable and nested generated `build/` output remains ignored.
- Re-ran link, threshold-order, scope, specification-stability, secret-pattern, and diff-hygiene checks.
- M0.3 is approved for fast-forward merge; no runtime data or schema exists yet.

### 2026-08-31 — M0.4 started

- Fast-forwarded reviewed M0.3 into `main` at `eaeab65`.
- Created `feature/M0.4-repository-guidance` from the clean updated `main`.
- Checked current official OpenAI documentation for `AGENTS.md` discovery and trusted project configuration.
- Recorded the M0.4 acceptance contract before adding repository instructions or Codex settings.

### 2026-08-31 — M0.4 guidance baseline completed

- Added concise root `AGENTS.md` covering source-of-truth documents, hard boundaries, workflow, commands, invariants, protected paths, review rules, stop conditions, and completion reporting.
- Added trusted-project `.codex/config.toml` with interactive approvals, workspace-write sandboxing, disabled sandbox network, and no external writable roots or model/provider integration.
- Added QA indexes and detailed feature-workflow, gate, protected-path, and completion-report documents.
- Parsed the TOML with Python 3.14 and confirmed `AGENTS.md` is 7,367 bytes, below the 32 KiB instruction limit.
- Confirmed Codex CLI `0.148.0-alpha.9` is on PATH; the IDE session remains the supervised workflow.

### 2026-08-31 — M0.4 implementation verification completed

- Parsed the exact `.codex/config.toml` structure and allowlisted its four top-level settings.
- Confirmed every protected path appears in both root guidance and the detailed protected-path policy.
- Confirmed all eight completion-report subjects are present exactly once.
- Resolved all local Markdown links and found no secret-shaped content or product scaffolding.
- Confirmed the protected-path diff is empty and the staged change passes `git diff --check`.
- M0.4 is ready for independent branch review; M0.5 has not been started.

### 2026-08-31 — M0.4 independent review passed

- Reviewed the complete feature against `main` and confirmed the eleven intended guidance/configuration paths only.
- Re-parsed the TOML and confirmed it adds no external writable root, provider, model, MCP server, credential, or broad sandbox mode.
- Confirmed every required root-guidance section is present exactly once.
- Confirmed specification, protected-path, product-code, secret-pattern, and diff-hygiene checks are clean.
- M0.4 is approved for fast-forward merge with no schema, runtime, or data impact.

## Known prerequisites and blockers

- Docker Desktop is selected but not installed; its installation remains a separately approved prerequisite before F0.2. WSL has no registered distribution and remains only the documented fallback.
