# ShreeNexa Project Update

This file is the human-readable project progress log. It is updated after each major task. The machine-readable `build/state.json` is maintained through the validated helper introduced in M0.5 (`build/update_state.py`).

## Current snapshot

| Item | Status |
|---|---|
| Current release wave | W1 — Stable backend foundation (in progress) |
| Current feature | F0.2 — Review passed; merged |
| Current branch | `main` |
| Product runtime | Not implemented |
| Live trading | Not implemented and not authorized |
| Legacy project boundary | `F:\Algotrading` remains outside this repository |

## Feature status

| Feature | Status | Evidence / next action |
|---|---|---|
| M0.1 | Done | Fast-forwarded into `main` at `951ed5b` after the approved re-review. |
| M0.2 | Done | Reviewed and fast-forwarded into `main` at `74d5656`. |
| M0.3 | Done | Review finding fixed; full data-root and build-ignore regression probes pass. |
| M0.4 | Done | Repository guidance and Codex/QA configuration passed independent review; fast-forwarded into `main` at `0c86d5e` after user merge authorization. |
| M0.5 | Done | Manifest, validator, and state helper pass all tests; F2.6 dependency fix applied (C11). Fast-forwarded into `main` at `22334e8` after user merge authorization. |
| M0.6 | Done | First green baseline proven via real fresh-clone bootstrap; fixtures frozen by hash. Fast-forwarded into `main` at `fef0814` after user merge authorization. **W0 (M0.1–M0.6) complete.** |
| F0.1 | Done | uv-managed Python env, frontend Node workspace, pre-commit, and CI skeleton all pass; fresh-clone bootstrap re-verified. Fast-forwarded into `main` at `996a55b` after user merge authorization. |
| F0.2 | Done | Postgres + Valkey (Redis-compatible) via Docker Compose, resource-limited and health-checked; Alembic scaffold proven; 33/33 tests pass with the stack up, 29 passed + 4 correctly skipped with it down. Fast-forwarded into `main`. |
| F0.3–F13.5 | Pending | F0.3 (api/engine/feedd/worker process skeletons) is next. |

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

### 2026-08-31 — F2.6 dependency finding resolved

- User decision: add a correction row (`C11`) to the build plan's corrections table recording the F2.6/F2.4 wave-ordering conflict and its resolution, but leave the F2.6 ledger row itself in its original wording — only the corrections table is authoritative for this override.
- Updated `build/manifest.yaml`: F2.6 now depends on `[F2.2, F2.3, F2.5]` (F2.4 dropped), with `notes` explaining the correction.
- Added a regression test proving no wave-3 feature (F2.1–F2.3, F2.5–F2.7, F3.1–F3.4, F3.7, F3.10, F3.12) transitively depends on a deferred UI feature (F2.4, F3.11, F3.13, F3.14).
- Re-ran the full suite: `python -m pytest build/tests -q` → 19 passed; `python build/validate_manifest.py` → 108 items, no cycles; `python -m ruff check build/` clean; `git diff --check` clean; no secret-shaped content.

### 2026-08-31 — M0.4 and M0.5 merged

- User authorized both merges. Fast-forwarded `feature/M0.4-repository-guidance` into `main` at `0c86d5e`, then `feature/M0.5-feature-manifest` into `main` at `22334e8`.
- Re-ran the full verification suite directly on `main`: `python -m pytest build/tests -q` → 19 passed; `python build/validate_manifest.py` → 108 items (6 M0, 102 product), no cycles; `python -m ruff check build/` clean.
- `main` is clean; no stray artifacts. M0.6 is the next dependency-ready feature.

### 2026-08-31 — M0.6 started

- Created `feature/M0.6-green-baseline` from the merged `main` at `22334e8`.
- M0.6 scope per the build plan: establish the first green baseline and freeze small synthetic/reference fixtures by hash.
- Scoped with the user: since F0.1 hasn't run, "baseline" means the current documentation/tooling repo bootstraps cleanly from a fresh clone with no manual setup, and the frozen fixtures are small hand-computed placeholders for future numeric-parity features (F1.6, F2.1) to pin against — not an indicator implementation.

### 2026-08-31 — M0.6 baseline and fixtures completed

- Discovered a real risk before freezing anything by hash: local `core.autocrlf=true` with no `.gitattributes` meant a fixture's on-disk bytes (and therefore its SHA-256) could differ between this Windows checkout and a future Linux clone. Added `.gitattributes` forcing LF for `build/fixtures/*` to make the hash freeze meaningful.
- Added `build/fixtures/ohlc_synthetic_10bar.csv` (hand-authored 10-bar OHLCV series) and `build/fixtures/sma_ema_reference.json` (hand-computed SMA(3)/EMA(3), not derived from any indicator library), with an explicit `null` warm-up policy for the first two bars.
- Added `build/fixtures/manifest.json` (SHA-256 per fixture) and `build/validate_fixtures.py`, which detects a hash mismatch, an untracked extra fixture, or a missing recorded fixture.
- Added `build/tests/test_fixtures.py` (8 cases): real fixtures pass; a one-byte tamper is caught; an untracked extra file is caught; a missing file is caught; SMA(3)/EMA(3) reference values are independently re-derived from the CSV and shown to match; warm-up bars are `null`, not a partial average.
- `python -m ruff check build/` is clean.

### 2026-08-31 — M0.6 clean-clone bootstrap verified

- Performed a real `git clone` of the repository (branch `feature/M0.6-green-baseline`) into an isolated directory, with no setup beyond the clone itself.
- In that fresh clone: `python build/validate_manifest.py` → 108 items, no cycles; `python build/validate_fixtures.py` → 2 fixtures verified; `python -m pytest build/tests -q` → 27 passed.
- Confirmed the `.gitattributes` LF pin actually matters: the cloned `ohlc_synthetic_10bar.csv` checked out as pure LF (hash matches the manifest exactly), while an unpinned file (`build/manifest.yaml`) checked out with local-autocrlf CRLF in the same clone — proving the pin is load-bearing, not redundant.
- Deleted the temporary clone after verification.

### 2026-08-31 — M0.6 independent review passed

- Reviewed the complete branch against `main`: only `.gitattributes`, `build/fixtures/`, `build/validate_fixtures.py`, `build/tests/test_fixtures.py`, `docs/qa/`, and status files changed — no product code or protected path.
- Found and fixed a real gap: `docs/qa/README.md` never linked the M0.5 or M0.6 acceptance contracts, defeating its own "fresh session finds it without repo-wide exploration" bar.
- Re-ran the full suite: `pytest build/tests -q` → 27 passed; `validate_manifest.py` → 108 items, no cycles; `validate_fixtures.py` → 2 verified; `ruff check build/` clean; `git diff --check` clean; no secret-shaped content.
- M0.6 is approved for fast-forward merge; no schema, runtime, or data impact.

### 2026-08-31 — M0.6 merged; F0.1 started

- User authorized the merge. Fast-forwarded `feature/M0.6-green-baseline` into `main` at `fef0814`. Re-verified directly on `main`: 27 passed, manifest/fixtures clean, ruff clean. **W0 (M0.1–M0.6) is complete.**
- User chose `uv` as the Python dependency/lockfile manager for F0.1 (the choice `docs/decisions/0004-packages-and-windows-topology.md` explicitly deferred to this feature).
- Created `feature/F0.1-repo-standardization` from the merged `main`. Recorded the F0.1 acceptance contract, including the uv/npm/GitHub-Actions scope decisions, before implementation.
- Installed `uv` via `pip install uv` (official PyPI wheel) rather than the shell/PowerShell installer script.

### 2026-08-31 — F0.1 task 1: Python tooling standardized

- Added root `pyproject.toml` (project `shreenexa-backend`, `backend/app` as the wheel target), `uv.lock`, and ruff/mypy/pytest configuration; pinned `.python-version` to `3.14`.
- `uv sync` resolved and installed 23 packages, every one a `cp314`/pure-Python wheel — no source build required (the F0.1 binary-wheel proof).
- Added a minimal `backend/app` package (version stub only) and a smoke test proving the test layer works end to end.
- Explicit ruff rule selection (`E`, `F`, `I`, `UP`, `B`, `RUF`) surfaced real `E501`/`RUF005` findings in the M0.5/M0.6 `build/*.py` scripts that ruff's bare defaults hadn't caught (`E501` isn't in ruff's default rule set); fixed all of them, re-verified 28 tests pass.

### 2026-08-31 — F0.1 task 2: frontend workspace skeleton

- Added `@shreenexa/frontend`: Vite + React + TypeScript + Vitest, with `typecheck`/`test`/`build` npm scripts and one placeholder component/test. Tooling only — F4.1 builds the real shell.
- `npm install` resolved 185 packages; typecheck, test, and build all pass. `npm audit` reports pre-existing transitive dev-dependency advisories (3 moderate, 1 high, 1 critical) in the toolchain, not investigated in this task since no production dependency is affected (the frontend has no runtime deps beyond `react`/`react-dom`) — flagged for follow-up before any frontend feature depends on the affected packages.

### 2026-08-31 — F0.1 task 3: pre-commit config, with a caught hazard

- Wired hygiene hooks (trailing-whitespace, end-of-file, yaml/json/toml, large-file, merge-conflict), ruff lint+format, and local hooks running `build/validate_manifest.py`/`build/validate_fixtures.py`.
- **Found and fixed a real hazard before committing it**: an unscoped `pre-commit run --all-files` let `ruff-format` reformat a Python code fence embedded inside the approved `SHREENEXA_TECHNICAL_SPEC.md`, and a `mixed-line-ending` hook rewrote nearly every already-tracked file's line endings against local `core.autocrlf=true`. Both changes were reverted before any commit was made. Fixed by excluding the two approved documents at the top level of `.pre-commit-config.yaml` and scoping the ruff hooks to `types_or: [python, pyi]` explicitly; dropped the mixed-line-ending hook entirely rather than fight local autocrlf on every pre-existing file.
- Proved the hooks catch real problems, not just pass vacuously: a deliberate ruff violation and a deliberately corrupted `build/manifest.yaml` dependency were each caught by `pre-commit run --all-files`, then reverted.

### 2026-08-31 — F0.1 task 4: CI skeleton and completion

- Added `.github/workflows/ci.yml` (backend: `uv sync`, ruff, mypy strict, pytest, manifest/fixture validators; frontend: `npm ci`, typecheck, test, build). No remote exists yet, so this workflow is inert until one is added.
- Moved the "become mandatory after F0.1" commands in `AGENTS.md` into "checks available now" with `uv run` prefixes, and documented the pre-commit exclusion for the approved documents.
- Performed a real `git clone` of the F0.1 branch into an isolated directory and ran every gate there with no manual setup beyond the clone: `uv sync` (23/23 wheels, no source build), ruff, mypy strict, `uv run pytest` (28 passed), manifest/fixture validators, `npm ci`, typecheck, test, build — all green. Deleted the temporary clone after verification.

### 2026-08-31 — F0.1 independent review passed

- Reviewed the complete branch against `main`: `pyproject.toml`, `uv.lock`, `.python-version`, `backend/`, `frontend/`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `AGENTS.md`, `docs/qa/acceptance/F0.1.md` — no protected path, no database, no Dhan client, nothing beyond tooling.
- Re-ran the full backend and frontend gate set directly on the branch (not just in the temporary clone): all green.
- No product code, live-trading path, or credential was introduced. `git diff --check` clean; no secret-shaped content.
- F0.1 is approved for fast-forward merge; no schema or runtime-data impact.

### 2026-09-01 — F0.1 merged; Docker Desktop installed and F0.2 started

- User authorized the merge. Fast-forwarded `feature/F0.1-repo-standardization` into `main` at `996a55b`. Re-verified directly on `main`: ruff/mypy/pytest/manifest/fixtures all green.
- User instructed that going forward, each reviewed feature is merged automatically and work continues to the next feature, without a separate per-feature merge-authorization pause (still subject to every other stop condition in `AGENTS.md`).
- Docker Desktop was not installed, blocking F0.2. Installed it via `winget install Docker.DockerDesktop` (user's chosen path over manual install or skipping ahead). This needed three more manual steps no automation could complete: approving a UAC elevation prompt, restarting Windows to activate the newly-enabled WSL2 feature, and manually launching Docker Desktop after restart (it does not auto-start). Also found and worked around a `wsl --status` exit-50 failure — the WSL2 platform component itself was missing even after the Windows optional feature was enabled; `wsl --update` installed it. `docker info`/`docker compose version` confirmed working after these steps.
- Created `feature/F0.2-postgres-redis-compose` from the merged `main`. Recorded the F0.2 acceptance contract, including the Valkey-over-Redis licensing decision (upstream Redis 7.4+ is not OSI-licensed; this repo's spec claims free/open-source infrastructure) and the resource-limit/data-root/CI-scope decisions, before implementation.

### 2026-09-01 — F0.2 implementation and verification completed

- Added `infra/docker-compose.yml`: `postgres:17-alpine` (1 CPU/512 MiB) and `valkey/valkey:8-alpine` (0.5 CPU/256 MiB), both health-checked and bind-mounted into `data/services/{postgres,redis}` per the M0.3 data-lifecycle ADR.
- `docker compose up -d` brought both to `healthy`; `docker inspect` confirmed the exact configured limits are applied (536,870,912 / 268,435,456 bytes; 1.0 / 0.5 CPUs), not merely written and ignored.
- Added a minimal Alembic scaffold (`backend/alembic.ini`, `env.py` reading `DATABASE_URL` from the environment, one empty bootstrap revision) and `backend/tests/integration/test_docker_services.py` (Postgres connectivity, `alembic upgrade head` run twice to prove idempotency, Valkey connectivity, a SQLAlchemy-engine-level check). Added real runtime dependencies this feature needs (`psycopg`, `sqlalchemy`, `alembic`, `redis`) — all resolved to `cp314` wheels, no source builds.
- Found and fixed two bugs while verifying, before committing: a `REPO_ROOT` path miscalculation that pointed `alembic.ini` at the wrong location, and a ~150x slowdown (153s → 10s) caused by Windows resolving `localhost` to the IPv6 loopback first, which nothing listens on since Compose binds only `127.0.0.1` — switched the test defaults to `127.0.0.1` explicitly.
- Verified both directions: 33/33 pass with the stack up; 29 passed + 4 correctly **skipped** (not silently passed) with named reasons when the stack is down. `ruff`/`mypy --strict`/`pre-commit run --all-files` all clean.
- Noted as a follow-up, not solved here: CI (`windows-latest`) does not yet run these Linux containers, so the integration tests always skip there for now.

### 2026-09-01 — F0.2 independent review passed; merged

- Reviewed the complete branch against `main`: only `backend/alembic/`, `backend/tests/integration/`, `infra/docker-compose.yml`, `pyproject.toml`/`uv.lock`, and `docs/qa/acceptance/F0.2.md` changed — no protected path, no product schema, no secret (the local dev Postgres password is a clearly-labeled non-secret, reachable only inside the Docker network on `127.0.0.1`).
- Re-ran the full suite with the stack both up and down: all green.
- Fast-forwarded `feature/F0.2-postgres-redis-compose` into `main`. **F0.2 done.**

## Known prerequisites and blockers

- None currently blocking. Docker Desktop is installed and verified working.
