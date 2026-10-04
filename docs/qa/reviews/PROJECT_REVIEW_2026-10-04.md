# ShreeNexa Terminal — Senior Project Review

> **Date**: 2026-10-04
> **Reviewer**: Senior developer review (Claude Opus 4.8, Claude Code)
> **Branch**: `feature/sb-f1-data-engine` @ `3fd7989`
> **Scope**: Deep correctness/security audit of trading-critical paths;
> frontend↔backend contract; reconciliation of the two planning tracks;
> offline gate execution. Live-trading and credentialed paths were reviewed
> read-only (never exercised).

---

## 1. Executive summary

ShreeNexa is a **substantial, genuinely-built** trading terminal, not a
greenfield skeleton: ~54k lines of backend Python (FastAPI, **194 REST
endpoints**) and ~39k lines of React/TypeScript frontend. Code quality on the
mechanical axes is high — `ruff`, `mypy --strict` (409 files), frontend
`typecheck`, and the 288-test frontend suite all pass; the backend **unit**
suite is 860 passed / 1 failed (the one failure is the Finding #10 route
collision). The backend **integration** suite is too slow to finish in a
CI-like window and is not runnable offline (§9).

The dominant issue is **not** code defects; it is **integration and
truth-in-labelling**:

1. **Frontend↔backend gap (largest issue).** The backend exposes 194
   endpoints; the running UI calls roughly **22** of them. The entire Strategy
   Builder Feature set (Data Engine, Screener, Strategy Builder, Multi-Variant,
   Paper Engine, Live Engine) and most research/investing/options/monitoring
   surface area have **no functional UI**. The two research-facing views
   (`ResearchView`, `ScreenerView`) are descriptive placeholders that make no
   API calls.

2. **Two disconnected live-execution stacks.** A well-designed, protected
   safety stack (`engine/risk.py` → `engine/broker.py` → `dhan/orders.py`:
   live-disabled-by-default, static-IP preflight, no blind retry) coexists with
   a newer Feature-6 stack (`live/dhan_adapter.py` + `live/safety_guard.py`)
   that the live API actually uses. The newer adapter is an **in-memory mock**
   and its 4-layer guardrails are **never invoked by any reachable endpoint**.
   This is safe *today* (live trading is gated off), but the critical invariant
   "every order passes risk filtering" is not demonstrated or enforced on the
   path that would eventually go live.

3. **Placeholder/fabricated data presented as real.** Several newer endpoints
   return hardcoded numbers (e.g. live daily PnL `4500.0`) or seed fake
   positions into the DB on creation (paper session seeds a `+₹1200` position).
   Fine as UI scaffolding; misleading if mistaken for working behavior.

4. **Stale/contradictory documentation.** `README.md` said "not implemented
   yet" over a ~93k-line codebase (fixed in this pass); `PROJECT_UPDATE.md`'s
   snapshot header is dated 2026-09-01 and still reports "Product runtime: Not
   implemented." Two parallel plans (governed `F0.x` vs Strategy Builder
   Features 1–6) do not reference each other.

**Overall verdict:** architecturally sound core, strong safety design in the
protected layer, clean static analysis — but the product is **backend-heavy
and UI-light**, with a second "demo" engine layer grown beside the original
one. No committed secrets, no legacy-project (`F:\Algotrading`) dependency, and
no look-ahead bias found in the backtester. Not ready for live activation (nor
authorized for it), but a solid base. Priorities below.

---

## 2. Methodology & gate results

Commands were run offline (no Dhan credentials, no live/broker calls).

| Gate | Result |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `mypy backend --strict` | ✅ Success — no issues in 409 source files |
| frontend `typecheck` (`tsc --noEmit`) | ✅ Clean |
| frontend `test` (vitest) | ✅ 288 passed / 67 files |
| `backend/tests/unit` (stack up) | ⚠️ **860 passed, 1 failed** (95s) — failure = route collision (§9, Finding #10) |
| full `uv run pytest` (stack up) | ⚠️ Did not finish — integration suite too slow (~47 tests/15 min); offline run hard-crashes (§9) |
| Secret scan (tracked source) | ✅ No secret-shaped values in tracked `.py`/`.ts` |
| FastAPI route enumeration | ✅ 194 OpenAPI paths registered and served |
| Docker stack (`infra/docker-compose.yml`) | ✅ postgres + valkey healthy |
| `alembic upgrade head` | ❌ **FAILED** — duplicate revisions + cycle (§5.7) |
| App walkthrough (Playwright, 13 views) | ✅ All render; ⚠️ sample data only; demo-mode live calls → 403 (§11) |

**Review gotcha worth recording:** this repo pins **FastAPI 0.141.1**, whose
`include_router` appends a lazy `_IncludedRouter` matcher instead of flattening
sub-routes into `app.routes`. Naively counting `app.routes` shows only 2
`APIRoute`s and looks catastrophically broken. Always enumerate the surface via
`app.openapi()["paths"]` (194) — not `app.routes` — for this version.

---

## 3. The two planning tracks (reconciliation)

| | Governed build plan | Strategy Builder track |
|---|---|---|
| Source | `SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md`, `docs/qa/acceptance/F*.md` | `Strategy Builder/` (Plan + Feature1–6 docs) |
| Framing | "ShreeNexa Terminal" greenfield, process-governed | "Dhan F&O Algo Trading System" |
| IDs | `M0.x`, `F0.x`–`F13.x` | Features 1–6 |
| Status in docs | F0.4/F0.5 blocked; "product runtime not implemented" | Features 1–6 "implemented" per git log |
| Reality (git) | Branch `feature/sb-f1-data-engine`, commits implement Features 1–6 | Matches git history |

These describe the **same product from two eras**. `Plan.MD` and `Plan_V1.0.md`
are **byte-identical duplicates** — one should be removed and the other linked.

**Mapping (how the tracks line up):**

| Strategy Builder | Governed-plan analogue | Backend modules |
|---|---|---|
| F1 Data Engine | F1.x Historical/warehouse | `worker/data_engine/`, `api/data_engine.py`, `warehouse/` |
| F2 Screener | F7.x / `screener` | `screener/`, `api/screener_engine.py` |
| F3 Strategy Builder | F8.x / `strategy` | `strategy/`, `api/strategy_builder.py`, `api/strategy_ir.py` |
| F4 Multi-Variant | backtest + variants | `engine/multi_variant_loop.py`, `engine/variant_models.py`, `api/variant_engine.py` |
| F5 Paper Trading | F9.x / `paper` | `paper/` (older) + `api/paper_engine.py` (newer demo) |
| F6 Live Trading | F12.x / activation-gated | `live/` + protected `engine/`, `dhan/` |

**Recommendation:** adopt one canonical roadmap (a single `ROADMAP.md`) that
states, per feature: backend status, UI status, test evidence, and whether it
is demo-grade or production-grade. Keep the `F0.x` acceptance contracts as the
QA backbone; fold Strategy Builder Features 1–6 into it as the implemented
slice. Do **not** delete Strategy Builder work — it is the real product.

---

## 4. Frontend ↔ backend discrepancy (the central finding)

**Backend surface:** 194 endpoints across `ai, auth, backtests, data, depth,
feature-builder, feed, heatmap, historical, indicators, indices, instruments,
investing, live, monitoring, options, options/analytics, orders, paper,
screener, strategy, variant, watchlists`.

**Frontend actually calls (~22):** `auth/*`, `dhan/token-health`,
`feed/quotes`, `heatmap/*`, `historical/bars|coverage|export|report`,
`indices/*`, `instruments/search`, `orders/ticket/place`,
`paper/orders|fills|portfolio/summary`, `ai/generate-strategy`.

**Good news:** every endpoint the frontend calls **exists** in the backend
(dynamic segments accounted for) — there are **no frontend→404 mismatches** in
the wired surface, and the typed `apiClient` + raw `fetch` contracts line up.

**The gap:** ~**172 endpoints have no UI consumer.** Whole subsystems are
backend-only:

| Area | Backend endpoints (examples) | UI today |
|---|---|---|
| Backtesting | `backtests`, `backtests/run`, `backtests/{id}` | None — `ResearchView` is placeholder text |
| Screener engine | `screener/*` (run, schedule, results) | None — `ScreenerView` is placeholder text |
| Strategy builder | `strategy/*`, `strategy_ir/*` | Isolated TS (`strategybuilder/compiler.ts`, unit-tested) not mounted in a view |
| Multi-variant | `variant_engine` (`/api/v1` tradebook) | None |
| Paper sessions | `paper/sessions/*`, `scorecard`, `drift-analysis`, `quick-compare` | None (UI uses older `paper/orders|fills|portfolio`) |
| Live engine | `live/status|positions|kill-switch|tradebook|risk-settings|reconcile` | None |
| Data engine | `data/sync/*`, `data/candles`, `data/quota` | None |
| Investing | `investing/*` (XIRR, TWR, holdings, SIP, rebalance) | None |
| Options analytics | `options/analytics/*`, `options/chain` | `optionstrategy/` TS exists, not wired to backend |
| Monitoring | `monitoring/*` | None |

**Interpretation:** the project built **backend capability first, UI last**.
This is a legitimate strategy, but it means most "completed" features cannot be
exercised by a user and are only covered by API/unit tests. The single largest
unit of remaining product work is **frontend integration**, not new backend
code.

**Fairness note (confirmed by the live walkthrough, §12):** the UI is *not*
just five stub views — it is a polished, widget-based terminal with ~27
navigable surfaces (watchlist, heatmap, chart, order ticket, blotter, option
chain, strategy builder, backtest summary, P&L, etc.) rendered through a widget
registry. However, those widgets are populated with **client-side sample data**
(e.g. a static "NIFTY Alpha Trend +38.5% / Sharpe 1.85" backtest card), not data
from the 194 backend endpoints. So the gap is better stated as: **the
presentation layer is advanced; the data-integration layer is not.**

---

## 5. Deep audit — trading-critical paths

### 5.1 Risk engine — `backend/app/engine/risk.py` (protected) — SOUND
- Kill switch halts on first tick; `filter_order` rejects while halted.
- Pre-trade caps: notional, price-band (limit orders), position count,
  per-second velocity; reconciliation freeze honored.
- `cancel_order` intentionally allowed during halt (reduces exposure) — correct.
- Minor: a rejected order still consumes a rate-limit slot (timestamp appended
  before downstream checks); market orders skip the price-band check (expected,
  but worth a comment). **No change made (protected path).**

### 5.2 Broker — `backend/app/engine/broker.py` (protected) — SOUND
- Live disabled unless `SHREENEXA_ENABLE_LIVE_TRADING` truthy; static-IP
  preflight enforced; **never blind-retries on timeout** (returns
  `PENDING_BROKER_CONFIRMATION`); freeze-limit slicing with bounded correlation
  IDs (ADR-0007). This is the production-grade path and should be the **only**
  live path.

### 5.3 Live engine (Feature 6) — `backend/app/live/*`, `api/live_engine.py` — GAPS (report-only; user-added feature)
- `DhanLiveExecutionAdapter` is an **in-memory mock** (`client_id="…_MOCK"`,
  hardcoded `150.0` fill, `0.05` slippage) — correct for the no-live gate, but
  labelled "production-grade"/"live".
- **No order-submission endpoint exists**, so `SafetyGuardEngine.
  validate_pre_order_all_guards` (the 4-layer guardrails) and
  `submit_order_async` are **unreachable via the API** — the guard chain is
  effectively dead at the surface and only touched by tests.
- `/live/status` returns **hardcoded** `daily_realized_pnl=4500.0`;
  `/live/reconcile` sets `local = broker` so it can **never** detect drift.
- Two independent risk layers (`engine/risk.py` vs `live/safety_guard.py`) with
  duplicated concerns and no shared source of truth; module-global singletons
  (`_adapter`, `_safety_guard`) can diverge from the DB `kill_switch_active`.
- **Risk for activation:** before live is ever enabled, the live path must route
  through the protected `RiskFilteredBroker`/`DhanBroker` stack, and *every*
  submit must pass guards. Today nothing enforces that on the Feature-6 path.

### 5.4 Paper trading — `backend/app/paper/*` + `api/paper_engine.py` — DUAL LAYER (report-only; user-added)
- Older `paper/` layer (broker, fill_policy, lifecycle, divergence,
  multi_strategy) is the serious engine; the UI uses its endpoints
  (`/paper/orders|fills|portfolio/summary`).
- Newer `api/paper_engine.py` (Feature 5) **seeds a fake position**
  (`NIFTY26OCT25000PE`, entry 150 / current 158 / +1200 unrealized) into the DB
  on every `POST /paper/sessions`. It is a demo scaffold, not a working paper
  trader driven by a live/sim feed. Both mount under `/api/v1/paper` but with
  **non-colliding subpaths**, so they coexist (confusing, not broken).

### 5.5 Backtester — `backend/app/backtest/runner.py`, `engine/sim_broker.py` — LOOK-AHEAD SAFE
- Loop order is **process-fills-then-submit**: an order created on bar *T* is
  filled on bar *T+1*. Default `FillTiming.NEXT_BAR_OPEN` fills at the next
  bar's open. No same-bar leakage in the stock runner.
- Indian cost model applied per fill (STT/CTT, exchange, SEBI, stamp, GST).
- `engine_commit` recorded per result (provenance ✔).
- **Naming bug:** `FillTiming.SIGNAL_BAR_CLOSE` actually fills at the *next*
  bar's close (because submit happens after that bar's processing). Behavior is
  conservative (no look-ahead) but the label misleads. *Non-protected — safe to
  clarify; left as report item to avoid altering backtest semantics without
  sign-off.*
- Limitation: the stock runner only emits MARKET entry/exit; SL+target bracket
  intra-bar ambiguity ("worst-case if both hit in one candle") from the Plan is
  not modelled in this runner (options/futures runners differ).

### 5.7 Database migrations — `backend/alembic/versions/` — BROKEN (Critical; empirically confirmed)

Verified live against the running Postgres stack: `alembic -c backend/alembic.ini
upgrade head` **fails** with:

```
UserWarning: Revision a1b2c3d4e5f6 is present more than once
UserWarning: Revision b2c3d4e5f6a7 is present more than once
UserWarning: Revision c3d4e5f6a7b8 is present more than once
FAILED: Cycle is detected in revisions (a1b2c3d4e5f6, b2c3d4e5f6a7,
        c3d4e5f6a7b8, d4e5f6a7b8c9, e5f6a7b8c9d0, f6a7b8c9d0e1)
```

**Root cause.** The two development tracks independently authored migrations and
**collided on revision IDs**. Three IDs are defined in two files each:

| Revision ID | File A (governed track) | File B (Strategy Builder track) |
|---|---|---|
| `a1b2c3d4e5f6` | `…add_option_type_to_backfill_job` (down `9c0d1e2f3a4b`) | `…create_variant_and_tradebook_tables` (down `f6a7b8c9d0e1`) |
| `b2c3d4e5f6a7` | `…add_window_quality_metrics` (down `a1b2c3d4e5f6`) | `…create_paper_engine_tables` (down `a1b2c3d4e5f6`) |
| `c3d4e5f6a7b8` | `…denormalize_claim_ordering` (down `b2c3d4e5f6a7`) | `…create_live_engine_tables` (down `b2c3d4e5f6a7`) |

The Strategy-Builder chain (`variant → strategy → screener → mkt_data → live →
paper → variant`) also closes into a **cycle** because
`…create_variant_and_tradebook_tables` sets `down_revision = f6a7b8c9d0e1` while
`f6a7b8c9d0e1` is itself downstream of it. The sequential hand-picked hex IDs
(`a1b2…`→`f6a7…`) were chosen without checking they already existed on the
governed lineage.

**Impact.** A fresh environment cannot build its schema via migrations; any
alembic-based deploy, CI migration check, or disaster-recovery restore fails.
Tests pass only because they create tables through SQLAlchemy metadata /
fixtures, not alembic — so this is invisible to the suite and to the UI. It also
violates the repository's provenance/reproducibility invariants.

**Fix (requires sign-off — touches added-feature migrations).** Give the six
Strategy-Builder migrations fresh unique revision IDs and re-chain them as a
single linear sequence appended **after** the current governed head
(`c3d4e5f6a7b8 …denormalize_claim_ordering`), then verify `alembic heads` shows
one head and `upgrade head` + `downgrade base` round-trips on a scratch DB. I
did **not** edit these files, per the instruction not to change later-added
features; this needs an explicit go-ahead.

### 5.6 Determinism
- Backtests key fills off **bar timestamps**, not wall-clock. `datetime.now`
  usage is confined to record metadata (created/updated, run ids) — acceptable.
- No unseeded RNG found in backtest/screener/paper hot paths.

---

## 6. Findings ranked by severity

| # | Sev | Finding | Location | Action |
|---|---|---|---|---|
| 0 | **Critical** | **Alembic migration chain is broken**: 3 revision IDs are each defined twice and the Strategy-Builder migrations form a cycle → `alembic upgrade head` fails; DB schema cannot be built from migrations | `backend/alembic/versions/` | See §5.7 — needs sign-off (touches added-feature migrations) |
| 1 | High | Live order path (Feature 6) bypasses the protected risk/broker stack; guards unreachable; adapter is a mock | `live/`, `api/live_engine.py` | Report — gate for activation; see §10 |
| 2 | High | ~172 backend endpoints have no UI; core research/screener/strategy/backtest views are placeholders | `frontend/src/views/*` | Recommend phased UI integration (§10) |
| 3 | Med | Fabricated/placeholder data returned as real (`4500.0` live PnL; seeded paper position; reconcile stub) | `api/live_engine.py`, `api/paper_engine.py` | Report — label as demo or compute real |
| 4 | Med | Two parallel, non-cross-referenced plans; `Plan.MD`==`Plan_V1.0.md` duplicate | docs | Unify into one roadmap; de-dupe |
| 5 | Med | Stale docs (`README` "not implemented"; `PROJECT_UPDATE` snapshot 2026-09-01) | `README.md`, `PROJECT_UPDATE.md` | README fixed this pass; PROJECT_UPDATE §9 |
| 6 | Low | `FillTiming.SIGNAL_BAR_CLOSE` label vs behavior | `engine/sim_broker.py` | Clarify name/doc |
| 7 | Low | Duplicate rate-limit slot on rejected orders; module-global singletons in live API | `engine/risk.py`, `api/live_engine.py` | Report |
| 8 | Low | Six active git worktrees + `.runtime` recovery trees clutter the tree | repo | Prune stale worktrees |
| 9 | Med | Backend tests can't run offline: DB tests mixed into `unit`, and a DB-less connect **hard-crashes** the interpreter (psycopg access violation) instead of skipping; integration suite is pathologically slow (couldn't finish in 15 min) | `backend/tests/`, DB fixtures | Gate DB tests behind `postgres_or_skip`; speed up/parallelize integration |
| 10 | Med | **Route collision:** `POST /api/v1/strategy/validate` is defined by **both** `strategy_engine` and `strategy_ir` with **incompatible** response shapes (`valid` vs `is_valid`); one silently shadows the other → the 1 failing unit test. Invisible to OpenAPI (dedups) and to `app.routes` checks under FastAPI 0.141 | `api/strategy_engine.py:37`, `api/strategy_ir.py:40` | Give the two endpoints distinct paths or merge them |

No blocking issues were found in the required code-review categories (legacy
dependency, committed secret, look-ahead/survivorship, mutable published data,
process owning out-of-boundary state, broker bypassing risk *on the enabled
path*, protected-path change, fabricated tests). Finding #1 is the one to watch
because it becomes blocking the moment live trading is enabled.

---

## 7. Placeholder / fabricated-data inventory

| Endpoint/func | Fabrication | File |
|---|---|---|
| `GET /api/v1/live/status` | `daily_realized_pnl = 4500.0` hardcoded | `api/live_engine.py:109` |
| kill-switch telegram | `daily_pnl=-4500.0` hardcoded | `api/live_engine.py:201` |
| `POST /api/v1/paper/sessions` | seeds fake `+₹1200` position | `api/paper_engine.py:120-134` |
| `POST /api/v1/live/reconcile` | `local = broker` → never drifts | `api/live_engine.py:390-391` |
| `DhanLiveExecutionAdapter` | mock fills (`150.0`, `0.05`) | `live/dhan_adapter.py:51-55` |

These are not test fakes leaking into prod logic per se, but they **present as
live data** through the API. Recommend a consistent `"data_source": "demo"`
flag on any response not backed by real computation, so the UI can badge it.

---

## 8. Positives worth preserving

- Protected safety stack (`risk.py`/`broker.py`/`dhan/orders.py`) is genuinely
  well-designed: fail-closed live gate, static-IP preflight, no blind retry.
- Backtester is look-ahead-safe with a real Indian cost model and provenance.
- `mypy --strict` clean across 409 files; `ruff` clean; 288 frontend tests pass.
- Clean process/role separation per ADRs; no `F:\Algotrading` coupling.
- No secrets in tracked source; DPAPI-based credential handling.

---

## 9. Changes applied in this review pass

- **`README.md`** — replaced the inaccurate "not implemented yet" with an
  accurate status, safety posture, and the two-track note. No feature behavior
  touched.
- **This report** — `docs/qa/reviews/PROJECT_REVIEW_2026-10-04.md`.

Per the explicit instruction not to modify features added later, **no
Strategy-Builder / Feature 1–6 code was changed.** All findings touching those
features (§5.3–5.4, §7) are report-only.

> **PROJECT_UPDATE.md note:** the snapshot header (2026-09-01, "Product runtime:
> Not implemented") is stale but is governed by the M0.5 validated helper and is
> safety/governance-sensitive; it was **not** edited here to avoid conflicting
> with that process. Recommend refreshing it through `build/update_state.py`.

> **Backend `pytest` note (resolved with stack up):**
> - **Unit suite, stack up:** `backend/tests/unit` → **860 passed, 1 failed in
>   95s**. The single failure is `test_strategy_ir_validate_api_endpoint`
>   (`KeyError: 'is_valid'`), caused by the Finding #10 route collision — the
>   `strategy_engine` `/validate` (returns `valid`) shadows the `strategy_ir`
>   one (returns `is_valid`).
> - **Full suite, stack up:** did **not** finish — only ~47 tests ran in 15 min
>   before the time limit (1 failure among them). The **integration** tests
>   (process-independence / startup) are the bottleneck.
> - **Offline (no stack):** hard-crashes with a Windows fatal exception (access
>   violation) in `psycopg` when a DB-touching "unit" test connects — it should
>   `skip`, not crash the interpreter.
>
> **Recommendations:** fix the route collision (unblocks the 1 unit failure);
> gate DB tests behind a `postgres_or_skip` fixture so offline runs skip cleanly;
> profile/parallelize the integration suite (e.g. `pytest-xdist`) so it can
> complete in CI. Static gates (ruff, mypy --strict, frontend typecheck + 288
> tests) all pass regardless.

---

## 10. Prioritized recommendations

**P0 — before any live-trading work**
1. Make the protected `RiskFilteredBroker`/`DhanBroker` stack the **single**
   live path; have the Feature-6 live engine delegate to it so every submit is
   risk-filtered. Add a parity test asserting "no submit without passing guards."
2. Add a reachable, guard-chained order-submission flow (even if it only ever
   targets the mock/sandbox until the activation gate) so the 4-layer guardrails
   are actually exercised end-to-end.

**P1 — product usability (largest ROI)**
3. Build real `ResearchView` (backtest form → `POST /backtests/run` → results +
   equity curve + metrics) and `ScreenerView` (→ `screener/*`), replacing the
   placeholder text.
4. Mount the already-written `strategybuilder/` and `optionstrategy/` TS modules
   into views wired to `strategy/*` and `options/analytics/*`.
5. Surface paper sessions, live dashboard, and investing analytics in the UI.
6. Promote common calls into the typed `apiClient` (today only auth/health are
   typed; everything else is raw `fetch`).

**P2 — hygiene & truth**
7. Add a `"data_source"` flag (real vs demo) to responses not backed by real
   computation; replace hardcoded `4500.0`/seeded positions with computed values
   or clearly-badged demo data.
8. Unify the two plans into one `ROADMAP.md`; delete the duplicate `Plan.MD`.
9. Refresh `PROJECT_UPDATE.md` via the validated helper; prune stale git
   worktrees.
10. Make `reconcile` compare real local DB state vs broker state.

**P3 — correctness polish**
11. Rename/doc `FillTiming.SIGNAL_BAR_CLOSE` to match actual next-bar-close
    behavior.
12. Model SL+target intra-bar bracket ambiguity in the stock runner (align with
    the Plan's conservative-OHLC rule) or document that only options/futures
    runners do so.

---

## 11. Empirical run (option C) — stack, migrations, app walkthrough

Executed live this session:

- **Docker stack:** brought up `infra/docker-compose.yml` — `postgres:17-alpine`
  and `valkey:8-alpine` both reached **healthy** (127.0.0.1:5432 / 6379).
- **Migrations:** `alembic upgrade head` **FAILED** — duplicate revisions +
  cycle (see §5.7). This is the headline empirical finding.
- **Backend:** an `api` process serves on :8000; `/healthz` and `/openapi.json`
  (194 paths) respond.
- **Frontend:** `vite` dev server on :5173 (proxying `/api` → :8000).
- **Playwright walkthrough** (headless Chromium, demo login via `?demo=true`,
  screenshots saved): all **13 sampled views rendered with no crashes and no
  500s**. Observations:
  - Widgets render **client-side sample data** (blotter "Unrealized +₹2,025";
    backtest "NIFTY Alpha Trend +38.5%"; chart "Sample Historical Data"; option
    chain "Spot ₹24,520") — not backend data.
  - The only **real** backend calls in demo mode returned **403 Forbidden**:
    `GET /api/v1/heatmap/indices`, `GET /api/v1/heatmap/{index}/constituents`,
    and the `ws /api/v1/feed/ws` WebSocket. Cause: these carry
    `require_non_demo_session`, and the demo login is a demo session — **correct
    security behaviour**, but it means demo mode shows no live market data and
    the UI silently falls back to samples.
  - Header correctly surfaces "Dhan Feed: EXPIRED" (token health) and process
    status (API/Engine/Feedd/Worker) in the footer.
- **Conclusion:** the running app is **stable and visually complete** but
  **data-inert** — it demonstrates the §4 gap directly: rich presentation, thin
  wiring, and a broken migration path underneath.

> Tooling installed for this run: Playwright Chromium (ephemeral, via
> `uv run --with playwright`; **not** added to `pyproject`/`uv.lock`). The
> Postgres/Valkey containers were pre-existing and left running.

## 12. Appendix — what was inspected

Read in full or in depth: `AGENTS.md`, `README.md`, `Strategy Builder/Plan*.md`,
`Strategy Builder/Feature5–6`, `PROJECT_UPDATE.md` (snapshot + status), module
trees for `backend/app/{engine,live,paper,backtest,dhan,api}`,
`frontend/src/{api,views,App,Shell}`; FastAPI OpenAPI surface (194 paths);
frontend endpoint usage. Gates executed: ruff, mypy --strict, frontend
typecheck/test; secret scan; route enumeration. Live/credentialed paths were
never executed.
