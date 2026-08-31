# ShreeNexa Project Update

This file is the human-readable project progress log. It is updated after each major task. The machine-readable `build/state.json` remains deferred until M0.5 introduces its validated update helper.

## Current snapshot

| Item | Status |
|---|---|
| Current release wave | W0 — Greenfield baseline |
| Current feature | M0.5 — Review passed; merge authorized (stacked behind unmerged M0.4) |
| Current branch | `feature/M0.5-feature-manifest` |
| Product runtime | Not implemented |
| Live trading | Not implemented and not authorized |
| Legacy project boundary | `F:\Algotrading` remains outside this repository |

## Feature status

| Feature | Status | Evidence / next action |
|---|---|---|
| M0.1 | Done | Fast-forwarded into `main` at `951ed5b` after the approved re-review. |
| M0.2 | Done | Reviewed and fast-forwarded into `main` at `74d5656`. |
| M0.3 | Done | Review finding fixed; full data-root and build-ignore regression probes pass. |
| M0.4 | Done | Repository guidance and Codex/QA configuration passed independent review with no findings. Independently re-verified in a later session; not yet merged into `main` — awaiting user merge authorization. |
| M0.5 | Done | Manifest, validator, and state helper pass all tests; one build-plan inconsistency found and flagged (see below). Not yet merged; stacked on unmerged M0.4. |
| M0.6 | Pending | Blocked on M0.4/M0.5 being merged into `main`. |
| F0.1–F13.5 | Pending | Product feature work begins only after M0.6. |

## Open item requiring a user decision

- **F2.6 dependency ambiguity.** The build plan's feature ledger lists F2.6's dependency as the literal range `F2.2-F2.5`, which includes F2.4 (indicator-builder UI, explicitly deferred to after F4.1-F4.3 by correction C4). Wave W3 places F2.6 *before* the frontend shell exists and explicitly excludes F2.4 from that wave. Taken literally, F2.6 would transitively require the frontend, contradicting its own wave placement. `build/manifest.yaml` transcribes the dependency literally (per AGENTS.md — the approved plan is not silently rewritten) and flags it in a `notes` field on the `F2.6` entry. This needs a decision before F2.6 is implemented: most likely the intended dependency was `F2.1-F2.3, F2.5` (the compiler/parser/schema prerequisites, without F2.4), but that correction should come from the user, not be assumed.

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

### 2026-08-31 — M0.4 independently re-verified; M0.5 started

- Found `main` still at the M0.3 tip (`eaeab65`) and `feature/M0.4-repository-guidance` already implemented and self-reviewed but not yet merged; treated this as a fresh, separate review rather than trusting the branch's own report.
- Re-parsed `.codex/config.toml` with Python 3.14 `tomllib`, confirmed workspace-write sandboxing with network access disabled and no provider/model/MCP/credential configuration.
- Re-ran link resolution, `git diff --check`, and a secret-shaped-content scan across the full M0.4 diff; found no issues.
- Removed a stray untracked working-tree copy of `.codex/` (byte-identical to the committed M0.4 version) that blocked branching; confirmed identity before deleting.
- Created `feature/M0.5-feature-manifest` from the reviewed M0.4 tip because M0.4 is not yet merged, matching the precedent set when M0.2 branched from an unmerged M0.1.
- Recorded the M0.5 acceptance contract before writing the manifest.

### 2026-08-31 — M0.5 manifest and state helper completed

- Transcribed all 6 M0 tasks and all 102 product features from the build plan's feature ledger into `build/manifest.yaml`, expanding every dependency range to explicit IDs without silently correcting the source text.
- Built `build/validate_manifest.py`: schema/required-field checks, dependency-existence checks, a topological sort proving the graph is acyclic, and generated (not handwritten) item counts.
- Added `build/tests/test_manifest.py` (11 cases) covering a valid pass, an unresolved dependency, an introduced cycle, a missing field, a duplicate ID, a malformed ID, and the generated 102/6/108 counts against the approved manifest.
- Introduced the `build/state.json` validated update helper promised in this file's header: `build/state_schema.py` (schema) and `build/update_state.py` (atomic, schema-validated writer), with 7 tests in `build/tests/test_state.py`.
- `python -m ruff check build/` is clean; `python -m mypy` is not yet installed (unavailable evidence, not reported as passing — mypy becomes mandatory at F0.1).
- Discovered and flagged the F2.6 dependency inconsistency described above rather than resolving it unilaterally.
- Initialized `build/state.json` through the new helper (`feature: M0.5, status: in_progress`) rather than hand-editing it.

### 2026-08-31 — M0.5 independent review passed

- Ran `python build/validate_manifest.py`: 108 items (6 M0, 102 product), topological sort succeeded.
- Ran `python -m pytest build/tests/ -q`: 18 passed.
- Spot-checked name/depends_on/proof/model transcription fidelity for a representative sample across every epic (F0, F1, F3, F4, F7, F8, F9, F10, F11, F12, F13) against the build plan source text; no mismatches found beyond the already-flagged F2.6 item.
- Confirmed the diff touches only `build/` and `docs/qa/acceptance/M0.5.md` — no product code, backend/frontend scaffolding, or protected path.
- Confirmed no secret-shaped content, `git diff --check` is clean, and no stray test artifacts (temp dirs, `__pycache__`) remain in the working tree.
- M0.5 is approved for fast-forward merge once M0.4 merges ahead of it; no schema, runtime, or data impact.

## Known prerequisites and blockers

- Docker Desktop is selected but not installed; its installation remains a separately approved prerequisite before F0.2. WSL has no registered distribution and remains only the documented fallback.
