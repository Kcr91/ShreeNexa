# ShreeNexa — Codex + VS Code Feature Build Plan

**Based on:** `SHREENEXA_TECHNICAL_SPEC.md` v1.1, dated 2026-08-31

**Plan date:** 2026-08-31

**Purpose:** Convert the approved technical specification into safe, reviewable, feature-by-feature work for Codex in VS Code.

**Product:** ShreeNexa Terminal

**Tagline:** *Connected Intelligence. Prosperous Decisions.*

**Repository slug:** `shreenexa-terminal`

---

## 1. Recommended build decision

Create a completely new repository at **`F:\ShreeNexa`**. This keeps ShreeNexa independent from `F:\Algotrading` and uses the drive with substantially more free space for the Parquet warehouse.

`F:\Algotrading` is explicitly outside the new repository. Codex must not import its modules, copy its architecture, edit its files, or make the new terminal depend on it. If historical CSV import is ever wanted later, it must be a separate, optional, read-only import feature approved by the user; it is not part of the initial build.

The approved specification is therefore the source of truth for a greenfield implementation, with the corrections in this plan.

### Binding project rules

1. One feature per branch and one primary Codex chat.
2. Never develop directly on `main`.
3. Codex may create the requested feature branch from a clean `main`; it must stop if unrelated or conflicting changes are present.
4. No feature is merged automatically. The user reviews the diff and the feature report first.
5. A feature is complete only when its acceptance tests, relevant regression tests, lint, types, and compilation/build checks pass.
6. Never read from, write to, or restructure `F:\Algotrading` during normal feature work. The new repo and its data are self-contained under `F:\ShreeNexa`.
7. No real order placement before the explicit Epic 12 approval gate.
8. Safety-critical files require manual review and may not be modified by autonomous feature-building workflows.
9. Every backtest result records data version, StrategyIR snapshot, seed, configuration version, and code commit.
10. Point-in-time membership and no-look-ahead correctness are release blockers, not optional refinements.

---

## 2. Corrections incorporated into this version

These ambiguities in the original draft are resolved in the updated specification and are binding on implementation.

| Ref | Original ambiguity | Binding resolution |
|---|---|---|
| C1 | The source specification named `C:\Users\chand\nifty-terminal`, but the product is now ShreeNexa and the F: drive has more capacity. | Use the new, independent root `F:\ShreeNexa`. Do not mix it with `F:\Algotrading`. |
| C2 | It says “~103 features,” but the listed tables contain **102** features. | Treat the manifest tables as authoritative; generate and validate the count automatically. |
| C3 | Historical index membership uses an `as_of` snapshot table. Removals are difficult to represent correctly with incomplete snapshots. | Use `valid_from`/`valid_to`, `source_date`, and provenance. A query for a past date must return the membership effective on that date. |
| C4 | F2.4, F3.11, F3.13, and F3.14 are UI features scheduled before the frontend shell/layout exists. | Execute them only after F4.1–F4.3. |
| C5 | F3.5 needs delta-based option selection before F8.1 provides Black-76 and the IV solver. | Execute F8.1 before F3.5, or initially restrict F3.5 to offset/premium selection. This plan executes F8.1 first. |
| C6 | Epic 12 live trading precedes production deployment, backup, authentication, and monitoring. | Deploy and prove the paper-only system through Epic 13 before enabling Epic 12 live trading. |
| C7 | The original build harness targeted a different coding-agent CLI, while development is requested in Codex/VS Code. | Use `AGENTS.md`, `.codex/config.toml`, VS Code Codex chats, `/review`, and later `codex exec` for stable repeated checks. Keep runtime AI-provider decisions separate. |
| C8 | The product AI provider and the development coding agent are conflated. | Codex builds the system. The product's NL-to-StrategyIR provider remains a separate pluggable decision; do not assume a ChatGPT subscription is an API credential. |
| C9 | The specification assumes Docker is the simplest choice, but the Windows laptop has 8 GB RAM. | Use Docker Desktop with explicit CPU/RAM limits and only Postgres/Redis running locally; benchmark before adding more containers. |
| C10 | Several Dhan facts are explicitly unverified or may change. | Each affected feature begins with a dated documentation/cassette verification task and stores limits in configuration rather than code. |

---

## 3. Codex setup in VS Code

Official Codex guidance supports using open files/selections as prompt context, reviewing focused diffs beside the code, and sharing model/permission settings between the IDE extension and CLI. Project-specific rules belong in the repository, while personal defaults remain outside it.

### 3.1 Initial VS Code setup

1. Create and open `F:\ShreeNexa` as the VS Code workspace. Do not open it as a subfolder of `F:\Algotrading`.
2. Install or update the official Codex IDE extension and sign in.
3. Set **GPT-5.6 Sol, Medium** as the normal default.
4. Keep normal approval/sandbox settings initially. Do not grant broad unrestricted permission merely to avoid prompts.
5. Keep Codex on native Windows for this repository unless the repository and all tooling are deliberately moved into WSL. Do not split a single working tree across Windows and WSL paths.
6. Create repository-level `AGENTS.md` and `.codex/config.toml` during M0.4, after the audit determines the real commands and layout.

References: [Codex IDE extension](https://learn.chatgpt.com/docs/codex/ide), [Codex models](https://learn.chatgpt.com/docs/models), [Codex best practices](https://learn.chatgpt.com/guides/best-practices), [developer settings](https://learn.chatgpt.com/docs/developer-settings).

### 3.2 Model and reasoning policy

| Code | Configuration | Use |
|---|---|---|
| `SOL-XH` | GPT-5.6 Sol, Extra High | Architecture, StrategyIR, trading-engine semantics, numerical finance, look-ahead/parity design, security, risk, migrations with major data impact. |
| `SOL-H` | GPT-5.6 Sol, High | Complex multi-file features, debugging numerical or concurrency failures, integration design, final review of high-risk changes. |
| `SOL-M` | GPT-5.6 Sol, Medium | Default for ordinary feature implementation and code review. |
| `TER-H` | GPT-5.6 Terra, High | Well-specified backend/UI features with several moving parts. |
| `TER-M` | GPT-5.6 Terra, Medium | Routine endpoints, widgets, adapters, fixtures, and refactors with clear acceptance criteria. |
| `LUN-M` | GPT-5.6 Luna, Medium | Mechanical documentation, repetitive test matrices, configuration transforms, and fixture generation after the design is fixed. |

Use Max only to investigate a genuinely hard blocker. Do not use Ultra for normal feature work; these tasks are deliberately scoped to one reviewable unit.

### 3.3 Repository guidance files

Codex should create these during M0, not invent them independently in later chats:

```text
F:\ShreeNexa\
├── AGENTS.md                         durable project rules and validation commands
├── .codex\config.toml               trusted repo-specific Codex settings
├── docs\architecture\               short authoritative architecture decisions
├── docs\qa\                         gates, fixtures, coverage, review checklist
├── docs\decisions\                  architecture decision records
├── build\manifest.yaml              feature definitions and dependencies
├── build\state.json                 status only; no conversational history
└── build\prompts\                   generated or saved per-feature briefs
```

`AGENTS.md` should include:

- Canonical Windows commands and paths.
- The supported Python and Node versions.
- Data directories that must never be committed or destructively rewritten.
- Protected live-trading paths.
- Required test commands by touched area.
- Branch and commit policy.
- Secrets policy.
- “No look-ahead, deterministic runs, point-in-time universe” invariants.
- The exact completion report format.

---

## 4. Feature execution protocol

Follow this loop for every feature.

### Step A — preflight

Codex reads `AGENTS.md`, the feature card, relevant architecture notes, and only the source files needed for that feature. It runs:

```powershell
git status --short --branch
git log -1 --oneline
python --version
```

It records the baseline tests relevant to the touched code. If the worktree has conflicting user changes, it stops and reports them. If the branch is `main` and clean, the prompt may explicitly authorize Codex to create the named feature branch.

### Step B — contract first

Before production code, Codex writes or updates:

- Acceptance tests.
- Data/API fixture or cassette requirements.
- Migration impact and rollback notes.
- UI behavior, when applicable.
- Explicit non-goals.

### Step C — smallest complete implementation

Implement only the named feature. Do not opportunistically start later features. Shared abstractions are allowed only when the current feature requires them and they are tested.

### Step D — verification

Run the narrow tests first, then all relevant gates:

```powershell
python -m ruff check .
python -m mypy backend --strict
python -m pytest
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build
```

The exact commands are finalized during M0.1–M0.4. `AGENTS.md` then becomes authoritative.

For UI features, also run a real application instance plus Playwright acceptance tests and inspect the affected screens. For numeric features, compare against an independent library or hand-computed fixture. For data migrations, reconcile counts, hashes, date coverage, gaps, duplicates, and samples before/after.

### Step E — review and handoff

Codex reviews its own diff, commits only the feature files, and reports:

1. Branch and commit.
2. Files created/modified.
3. User-visible behavior.
4. Schema/migration impact.
5. Tests and exact results.
6. Manual validation performed.
7. Known limitations or open evidence.
8. Whether it is ready to merge.

The user then uses the Codex `/review` workflow or a separate review chat against `main`. Merge only after that review is clean.

---

## 5. Delivery sequence

The source epics are retained for traceability, but implementation follows dependency-safe release waves.

| Wave | Outcome | Included work |
|---|---|---|
| W0 | New repository created and protected | M0.1–M0.6 |
| W1 | Stable backend foundation | F0.1–F0.9 |
| W2 | Newly downloaded Dhan history available through the new warehouse | F1.1–F1.7 |
| W3 | First trustworthy end-to-end stock backtest | F2.1–F2.3, F2.5–F2.7, F3.1–F3.4, F3.7, F3.10, F3.12 |
| W4 | Usable research UI | F4.1–F4.8 plus deferred F2.4, F3.11, F3.13, F3.14 |
| W5 | Screening and robust research | F2.8–F2.9, F3.9, F6.1–F6.5 |
| W6 | Options research | F8.1 before F3.5; then F3.5–F3.8 and F8.2–F8.7 |
| W7 | Live market data and paper trading | F7.1–F7.9, F9.1–F9.7 |
| W8 | Investing and AI-assisted authoring | F10.1–F10.5, F5.1–F5.4 |
| W9 | Self-extension sandbox, only after paper platform is stable | F11.1–F11.6 |
| W10 | Production paper deployment and promotion proof | F13.1–F13.5, then F11.7 |
| W11 | Live trading, explicit approval only | F12.1–F12.6, followed by a separate activation checklist |

### Release gates

- **R0 — Greenfield baseline protected:** M0 complete; clean checkout builds and tests; `F:\Algotrading` remains untouched.
- **R1 — Backtest MVP:** One StrategyIR stock strategy runs deterministically on the new warehouse data with costs and audited no-look-ahead behavior.
- **R2 — Research terminal:** Browser UI can create/review a strategy, run it, and inspect metrics, scorecard, trades, P&L calendar, and chart markers.
- **R3 — Options research:** Expired options can be backtested with explicit coverage failures and independently validated Greeks/payoffs.
- **R4 — Paper terminal:** Live feed, paper orders, restart recovery, and divergence reporting operate for at least 20 market days.
- **R5 — Production paper:** Auth, backup/restore, monitoring, and deployment rollback proven.
- **R6 — Live eligible:** Explicit user approval plus risk-layer, reconciliation, kill-switch, audit, and broker-cassette gates. Eligibility is not automatic activation.

---

## 6. Feature-by-feature Codex work ledger

The “proof” column is the minimum evidence required in addition to the global gates.

### M0 — Greenfield bootstrap before the listed epics

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| M0.1 | Create `F:\ShreeNexa`, initialize git, verify Python/Node/git/Docker prerequisites, record versions, and create only the minimal README/bootstrap files. | — | New independent repo exists; `F:\Algotrading` was not touched; environment audit names every blocker. | SOL-H |
| M0.2 | Freeze the greenfield architecture, process boundaries, storage ownership, package names, and Windows development topology as ADRs. | M0.1 | Module/dependency map has no circular process ownership and no dependency on the old project. | SOL-XH |
| M0.3 | Define the new terminal's own data-root, immutable raw-download policy, warehouse versioning, backup boundary, and disk-capacity alarms. | M0.1–M0.2 | Data lifecycle/rollback design; all data paths are under the new project or an explicitly configured new data root. | SOL-XH |
| M0.4 | Add `AGENTS.md`, scoped `.codex/config.toml`, architecture index, QA rules, protected paths, and completion-report template. | M0.1–M0.3 | A fresh Codex chat can identify commands, boundaries, and done criteria without repo-wide exploration. | SOL-H |
| M0.5 | Convert the 102 listed features plus M0 into `build/manifest.yaml`; validate IDs, dependencies, cycles, and counts. | M0.4 | Manifest schema test; topological sort succeeds; count is generated, not handwritten. | TER-H |
| M0.6 | Establish the first green baseline and freeze small synthetic/reference fixtures by hash. | M0.1–M0.5 | Clean clone bootstrap and empty test suite gates are green; no unexplained warnings. | TER-M |

### Epic 0 — Foundations

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F0.1 | Standardize the new repo, Python 3.14 venv, Node workspace, lockfiles, ruff, mypy, pytest, frontend test/build, pre-commit, and CI skeleton. | M0.6 | Clean checkout installs from locks; CPython 3.14 binary-wheel check; every baseline command passes. | SOL-H |
| F0.2 | Add resource-limited local Postgres and Redis using Docker Compose; document the WSL2 fallback, but implement only one active path. | F0.1 | `up` makes both healthy; migrations/connectivity smoke tests pass on the 8 GB laptop. | TER-H |
| F0.3 | Create `api`, `engine`, `feedd`, and `worker` process skeletons plus supervisor contracts; no trading behavior yet. | F0.1–F0.2 | Kill/restart `api`; an engine heartbeat and persisted state continue. | SOL-XH |
| F0.4 | Central settings, `.env.example`, secret loading, redaction, and Dhan token-expiry health state/banner API. | F0.1–F0.3 | Secrets never appear in frontend payloads, logs, exceptions, fixtures, or git; expired-token acceptance test. | SOL-H |
| F0.5 | Typed Dhan REST wrapper with injectable transport and recorded cassettes. | F0.4 | Offline cassette tests cover success, auth failure, malformed response, timeout, and retryable error. | SOL-H |
| F0.6 | Verify current Dhan limits, store dated limits in YAML, and implement a Redis token bucket with jittered backoff. Route all Dhan REST calls through it. | F0.2, F0.5 | Hypothesis/concurrency test never exceeds configured limits; architecture test finds no bypassing call site. | SOL-XH |
| F0.7 | Ingest the detailed Dhan instrument master and expose typed search across every segment actually present in the source. Do not hardcode “7” if the master disagrees. | F0.5–F0.6 | Known symbols/options resolve correctly; inactive/duplicate IDs and schema drift are tested. | SOL-H |
| F0.8 | Build current and historical index-constituent ingestion from scratch using effective intervals, official source snapshots, committed fallback, and manual override. | M0.3, F0.7 | Date-aware membership tests; NSE failure uses a stale fallback with visible provenance; unavailable constituents remain non-fatal. | SOL-XH |
| F0.9 | Central connection-budget manager for market-feed and depth sockets, conservative shared pool of five until proven otherwise. | F0.3–F0.5 | Property tests never open socket six; exhaustion is explicit; configuration can switch to independent pools. | SOL-XH |

### Epic 1 — Historical warehouse

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F1.1 | Implement immutable DuckDB/Parquet bar store with typed schema, partition manifest, atomic writes, correction workflow, and read API. | F0.1, M0.3 | Round-trip and partition-pruning tests; interrupted write cannot expose a partial partition. | SOL-XH |
| F1.2 | Dhan daily backfill since inception with resumable windows, provenance, and corporate-action-adjustment investigation. | F0.5–F0.7, F1.1 | NIFTY sample reconciles independently; adjustment status is explicit; no equity backtest is marked trusted until resolved. | SOL-H |
| F1.3 | Build resumable Dhan one-minute backfill in 90-day windows, writing only to the new warehouse. | F0.5–F0.7, F1.1, M0.3 | Per-symbol counts/date coverage/hashes and gap/duplicate report; kill/resume produces no duplicates. | SOL-XH |
| F1.4 | Expired-option 30-day-window backfill with ATM coverage metadata. | F0.5–F0.7, F1.1 | Outside ATM±10/±3 returns `strike_unavailable`; no substitution; restart-safe writes. | SOL-H |
| F1.5 | Per-segment trading sessions, holidays, timezone normalization, and calendar versions. | F0.7, M0.2 | Published-calendar fixtures; no bars outside valid session; IST handling is deterministic. | SOL-XH |
| F1.6 | Session-aware resampling from 1m to 3/5/15/30/60/D/W, including partial-bar policy. | F1.1, F1.5 | OHLC/volume/OI invariants and parity with pandas on independent fixtures. | SOL-H |
| F1.7 | Data-quality reporting for gaps, duplicates, outliers, zero volume, unexpected dates, stale partitions, and coverage by universe/date. | F1.1–F1.6 | Seeded defects are detected; report separates upstream source gaps from warehouse errors. | TER-H |

### Epic 2 — Indicators, StrategyIR, and screener

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F2.1 | Build the vectorized indicator registry in small family batches, not one 100-indicator commit. | F1.1, F1.5–F1.6 | Each primitive matches TA-Lib/pandas-ta or a documented independent reference, including warm-up/NaN policy. | SOL-H |
| F2.2 | Add the incremental implementation for every accepted vector primitive. | F2.1 | G1 parity property test for every primitive; no primitive registers with only one implementation. | SOL-XH |
| F2.3 | Safe formula parser, AST validator, compiler, and restricted evaluator. | F2.1–F2.2 | Fuzz tests; attribute/import/arbitrary-call/negative-ref payloads fail at parse time. | SOL-XH |
| F2.4 | Indicator-builder UI and plotting. Execute after F4.1–F4.3. | F2.3, F4.1–F4.3, F4.6 | Playwright creates, validates, saves, plots, edits, and rejects a malicious formula. | TER-H |
| F2.5 | Versioned Pydantic StrategyIR schema and JSON Schema export, including separate `horizon` and `strategy_type`. | F0.7–F0.8, F2.1 | Round-trip, invalid-node, migration, universe, and option-leg schema tests. | SOL-XH |
| F2.6 | Vectorized StrategyIR compiler/evaluator. | F2.2–F2.5 | Hand-verified strategies plus G2 truncated-data audit; deterministic signals. | SOL-XH |
| F2.7 | Incremental compiler/evaluator with state recovery. | F2.2, F2.5–F2.6 | Repository parity suite proves identical signals/state across vector and streaming runs. | SOL-XH |
| F2.8 | Point-in-time screener runner using the same signal nodes and historical memberships. | F0.8, F1.1, F2.6 | Three hand-verified names; G2; survivorship-bias warning where membership evidence is incomplete. | SOL-XH |
| F2.9 | Screener persistence, scheduling, ranking, export, and routing to watchlists/strategy universes. | F0.3, F2.8 | Offline scheduled-run integration test; output snapshot is reproducible and auditable. | TER-H |

### Epic 3 — Backtester and analysis core

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F3.1 | Engine contracts for clock, data source, broker, portfolio, events, and persistence. | F1.1, F2.5–F2.7 | State-machine properties; restart from persisted checkpoint produces the same result. | SOL-XH |
| F3.2 | `SimBroker` fills and slippage models with explicit signal/fill timing. | F3.1 | No fill outside bar high/low; next-bar semantics prove no same-bar look-ahead. | SOL-XH |
| F3.3 | Effective-dated Indian cost model. | F3.1–F3.2 | Reconciles to a redacted real Dhan contract note and hand fixtures for every supported segment/side. | SOL-XH |
| F3.4 | Stock-strategy backtest runner and persistence. This completes the first vertical slice. | F1.1, F2.6, F3.1–F3.3 | Buy-and-hold and one hand-specified intraday strategy reconcile manually; identical seed/input produces byte-identical output. | SOL-XH |
| F3.5 | Multi-leg options backtest with strike offset, premium, absolute, and delta selectors. Execute F8.1 first. | F1.4, F3.1–F3.4, F8.1 | Hand-computed straddle; unavailable strikes fail explicitly; leg and portfolio P&L reconcile. | SOL-XH |
| F3.6 | Expiry, settlement, square-off, and rolling rules. | F3.5 | No unsettled position survives expiry; holiday-shifted expiry fixtures pass. | SOL-XH |
| F3.7 | Pluggable core metrics registry and breakdowns. | F3.4 | Spreadsheet/reference fixtures; zero-trade and degenerate-return behavior is explicit. | SOL-XH |
| F3.8 | Options-specific metrics and per-leg attribution. | F3.5–F3.7, F8.1 | Independent fixtures for premium capture, Greeks exposure, DTE/IV buckets, margin efficiency. | SOL-XH |
| F3.9 | Parameter sweep, sensitivity surface, and walk-forward evaluation. | F3.4, F3.7 | Deterministic parallel runs; lone-spike visualization data; in/out-of-sample split has no leakage. | SOL-XH |
| F3.10 | Metric grading, four horizon profiles, style-specific win rate, flags, verdict, config version, and deployment gates. | F3.7 | Hand-graded fixtures per profile; contiguous boundary properties; overfit result becomes INVESTIGATE. | SOL-XH |
| F3.11 | Grading Thresholds UI. Execute after F4.1–F4.3. | F3.10, F4.1–F4.3 | Preview before save; invalid bands rejected; old scorecards marked stale; explicit re-grade only. | TER-H |
| F3.12 | Shared daily P&L model for backtest/paper/live with realised, MTM, costs, cashflow, and TWR. | F3.4, F3.7 | Accounting identity, compounding, and pure-cashflow 0% return properties. | SOL-XH |
| F3.13 | P&L calendar widget and drill-down. Execute after F4.1–F4.3. | F1.5, F3.12, F4.1–F4.3 | Playwright day click reconciles to trade book; MTM-only days and segment holidays display correctly. | TER-H |
| F3.14 | Monthly/yearly/rolling returns and continuous mode timeline. Execute after F4.1–F4.3. | F3.12, F4.1–F4.3 | Independent compounded-return fixtures; backtest→paper→live timeline does not double count. | TER-H |

### Epic 4 — Frontend shell, widgets, and charting

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F4.1 | React/TypeScript/Vite shell, routing, theme tokens, API client boundary, error/loading states, and development auth stub. | F0.1, F0.3–F0.4 | Production build, accessibility smoke test, route/error Playwright tests; no secrets in bundle. | TER-H |
| F4.2 | Typed widget registry with settings-schema validation and lazy loading. | F4.1 | A fixture widget appears in the palette without editing layout code; invalid settings fail visibly. | SOL-H |
| F4.3 | Draggable/resizable layout engine with persisted layouts, clone/reset/rename/reorder, and optimistic-conflict handling. | F4.2 | Playwright rearrange→reload persistence; simultaneous-edit behavior is deterministic. | TER-H |
| F4.4 | Seven shipped dashboard preset definitions. Widgets not yet implemented use honest “not available yet” placeholders, never fake data. | F4.2–F4.3 | Create/reset every preset; schema/version migration tests; no missing registry key crashes a dashboard. | TER-M |
| F4.5 | UDF-shaped historical datafeed adapter over the warehouse API. | F1.1, F1.5–F1.6, F4.1 | Requested bars/timezones match direct warehouse queries; pagination and empty ranges tested. | SOL-H |
| F4.6 | Lightweight Charts widget with panes, timeframes, crosshair sync, responsive resizing, and data-boundary states. | F4.2–F4.5 | Playwright multi-chart synchronization; screenshot/visual check at supported viewport sizes. | TER-H |
| F4.7 | Drawing tools with persistence, symbol/timeframe ownership, edit/delete, and version migration. | F4.6 | Draw→reload→edit→delete acceptance flow; drawings never attach to the wrong instrument. | TER-H |
| F4.8 | Backtest widgets: run status, equity, drawdown, trade list, chart markers, metrics, scorecard, and comparison view. | F3.4, F3.7, F3.10, F4.2–F4.6 | UI totals reconcile with API fixtures; marker timestamps/prices link to the exact trade. | TER-H |

After F4.1–F4.3, execute the deferred UI features in this order: **F2.4 → F3.11 → F3.13 → F3.14**.

### Epic 5 — AI strategy generator

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F5.1 | Define the product runtime `AIProvider` protocol, disabled/mock provider, auth-mode checks, redaction, timeout, usage accounting, and pluggable real-provider boundary. Do not couple this to the Codex development extension. | F0.4, F2.5 | Mock contract tests; startup clearly reports disabled/misconfigured provider; prompts/results never leak secrets. | SOL-H |
| F5.2 | Natural-language to schema-constrained StrategyIR through the selected real provider. Provider choice and any API cost require a separate recorded decision. | F2.5, F5.1 | At least 20 representative descriptions yield schema-valid drafts or clear validation errors; adversarial prompt cannot request deployment. | SOL-XH |
| F5.3 | Render generated IR in the visual builder with diff, explanation, warnings, edit, approve, reject, and draft-only status. | F2.4, F5.2 | Playwright confirms generation never changes deployment state and requires user approval before save. | TER-H |
| F5.4 | One-click backtest from an approved generated draft, preserving exact IR/version/provider metadata. | F3.4, F4.8, F5.3 | Generated run equals a manual run with the same IR snapshot and configuration. | TER-H |

### Epic 6 — Composition and regime switching

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F6.1 | Multi-strategy capital allocation and portfolio run orchestration. | F3.4, F3.12 | Allocation invariant, no double-spend, isolated strategy books, deterministic rebalancing. | SOL-XH |
| F6.2 | Combined equity curve, portfolio drawdown, aggregate caps, and marginal contribution. | F6.1 | Combined values reconcile exactly to strategy-level cash/equity fixtures. | SOL-XH |
| F6.3 | Cross-strategy return/signal correlation matrices with missing-period policy. | F6.1–F6.2 | Matches NumPy/reference fixtures; constant/short series behavior is explicit. | SOL-H |
| F6.4 | `StrategySignal` nodes and signal-level `And`/`Or`/`Not` composition. | F2.5–F2.7, F6.1 | G1/G2 across composed strategies; cycle detection rejects recursive strategy graphs. | SOL-XH |
| F6.5 | Versioned regime detectors and enforced walk-forward switching. | F3.9, F6.4 | Headline metrics are refused without walk-forward evidence; no regime label uses future bars. | SOL-XH |

### Epic 7 — Live data layer

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F7.1 | Dhan live-feed WebSocket client, binary packet parser, heartbeat, reconnect state machine, and captured golden packets. | F0.4–F0.7, F0.9 | Independent golden-packet decode; malformed/truncated packets do not corrupt state; no real credentials in fixtures. | SOL-XH |
| F7.2 | Subscription manager across the connection budget, including priority, batching, unsubscribe, reconnect, and resubscribe. | F0.9, F7.1 | Properties enforce ≤5,000/socket and ≤100/message under arbitrary operations. | SOL-XH |
| F7.3 | Redis quote/OI/depth hot cache with schema/version, freshness, and feed-health records. | F0.2, F7.1–F7.2 | Atomic update/read tests; stale data is marked, never presented as live. | SOL-H |
| F7.4 | Browser WebSocket fan-out with snapshots, deltas, backpressure, reconnect/resync, and authorization boundary. | F0.3, F4.1, F7.3 | Three-client consistency test; slow client cannot block feed ingestion. | SOL-XH |
| F7.5 | Multiple manual and F&O watchlists with configurable columns and stable ordering. | F0.7, F4.2–F4.3, F7.4 | Playwright create/edit/delete/reorder; symbols survive instrument-master refresh. | TER-H |
| F7.6 | Sector watchlists and index constituent drill-in driven by effective membership/provenance. | F0.8, F7.5 | Selected historical date/current date returns correct constituents; stale fallback is visible. | TER-H |
| F7.7 | Session-aware live one-minute bar builder merged onto warehouse history. | F1.1, F1.5–F1.6, F7.1–F7.3 | Built bars reconcile with Dhan minute bars; late/duplicate/out-of-order ticks are tested. | SOL-XH |
| F7.8 | Index and constituent heatmaps with breadth and transparent weighting source. | F0.8, F7.4, F7.6 | Cell totals/breadth match fixture calculations; missing weights are labelled and handled deterministically. | TER-H |
| F7.9 | 20-level depth ladder/watchlist, on-demand 200-level book, and explicit 5-level fallback for unsupported segments. | F0.9, F7.1–F7.4 | Golden depth packets; cumulative quantities monotonic; UI shows segment limitation and connection cost. | SOL-XH |

### Epic 8 — Option analytics and strategy builders

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F8.1 | Black-76 pricing, forward selection, Brent IV solver, Greeks, conventions, reliability flags, and vector/incremental forms. Execute before F3.5. | F1.5, F2.1–F2.2 | `py_vollib`/hand parity; put-call parity; delta/gamma/vega bounds; convergence and near-zero-vega cases. | SOL-XH |
| F8.2 | Dhan-chain calibration, convention fitting, tolerance policy, persistence, and drift badge API/UI. | F0.5–F0.7, F8.1 | At least 20 strikes reconcile; theta convention is explicitly validated; unreliable quotes are excluded with reason. | SOL-XH |
| F8.3 | Streaming option-chain widget combining tick prices/OI with locally computed IV/Greeks. | F4.2–F4.3, F7.1–F7.4, F8.1–F8.2 | Tick updates do not exceed render budget; stale/calibration drift is visible; strike/expiry changes resubscribe safely. | SOL-H |
| F8.4 | ATM IV, IV rank/percentile, OI/volume PCR, max pain, skew/smile, and term structure. | F1.4, F8.1–F8.3 | Independent fixtures and explicit minimum-history rules; no division-by-zero/fabricated percentile. | SOL-XH |
| F8.5 | Multi-leg option strategy builder with expiry/T+n payoff, breakevens, extrema, and position Greeks. | F2.5, F4.2–F4.3, F8.1 | Hand-computed standard structures; payoff/Greek aggregation properties; edit/reorder legs. | SOL-XH |
| F8.6 | Net Greeks plus Dhan margin adapter and reconciliation. | F0.5–F0.7, F8.5 | Recorded margin responses match Dhan calculator samples; unavailable margin is explicit, never zero. | SOL-H |
| F8.7 | Visual stock strategy builder mapping exactly to StrategyIR nodes. | F2.4–F2.7, F4.2–F4.3 | UI→IR→UI round-trip preserves meaning; produced IR passes evaluator and G2 tests. | TER-H |

### Epic 9 — Paper trading and forward testing

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F9.1 | `PaperBroker` using the live data source, realistic fill policy, persisted orders/fills, and restart recovery. | F2.7, F3.1–F3.3, F7.3–F7.7 | State-machine properties; G1; restart/replay cannot duplicate a fill. | SOL-XH |
| F9.2 | Paper order book, trade book, positions, live MTM, costs, and rejection/reason display. | F4.2–F4.3, F9.1 | Independent accounting fixture; UI/API/order/fill/position totals reconcile. | SOL-H |
| F9.3 | Multiple concurrent paper strategies with isolated capital and shared account caps. | F6.1, F9.1–F9.2 | No cross-strategy position/cash leakage; deterministic conflict/cap behavior. | SOL-XH |
| F9.4 | Reuse the Epic 3 metric registry for forward-test results without calculation forks. | F3.7–F3.10, F9.2 | The same trade/equity fixture produces the same metrics in backtest and paper modes. | SOL-H |
| F9.5 | Same-session paper-vs-backtest divergence report for signals, timestamps, prices, fills, costs, and P&L. | F3.4, F7.7, F9.1–F9.4 | Known injected divergence is localized and explained; identical inputs reconcile within declared tolerances. | SOL-XH |
| F9.6 | Deploy/pause/resume/stop lifecycle, engine ownership, restart reconciliation, and audit events. | F0.3, F9.1–F9.5 | Restarting `api` never stops an engine deployment; stop is idempotent; stale state is reconciled. | SOL-XH |
| F9.7 | Paper P&L calendar and monthly/yearly returns by reusing F3.12–F3.14. | F3.12–F3.14, F9.2–F9.6 | `source_kind='paper'` totals reconcile; no duplicated calendar or return-calculation code path. | TER-H |

Paper trading must run for at least **20 market days** with reviewed divergence reports before the project becomes eligible for any live-order work.

### Epic 10 — Long-term investing

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F10.1 | Holdings ledger, lots, average cost, corporate actions, and realised/unrealised P&L import/reconciliation. | F0.5–F0.7, F3.3, F4.2–F4.3 | Reconciles to redacted Dhan account fixtures; transfers/corporate actions do not masquerade as returns. | SOL-XH |
| F10.2 | XIRR plus sector/asset allocation and benchmark-aware performance. | F0.8, F10.1 | Excel XIRR parity across irregular cashflows; multiple-root/failure behavior is explicit. | SOL-XH |
| F10.3 | Dividend event ledger, import, matching, withholding/tax metadata, and income views. | F10.1 | Recorded/hand fixtures; unmatched payment is reported rather than assigned to the wrong holding. | SOL-H |
| F10.4 | SIP planning and calendar/threshold rebalancing proposals. No automatic orders. | F1.5, F10.1–F10.3 | Cashflow/TWR separation; G2; proposal totals respect cash and configured limits. | SOL-H |
| F10.5 | Point-in-time sectoral momentum rotation research strategy. | F0.8, F2.5–F2.7, F3.4, F3.9, F10.2 | G2, survivorship-bias checks, and enforced walk-forward evidence. | SOL-XH |

### Epic 11 — Codex feature-builder pipeline

This epic replaces the original vendor-specific development harness. Build it only after the research and paper platform is stable. Interactive VS Code Codex remains the primary supervised workflow; automation uses officially supported Codex CLI/non-interactive interfaces available at implementation time.

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F11.1 | Feature request → structured, editable implementation specification tied to the manifest. | F4.1–F4.4, M0.5 | Ambiguous/high-risk requests require approval; generated spec names scope, tests, risk, dependencies, and protected paths. | SOL-XH |
| F11.2 | Git worktree creation, branch ownership, path validation, cleanup, and recovery. | F11.1 | Property/acceptance tests prove the runner cannot write outside its worktree. | SOL-XH |
| F11.3 | Codex task runner with bounded fresh task context, structured events, browser stream, cancellation, and durable state. | F11.1–F11.2 | Interrupt/restart resumes from git/state, not conversation history; auth/usage errors are explicit. | SOL-XH |
| F11.4 | Gate harness for G1–G6 plus filtered failure summaries and bounded retry policy. | F11.3 | Deliberately broken parity/look-ahead/type/UI/protected-path fixtures are all blocked. | SOL-XH |
| F11.5 | Protected-path enforcement for risk, broker, live orders, and parity fixtures at prompt/tool/diff/promotion layers. | F11.2–F11.4 | Attempted protected edit is denied and audited even if one enforcement layer is bypassed. | SOL-XH |
| F11.6 | Isolated sandbox ports, database schema, Redis database, read-only warehouse, and hard-wired `PaperBroker`. | F9.1–F9.6, F11.4–F11.5 | Sandbox has no credentials or network/code path capable of placing a live order. | SOL-XH |
| F11.7 | Approval-gated blue/green promotion, health check, drain, rollback, and history. | F11.6, F13.1–F13.3 | Promote/rollback during an active paper strategy; engine is not restarted; audit is complete. | SOL-XH |

### Epic 13 — Production deployment (execute before Epic 12)

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F13.1 | Production containers for `api`, `engine`, `feedd`, and `worker`, with non-root users, health checks, resource limits, and immutable images. | F9.1–F9.7 | Local production stack starts cleanly; restarting API leaves engine/paper deployment intact. | SOL-XH |
| F13.2 | Lightsail Mumbai provisioning, network policy, systemd/container supervision, Caddy TLS, and blue/green upstream. | F13.1 | Staging deploy/rollback runbook is executed; only intended public ports are reachable. | SOL-XH |
| F13.3 | Single-user password + TOTP auth, secure sessions, recovery process, rate limiting, and audit. | F4.1, F13.2 | Security tests for session fixation, CSRF, brute force, secret storage, and WebSocket authorization. | SOL-XH |
| F13.4 | Nightly Postgres/Parquet/config backups, retention, encryption, integrity checks, and documented restore. | F13.2–F13.3 | Restore into a clean staging box succeeds and reconciles counts/hashes. | SOL-XH |
| F13.5 | Uptime, feed freshness, disk, token expiry, queue, engine, backup, and data-gap monitoring with actionable alerts. | F13.1–F13.4 | Injected failures trigger one clear alert and recovery notice; stale feed cannot look healthy. | SOL-H |

### Epic 12 — Live trading (last; explicit approval only)

These features are never assigned to the unattended Epic 11 builder. Use supervised Codex chats, one protected change at a time, two independent reviews, broker cassettes, and a live activation checklist. Development completion does not authorize live activation.

| ID | Codex work unit | Depends on | Minimum proof | Model |
|---|---|---|---|---|
| F12.1 | Typed `DhanBroker` order mapping, idempotency keys, timeout/unknown-state handling, and disabled-by-default feature gate. | F0.5–F0.7, F9.1–F9.6, F13.1–F13.5 | Offline cassettes/state properties; no test can reach live Dhan; startup remains paper-only by default. | SOL-XH |
| F12.2 | Live Order Update WebSocket, postback ingestion, deduplication, sequence gaps, and reconciliation. | F7.1–F7.3, F12.1 | Duplicate/lost/out-of-order events converge to broker truth without duplicate fills. | SOL-XH |
| F12.3 | Live order ticket with explicit mode, estimated charges/margin, confirmations, validation, and status uncertainty. | F4.2–F4.3, F8.6, F12.1–F12.2 | Playwright cannot submit accidentally; paper/live are unmistakable; uncertain order state blocks blind retry. | SOL-XH |
| F12.4 | Account risk layer: kill switch, capital/loss/position/order-rate/price-band caps, and broker-path enforcement. | F3.1, F9.3, F12.1–F12.3 | Exhaustive test proves no path reaches `DhanBroker` without risk filtering; kill switch halts within one tick. | SOL-XH |
| F12.5 | Continuous positions/orders/funds reconciliation against Dhan with freeze-on-mismatch policy. | F12.1–F12.4 | Seeded mismatch freezes affected trading and creates a clear resolution workflow; no silent auto-correction. | SOL-XH |
| F12.6 | Immutable audit of every signal, filter, risk decision, order request, response, update, reconciliation, override, and kill-switch event. | F12.1–F12.5 | One trade can be reconstructed end to end; sensitive values are redacted; audit tampering is detectable. | SOL-XH |

### Live activation is a separate decision

After F12.6, require a separate checklist and explicit user message authorizing activation. Minimum conditions:

- 20 reviewed paper-market days.
- No unresolved severe divergence.
- Latest backup restore passed.
- Kill-switch drill passed.
- Dhan reconciliation drill passed.
- Maximum capital and daily-loss limits entered by the user.
- First live run uses minimum quantity and one approved strategy.
- Human supervision for the entire first session.

---

## 7. How to split oversized features

The manifest counts 102 product features, but some are too large for one safe code change. Split them into numbered tasks inside the same feature branch and review after each task commit.

Examples:

| Feature | Recommended internal tasks |
|---|---|
| F2.1 | Registry contract → trend → momentum → volatility → volume → structure → statistical → options/session primitives. |
| F2.2 | Incremental base/warm-up policy → one task per indicator family → full parity registry gate. |
| F3.7 | Equity/trade basics → risk-adjusted metrics → drawdown/duration → breakdowns/curves → edge cases/reference report. |
| F4.6 | Data/render core → panes → timeframe changes → crosshair sync → responsive/accessibility/performance. |
| F7.1 | Connection lifecycle → header parser → each packet type → OI packets → golden fixtures/fuzzing. |
| F8.1 | Price functions → Greeks → IV solver → forward/conventions → reliability flags → vector/incremental parity. |
| F12.4 | Risk policy schema → pure decision engine → persistence/recovery → enforcement proof → kill-switch drill. |

A task may be retried inside its feature branch. Do not open the next product feature until the current feature report is accepted.

---

## 8. Reusable Codex prompt template

Paste this into a fresh VS Code Codex chat for one feature.

```text
Model/configuration: <MODEL CODE FROM THE PLAN>

Implement exactly <FEATURE ID>: <FEATURE NAME> in the new greenfield repository
F:\ShreeNexa.

Read first:
- AGENTS.md
- build/manifest.yaml entry for <FEATURE ID>
- the directly relevant docs/architecture and docs/qa files
- only the code/tests needed for this feature

Repository safety:
- F:\Algotrading is out of scope. Do not read, edit, copy, import, or depend on it.
- Run git status and record the current branch/HEAD before editing.
- If main is clean, you are authorized to create and switch to
  feature/<feature-id>-<short-slug>.
- If there are unrelated or conflicting changes, stop and report them.
- Do not merge to main.
- Preserve unrelated files and untracked user work.
- Never expose or commit credentials.

Scope:
- Implement only <FEATURE ID>.
- State assumptions and non-goals before editing.
- Write/update the acceptance contract and tests before production code.
- Do not start later features or perform unrelated cleanup.

Required acceptance:
<COPY THE “MINIMUM PROOF” CELL AND MANIFEST ACCEPTANCE ITEMS HERE>

Verification:
- Run the narrow tests first.
- Run every AGENTS.md gate required for the touched areas.
- For numerical behavior, compare against the named independent reference.
- For UI behavior, run the real app plus Playwright and inspect the changed views.
- Review the complete diff for regressions, look-ahead, nondeterminism, unsafe
  paths, secrets, and scope creep.

Commit only when all required checks pass. End with:
1. branch and commit SHA;
2. files created/modified;
3. behavior delivered;
4. schema/migration impact;
5. tests with exact pass/fail counts;
6. manual validation;
7. limitations/open evidence;
8. whether it is ready to merge.
```

### Review prompt

Use a separate Codex review chat or `/review` after implementation:

```text
Review branch <BRANCH> against main for feature <FEATURE ID>.

Read AGENTS.md and the manifest acceptance contract. Do not edit on the first
pass. Verify scope, correctness, tests, point-in-time behavior, look-ahead,
determinism, numerical references, secrets, migrations, concurrency, UI states,
and whether the completion report is accurate. Rank findings by severity and
cite files/lines. If there are no blocking findings, say exactly what evidence
you checked and whether the branch is safe to merge.
```

### Fix-review prompt

```text
Address only the confirmed findings from the review of <FEATURE ID>. Preserve
the accepted feature behavior. Add regression tests for each bug, run the full
required gates, review the final diff, commit the fixes on the same feature
branch, and update the completion report. Do not merge.
```

---

## 9. First Codex task — ready to paste

Before pasting this prompt, create/open the empty folder `F:\ShreeNexa` in VS Code and select **GPT-5.6 Sol, High**.

```text
Implement M0.1: greenfield repository and environment bootstrap.

This is a brand-new project at F:\ShreeNexa. F:\Algotrading is a separate,
older project and is completely out of scope. Do not read it, edit it, copy from
it, or make this project depend on it.

Goals:
1. Confirm the current workspace path is exactly F:\ShreeNexa.
2. Audit Windows version, available disk space, Python, pip, Node, npm, git,
   Docker Desktop/Compose, WSL status, and whether required executables are on
   PATH. Do not install missing prerequisites in this task.
3. If this folder is not already a git repository, initialize it with main as
   the default branch and create an empty baseline commit. If git identity is
   missing, stop and report the exact commands the user must run; do not invent
   an identity.
4. Create and switch to feature/M0.1-greenfield-bootstrap.
5. Create only:
   - README.md with project purpose and “not implemented yet” status;
   - a strong root .gitignore for Python, Node, secrets, databases, Parquet,
     logs, caches, IDE output, and local runtime data;
   - docs/environment-audit.md with commands, observed versions, pass/blocker
     status, and next required action;
   - docs/decisions/README.md explaining that architecture ADRs start in M0.2.
6. Do not scaffold backend/frontend packages, install dependencies, add Docker
   files, or implement any terminal feature yet.
7. Verify git status contains only the intended files and that no secret-looking
   value is present.
8. Commit the feature as: chore: bootstrap ShreeNexa repository

Completion report:
- workspace path;
- branch and commit SHA;
- environment table;
- blockers;
- files created;
- verification performed;
- confirmation that F:\Algotrading was untouched;
- ready/not ready for M0.2.

Do not merge to main.
```

---

## 10. Progress control

Update `build/state.json` only through a validated helper introduced in M0.5. At minimum track:

```json
{
  "feature": "M0.1",
  "status": "pending | in_progress | review | done | blocked | parked",
  "branch": null,
  "commit": null,
  "tests": {},
  "started_at": null,
  "finished_at": null,
  "blockers": []
}
```

Do not estimate the full completion date before M0.5. After the first 10 representative features, calculate actual median time by feature class and reforecast. The source document's 23–25 week estimate is a planning hypothesis, not a commitment.

### Stop conditions

Codex stops the current feature and asks for direction when:

- The worktree contains conflicting user changes.
- A dependency/acceptance decision is missing and materially changes behavior.
- A Dhan/API fact cannot be verified from current official evidence.
- A test would require real order placement.
- A migration could overwrite or discard data.
- A protected live-trading path appears in an unattended build.
- A secret appears in source, logs, fixtures, or frontend output.
- Required independent numerical/reference evidence cannot be obtained.

---

## 11. Definition of project success

The terminal is not “done” because all feature IDs have commits. It is done only when:

- A clean production restore works.
- Backtest/vector and paper/live incremental signals are proven equivalent.
- All universe queries are point-in-time or honestly flagged as biased.
- Costs, fills, metrics, Greeks, and returns reconcile to independent evidence.
- Paper trading survives restarts and reconciles against same-session backtests.
- Live trading remains disabled until explicit activation.
- Every live order decision is risk-filtered and auditable.
- `F:\ShreeNexa` is self-contained and `F:\Algotrading` remains independent.
