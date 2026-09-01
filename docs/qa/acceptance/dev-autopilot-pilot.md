# Development Autopilot Pilot Setup Acceptance Contract

## Feature

Add the smallest maintainable local development controller that uses the
installed Codex CLI to implement, verify, independently review, and locally
fast-forward only F0.4–F0.9. This setup is development tooling, not Epic 11's
product feature-builder.

## Accepted boundaries

- Branch: `feature/dev-autopilot-pilot`, based on clean `main` at `eb46c23`.
- One implementation session at a time; every reviewer is a fresh ephemeral,
  read-only session after implementation has stopped.
- Supported `codex exec` interfaces are those verified on 2026-09-01 against
  the installed CLI and official non-interactive documentation.
- Normal local Codex authentication is inherited without reading, copying,
  printing, exporting, or committing authentication files.
- No dangerous sandbox/approval bypass, ignored rule/config layer, remote Git
  write, product deployment, live order, new paid credential, installation, or
  feature outside F0.4–F0.9.

## Required behavior

1. The policy contains the exact allowlist and manifest dependency order,
   finite command timeouts, at most three repair cycles, controller-defined
   gates, scope lists, control-plane paths, and existing protected paths.
2. Run, status, stop, and resume commands are documented. A cross-process
   single-instance lock blocks a second controller.
3. Atomic ignored runtime state records phases, attempts, base/candidate SHAs,
   evidence, and cancellation. Startup reconciles it with Git and never repeats
   a completed merge. Canonical tracked progress uses only
   `build/update_state.py`.
4. Worker output is untrusted text. The controller executes only policy-defined
   commands and rejects worker edits to control-plane/protected/out-of-scope
   paths, symlinks, submodules, gate definitions, permissions, allowlist, or
   completion state.
5. Every command record includes command identity, exit code, duration,
   candidate SHA, and parsed pass/fail/skip counts where applicable. Required
   service tests receive explicit isolated test settings; required skips fail.
6. Review JSON is strict and binds verdict/findings to the recorded base and
   exact candidate. Missing, malformed, timed-out, SHA-mismatched, unknown, or
   blocking review results fail closed.
7. Any candidate mutation invalidates prior gates/review. Integration requires
   a clean worktree, unchanged main/base and remotes, full evidence for the
   final SHA, then `git merge --ff-only` only.
8. Logs redact secret-shaped values without reproducing matches. Cancellation
   terminates the active process tree within a finite timeout while preserving
   branches, commits, logs, and reports.
9. After setup is independently reviewed and merged, its control-plane paths
   are pinned to the setup SHA and the pilot launches without another routine
   confirmation. It stops after F0.9 or at the first defined blocker.

## Recovery requirements (2026-09-01)

- Git implementation presence, verified test/review evidence, and full feature
  acceptance are separate facts. `merged_unverified`, `blocked`, and `done`
  (verified complete) are not interchangeable.
- Startup reconciles merged feature-branch tips, the validated tracked feature
  ledger, the durable runtime journal, and exact-SHA evidence before selecting
  work. Any disagreement returns `recovery-needed`; a missing journal cannot
  cause a merged feature to replay.
- Controller policy version, policy digest, base SHA, candidate SHA, timestamps,
  command results, test counts, report hashes, and a fresh independent reviewer
  session are promotion inputs. Missing, stale, malformed, wrong-SHA, skipped,
  or zero-test evidence blocks.
- Feature-specific `evidence_checks` execute in the controller path. Worker prose
  and self-review never establish completion, and tracked status is not `done`
  until promotion evidence has passed.
- Synthetic Dhan-shaped fixtures fail F0.5's recorded-cassette requirement.
  Repairing controller enforcement does not make the pilot or F0.5 ready.

## Synthetic proof

Temporary repositories and a fake Codex adapter prove: passing merge/advance;
gate failure and required skips block; blocking/missing/malformed/unknown review
blocks; protected or gate-weakening edits block; candidate mutation and moved
main block; pre/post-merge resume is idempotent; lock exclusion; non-allowlisted
rejection; secret redaction; untrusted commands are not executed; and stop
preserves recoverable work.

## Setup verification

- Narrow controller tests, then every canonical backend/frontend/build gate.
- Markdown/config parsing, link/path checks, diff scope/protected/control-plane
  audit, secret-shaped scan, and `git diff --check`.
- One harmless real `codex exec` capability smoke test with read-only sandbox,
  ephemeral session, structured output, no secrets, and no external writes.
- A fresh independent review of the exact setup candidate against its base.
  Any fix invalidates evidence and requires all applicable checks and review
  again. The unvalidated controller cannot approve itself.

## Non-goals

No product feature implementation in the setup commit, no credential value
entry or token generation/renewal, no service/database mutation, no remote
operation, no scheduler/startup task, no laptop power change, and no expansion
beyond F0.9.
