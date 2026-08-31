# Protected Paths

## Protected set

```text
backend/app/engine/risk.py
backend/app/engine/broker.py
backend/app/dhan/orders.py
backend/tests/parity/
```

These paths contain or prove controls that separate a research/paper system from unsafe order execution. Unattended or automated feature-building workflows may not modify them.

## Required supervised process

A protected-path change requires all of the following:

1. Explicit user authorization naming the protected feature/path.
2. A dedicated branch and contract with no unrelated feature work.
3. Targeted safety, state-machine, parity, failure, and bypass tests as applicable.
4. Proof that routine tests cannot reach live Dhan endpoints or use live credentials.
5. Independent review of the complete branch and a final protected-path diff report.
6. Two reviews for Epic 12 live-order work, as required by the approved plan.
7. Separate live-activation approval even after implementation is merged.

No configuration flag, strategy field, UI request, plugin, or generated feature may bypass `risk.filter` on a broker path.

## Review-sensitive guidance

`AGENTS.md`, `.codex/config.toml`, QA gate definitions, and protected-path lists are not part of G6's runtime protected set, but changes to them can weaken enforcement. Modify them only in explicit guidance/QA scope and review the effective permission and instruction chain.

## Diff check

For any branch under review, list protected changes explicitly:

```powershell
git diff --name-only main...HEAD -- backend/app/engine/risk.py backend/app/engine/broker.py backend/app/dhan/orders.py backend/tests/parity
```

Any output blocks unattended promotion and requires the supervised process above.
