# QA Layers and Cross-Cutting Gates

## Test layers

| Layer | Meaning | Required examples |
|---|---|---|
| L1 | Unit | Pure domain/numeric/state functions |
| L2 | Independent reference/golden | TA-Lib/pandas-ta, `py_vollib`, hand spreadsheets, contract notes, captured packets |
| L3 | Property-based | Invariants across generated histories, prices, states, limits, and transitions |
| L4 | Integration | Offline recorded Dhan cassettes and local service integration |
| L5 | Acceptance | User-visible workflow, Playwright for UI, clean-checkout behavior |

Never validate a numeric implementation solely against another code path sharing the same formula.

## Cross-cutting gates

| Gate | Requirement | Activation |
|---|---|---|
| G1 | Vectorized/incremental IR and indicator parity | Indicator/IR and all signal-consuming modes |
| G2 | Truncated-history no-look-ahead plus point-in-time universe audit | Strategy, screener, backtest, paper/live signal work |
| G3 | Same input/version/configuration/seed gives byte-identical result | All reproducible jobs and numeric outputs |
| G4 | Ruff, strict mypy, frontend TypeScript, tests, production build | Commands activate in F0.1; touched-area subset plus full required gate |
| G5 | Coverage: 90% analytics/IR/engine/backtest; 80% other backend; 70% UI | Once executable modules and coverage config exist |
| G6 | No unattended protected-path change | Every automated build/review/promotion diff |

## Canonical commands

Currently active for documentation/bootstrap:

```powershell
git status --short --branch
git diff --check
```

Also parse every touched structured format, resolve local links, validate stated paths/rules with representative probes, and scan changed files for secret-shaped values.

Activated by F0.1:

```powershell
python -m ruff check .
python -m mypy backend --strict
python -m pytest
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run build
```

Do not weaken a gate, exclude code, lower coverage, or mark a command optional merely to make a feature green. Changes to gate policy are their own reviewed scope.
