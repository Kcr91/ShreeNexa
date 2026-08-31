# Feature Workflow

## 1. Preflight

- Read root `AGENTS.md`, `PROJECT_UPDATE.md`, the feature contract, relevant ADRs, and—after M0.5—the manifest entry.
- Record branch, HEAD, Python version, and worktree status.
- Stop for unrelated or conflicting changes.

## 2. Contract first

Before implementation, record acceptance behavior, fixtures/reference evidence, migration and rollback impact, UI behavior when applicable, and explicit non-goals.

## 3. Smallest complete implementation

Implement only the named feature. Shared abstractions are permitted only when required now and covered by the current acceptance proof. Do not scaffold downstream modules merely because the architecture names them.

## 4. Verification

Run narrow checks first, followed by every activated gate in [gates.md](gates.md). Preserve exact commands, exit codes, and test counts. A missing executable/configuration is unavailable evidence, not a pass.

Feature-specific evidence:

- Numeric: independent library and/or hand-computed fixture.
- UI: real app, Playwright, affected viewport/accessibility/visual inspection.
- Migration/data: before/after counts, hashes, ranges, gaps, duplicates, samples, rollback proof.
- External API: dated official documentation or redacted offline cassette; never burn credentials in routine tests.

## 5. Self-review and commit

Review the complete feature diff for scope, regression, security, secrets, path containment, process/storage ownership, determinism, look-ahead, protected paths, and truthful status. Commit only intended files after checks pass.

## 6. Independent review and fix loop

Review the branch against current `main`. Rank findings by severity and cite exact evidence. Fix confirmed findings on the same feature branch, add a regression check/test, rerun all affected gates, and repeat review until clean.

## 7. Merge and boundary

Merge only after authorization and a clean review, using fast-forward for the linear build sequence. Confirm `main` is clean, update project status, and only then open the next dependency-ready feature.
