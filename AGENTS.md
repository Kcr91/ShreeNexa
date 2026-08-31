# ShreeNexa Repository Instructions

## Project state and source of truth

ShreeNexa Terminal is a greenfield Indian-market research, paper-trading, and eventually approval-gated live-trading terminal. It is not implemented yet; follow the feature sequence instead of scaffolding ahead.

Read before editing:

1. `PROJECT_UPDATE.md` for current feature/branch status.
2. `SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md` for feature scope, dependency order, and proof.
3. `SHREENEXA_TECHNICAL_SPEC.md` for product behavior and invariants.
4. `docs/architecture/README.md` and only the directly relevant linked decisions.
5. `docs/qa/README.md` and the current feature acceptance contract.
6. `build/manifest.yaml` after M0.5 makes it available.

If these sources disagree, stop and report the conflict. The approved specification and build plan may not be silently rewritten during implementation.

## Hard boundaries

- `F:\Algotrading` is a separate legacy project. Do not read, write, import, execute, copy from, restructure, or depend on it. Mentions are permitted only to enforce this boundary.
- Work only inside `F:\ShreeNexa` and explicitly approved ShreeNexa-owned runtime roots. Validate resolved paths before writes or destructive actions.
- Root `data/` is local runtime state and is Git-ignored. Raw ingests and published warehouse versions are immutable; never use recursive cleanup against the data root.
- Never commit or expose credentials, tokens, cookies, private keys, `.env` files, Dhan client IDs, or signed URLs. Redact secrets from logs, fixtures, exceptions, reports, and frontend payloads.
- Product runtime AI is separate from the Codex development session and remains disabled until a separately approved provider decision.
- No real order placement, live-broker call, or live activation is authorized before the explicit Epic 12 and activation gates.
- Preserve user changes and unrelated work. Do not use destructive Git commands to make the tree clean.

## Feature workflow

1. Run preflight: `git status --short --branch`, `git log -1 --oneline`, and `python --version`.
2. Start from clean `main` and create exactly one `feature/<feature-id>-<slug>` branch. Never develop directly on `main`.
3. Read the feature contract and dependencies. Write/update acceptance criteria before implementation.
4. Implement only the smallest complete named feature. Do not begin dependent features early.
5. Run narrow checks, then every applicable gate below. Do not report unavailable commands as passing.
6. Review the complete branch diff for scope, correctness, secrets, path safety, determinism, look-ahead, migration impact, and protected paths.
7. Commit the feature, review it independently against `main`, fix confirmed findings on the same branch, and rerun gates.
8. Merge only after review is clean and the user has authorized merging. Prefer `git merge --ff-only` for this linear feature sequence.
9. Update `PROJECT_UPDATE.md` after each major task and feature review. Use `build/state.json` only through the validated helper introduced in M0.5.

Stop at a feature boundary when required evidence is missing or a decision changes architecture, safety, cost, external state, or data retention.

## Canonical environment and commands

- Windows working tree: `F:\ShreeNexa` (do not run this checkout through WSL paths).
- Python target: CPython 3.14.
- Node target: Node.js 24.
- Use `npm.cmd` in PowerShell because `npm.ps1` is blocked on the audited machine.

Checks available now:

```powershell
git status --short --branch
git diff --check
```

For documentation/configuration changes, also parse the affected format, resolve local links, verify referenced paths, and scan the changed files for secret-shaped values.

These commands become mandatory after F0.1 creates their configuration and lockfiles:

```powershell
python -m ruff check .
python -m mypy backend --strict
python -m pytest
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run build
```

Run UI features in a real application with Playwright and inspect changed screens. Validate numerical work against an independent implementation or hand fixture. Reconcile migrations/data changes using counts, hashes, ranges, gaps, duplicates, and samples before/after.

## Architecture invariants

- Four independent runtime roles: `api`, `engine`, `feedd`, and `worker`. Restarting `api` must not restart `engine`.
- Postgres is authoritative transactional state; Redis is reconstructible hot state/coordination; DuckDB over Parquet is the immutable historical warehouse.
- Code dependencies point inward to contracts/domain. Process entry points do not import one another; browsers access storage only through `api`.
- `worker` is the sole raw-ingest/warehouse publisher; readers pin a validated warehouse version and manifest digest.
- Every backtest records exact StrategyIR, data/manifest version, seed, configuration version, and code commit.
- No look-ahead, deterministic replay, vector/incremental parity, point-in-time universe selection, and honest provenance are release-blocking invariants.

## Protected paths

These paths are excluded from unattended or automated edits:

```text
backend/app/engine/risk.py
backend/app/engine/broker.py
backend/app/dhan/orders.py
backend/tests/parity/
```

A protected-path change requires a separately scoped supervised feature, explicit user authorization, targeted safety/parity tests, an independent review, and a final protected-diff check. Configuration, `AGENTS.md`, and `.codex/config.toml` are also review-sensitive and must not be changed as incidental cleanup.

## Code review rules

Flag as blocking:

- any legacy-project dependency or path escape;
- a secret or credential in source, history, logs, fixtures, or frontend output;
- same-bar/future-data leakage, current-membership survivorship bias, nondeterministic results, or missing vector/incremental parity where required;
- mutable raw/published historical data or an unpinned backtest input;
- a process owning state outside its ADR boundary;
- any broker path that bypasses risk filtering or implies live activation;
- a protected-path change without its required authorization/evidence;
- fabricated passing tests, swallowed failures, silent fallback, or scope creep.

Rank findings by severity and cite exact files/lines. Review first; edit only when the task authorizes fixes.

## Stop conditions

Stop and ask for direction when:

- unrelated/conflicting user changes prevent isolated work;
- a required architecture, API, cost, retention, migration, or safety decision is missing;
- current official evidence cannot verify a changing Dhan/Codex fact needed by the feature;
- a test would require real order placement or real credentials;
- a migration or cleanup could overwrite/discard data;
- a secret appears;
- required independent numeric/reference evidence is unavailable;
- a protected path is requested outside its supervised approval process.

## Completion report

End every feature with exactly these subjects:

1. Branch and commit SHA.
2. Files created/modified.
3. Behavior delivered.
4. Schema/migration/data impact.
5. Tests and exact pass/fail results.
6. Manual validation performed.
7. Known limitations, blockers, or open evidence.
8. Review result and whether the branch is safe to merge.
