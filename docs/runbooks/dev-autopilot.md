# Controlled Local Development Autopilot Runbook

## Boundary

This controller is local development tooling for exactly F0.4–F0.9. It uses
the normally configured Codex CLI login and never reads or exports Codex/Dhan
authentication files. It does not push, open pull requests, deploy, provision,
place orders, activate live trading, install software, change laptop power or
startup settings, or continue to F1.x.

Run every command from `F:\ShreeNexa` in native Windows PowerShell. The setup
commit must already be independently reviewed, fast-forwarded to clean `main`,
and pinned before `run` or `start` is used.

## Commands

Foreground run (best for direct observation):

```powershell
python -m uv run python build/dev_autopilot.py run
```

Detached run:

```powershell
python -m uv run python build/dev_autopilot.py start
```

Status:

```powershell
python -m uv run python build/dev_autopilot.py status
```

Safe stop request:

```powershell
python -m uv run python build/dev_autopilot.py stop
```

Reconcile Git/runtime history and resume:

```powershell
python -m uv run python build/dev_autopilot.py resume
```

`start` prints its process identifier and the status command. Do not start a
second process; the OS-held single-instance lock rejects it.

## Durable local evidence

Ignored operational state is under `.runtime/dev-autopilot/`:

- `state.json`: atomic phase, attempt, feature, base/candidate, and completion
  reconciliation journal;
- `controller.lock`: OS-held single-instance lock plus diagnostic PID metadata;
- `stop-requested.json`: durable cancellation request;
- `reports/<feature>/`: redacted worker/reviewer output, exact-SHA gate logs,
  JUnit reports, candidate manifests, and secret-scan categories;
- `worktrees/<feature>/`: preserved unfinished worktree when blocked/stopped.

This ignored journal is recovery/evidence state, not a competing project
progress database. The tracked `build/state.json` remains status-only and is
written only through `build/update_state.py` by the controller.

## Recovery rules

At startup/resume the controller reconciles `main`, merged feature-branch tips,
the validated tracked feature ledger, durable run state, and exact-SHA evidence.
`merged_unverified` means implementation is present but proof is incomplete;
`blocked` carries the missing evidence/reason; only `done` means verified
complete. A missing journal never means a merged feature should be replayed.
Any disagreement returns `recovery-needed`. If main is still the recorded base,
unfinished work is preserved; if integration or state persistence already
occurred, it is finalized exactly once. Any other movement, divergence,
conflict, user change, control-plane drift, or remote change blocks. The
controller never force-resolves or overwrites preserved work.

Cancellation terminates the active child process tree within a finite timeout
and retains commits, branches, worktrees, reports, and state. Authentication,
quota, network, service, evidence, or architecture blockers are reported once
and are not repeatedly retried.

## Service safety

Every canonical test run receives explicit settings for a uniquely named
`shreenexa_autopilot_test_*` Postgres database and Redis database 15. The
controller creates and removes only that validated disposable Postgres name;
it never resets, downgrades, drops, or reuses the `shreenexa` development/user
database. Required skips block promotion.

## Evidence interpretation

Only controller-defined commands are executed. Worker-suggested commands are
untrusted text. Every approval belongs to one exact candidate SHA; a change
invalidates all prior gates and review. Missing/malformed/timeout/unknown
review output and any unresolved finding block integration. Synthetic fixtures
are labelled synthetic and cannot satisfy a required recorded-response gate.

Gate evidence is bound to the controller version and policy digest and includes
the base/candidate SHAs, start/finish times, exit result, report hash, and parsed
test counts. Required test gates must execute at least one test and may not
skip required tests. The controller launches a fresh ephemeral read-only
reviewer session after implementation and rejects implementer self-review.
