# ShreeNexa — Complete Technical Specification

**Version:** 1.1
**Date:** 2026-08-31
**Owner:** chandreshkhunt91@gmail.com
**Status:** Approved plan, not yet implemented
**Product name:** ShreeNexa Terminal
**Tagline:** *Connected Intelligence. Prosperous Decisions.*
**Companion file:** `SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md`

---

## Table of contents

1. [Goals and scope](#1-goals-and-scope)
2. [Environment audit and prerequisites](#2-environment-audit-and-prerequisites)
3. [Verified external API reference](#3-verified-external-api-reference)
4. [System architecture](#4-system-architecture)
5. [Data model](#5-data-model)
6. [StrategyIR specification](#6-strategyir-specification)
7. [Execution engine](#7-execution-engine)
8. [Indicator system](#8-indicator-system)
9. [Screener](#9-screener)
10. [Backtester and metrics catalogue](#10-backtester-and-metrics-catalogue)
11. [Option analytics](#11-option-analytics)
12. [Live data layer](#12-live-data-layer)
13. [Frontend: widget registry and layout engine](#13-frontend-widget-registry-and-layout-engine)
14. [AI layer](#14-ai-layer)
15. [Build orchestrator](#15-build-orchestrator)
16. [QA standard](#16-qa-standard)
17. [Feature manifest](#17-feature-manifest)
18. [Risks and open items](#18-risks-and-open-items)
19. [Glossary](#19-glossary)

---

## 1. Goals and scope

### 1.1 What this is

**ShreeNexa** is a personal algorithmic trading and investment terminal for Indian markets, running on your paid DhanHQ Data API. It covers the complete lifecycle of a trading idea:

```
idea → indicator/rule definition → screen for candidates → backtest on history
     → analyse with full metrics → combine with other strategies
     → forward-test on paper against live data → deploy live
```

It serves both **intraday/F&O trading** and **long-term investing**. Development is performed feature by feature with Codex in VS Code. After the research and paper-trading platform is stable, a built-in Codex-compatible pipeline may build new features in isolated worktrees, gate them behind tests, run them in a paper-only sandbox, and promote them without disturbing running strategies.

### 1.2 The three organising ideas

**One strategy definition drives everything.** A strategy is a validated JSON document (the *StrategyIR*). The screener, backtester, paper engine and live engine all consume the same document. What you test is literally what trades — there is no translation step in which behaviour can drift.

**Process separation makes zero-downtime real.** The strategy engine runs as a separate supervised process from the web API, with all state in Postgres/Redis. Promoting a new build restarts the API while your strategies keep running.

**The build harness is part of the product.** The orchestrator that constructs this system from the feature manifest is the same machinery that later builds features on request, and the same progress widget tracks both.

### 1.3 In scope

| Area | Included |
|---|---|
| Segments | NSE Equity, NSE F&O, NSE Currency, BSE Equity, BSE F&O, MCX Commodity, Indices |
| Instruments | Equity, index, futures, options (index + stock), currency, commodity |
| Data | Live tick feed, 20-level depth, daily history since inception, 1-minute history 5 years, expired-options minute history 5 years |
| Research | Indicator builder, visual rule builder, screener, backtester, parameter sweep, walk-forward |
| Analysis | Full institutional metrics + options-specific metrics; strategy combination; correlation; regime detection |
| Execution | Paper trading (forward test), then live trading behind a risk layer |
| Investing | Holdings, XIRR, allocation, dividends, SIP, rebalancing, sectoral momentum rotation |
| UI | Configurable widget dashboards, TradingView-style charting, option chain with Greeks, heatmap, order book |
| AI | Natural-language → strategy generation; self-extension pipeline |

### 1.4 Explicitly out of scope

| Excluded | Why |
|---|---|
| Fundamental data screening (P/E, ROE, growth) | Dhan provides none. Free sources are fragile and legally grey. Can be added later behind a flagged adapter |
| Far-OTM option backtesting | Dhan's expired-options history covers ATM±10 (index) / ATM±3 (stock) only. Confirmed acceptable — strategies are near-ATM |
| Pine Script compatibility | Pine Script is TradingView-proprietary. Not reimplemented. An equivalent formula language is built instead |
| Multi-user / SaaS | Single user. Distribution would require a separate security, tenancy, licensing, and runtime-AI review |
| Non-Indian markets | Dhan is India-only |

### 1.5 Costs

| Item | Cost | Status |
|---|---|---|
| DhanHQ Data API | ₹499 + GST / month, renews every 30 days | Active |
| Codex access through ChatGPT | Existing | Active; model/usage availability depends on the signed-in plan |
| Product runtime AI provider | TBD; disabled by default | No credential or API cost until separately approved and enabled |
| All software (Python, Postgres, Redis, DuckDB, React, Lightweight Charts) | Free / open source | — |
| AWS Lightsail Mumbai (deferred to Epic 13) | ~$12/mo (2GB) or ~$24/mo (4GB) | Not yet provisioned |
| Vercel (frontend) | Free tier | Not yet provisioned |

---

## 2. Environment audit and prerequisites

Audited on the target machine, 2026-08-30.

### 2.1 What is present

| Tool | Version | Path |
|---|---|---|
| Python | 3.14.5 | `C:\Python314\python.exe` |
| Node.js | 24.15.0 | `C:\nvm4w\nodejs\node.exe` |
| npm | 11.12.1 | — |
| git | 2.54.0.windows.1 | — |
| OS | Windows 10 Home 10.0.19045 | — |

**Python version: 3.14.5 confirmed as the build target.** An earlier draft of this spec proposed pinning 3.13 on the assumption that numba — used for fast incremental indicator loops — would lag the 3.14 release. That was verified against PyPI on 2026-08-30 and found to be false. Every dependency in the stack publishes CPython 3.14 wheels for `win_amd64`:

| Package | Version | cp314 win_amd64 wheel |
|---|---|---|
| numba | 0.67.0 | Yes |
| numpy / pandas / scipy | 2.5.2 / 3.0.5 / 1.18.1 | Yes |
| duckdb / pyarrow | 1.5.5 / 25.0.1 | Yes |
| pydantic-core / psycopg-binary | 2.48.0 / 3.3.4 | Yes |
| TA-Lib | 0.7.1 | Yes — binary wheel, no C-library build step on Windows |
| hypothesis / websockets | 6.167.1 / 17.1 | Yes |
| redis, fastapi, uvicorn, pandas-ta, py-vollib, dhanhq, polars | current | Pure Python (`py3-none-any`), version-agnostic |

Python 3.14 was released roughly ten months before this audit, which is ample time for the compiled scientific stack to catch up — and it has. **No second Python install is required.** Re-run this check if a new dependency with compiled extensions is added later.

### 2.2 Gaps that block the build — resolve before Epic 0

| # | Gap | Why it matters | Resolution |
|---|---|---|---|
| P2 | **Docker not installed** | Postgres and Redis run as containers in local development | Install Docker Desktop for Windows |
| P3 | **WSL has no distribution installed** (feature present, no distro) | The fallback path for Postgres/Redis if Docker is unwanted | `wsl --install -d Ubuntu`, then install Postgres and Redis inside it |
| P4 | **Codex IDE/CLI readiness not yet verified in the new repository** | Feature development uses the Codex VS Code extension; the later build orchestrator uses supported Codex CLI interfaces | Sign in to Codex in VS Code, verify the sidebar works, and record the installed CLI/version only when Epic 11 begins |
| P5 | **git has no global `user.name` / `user.email`** | The orchestrator auto-commits after each green task; commits fail without an identity | `git config --global user.name "..."` and `git config --global user.email "chandreshkhunt91@gmail.com"` |

**Pick one of P2 or P3 — not both.** Docker Desktop is the simpler path on Windows 10 Home.

### 2.3 Prerequisites that are not local

| # | Item | Action |
|---|---|---|
| P6 | Dhan `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN` | Generate manually at web.dhan.co. **Never** commit these or expose them to the frontend. Dhan documents a 24-hour validity for manually generated Dhan Web access tokens; this is distinct from the Data API subscription renewal period and from other authentication artifacts. Production uses injected server-side environment variables. Local development may persist only the client ID, access token, and non-secret absolute expiry metadata using current-Windows-user DPAPI, with no plaintext fallback. The terminal monitors expiry and shows a non-secret banner |
| P7 | TradingView Advanced Charting Library application | Free but requires approval, which can take weeks. Apply in week 1. Nothing is blocked on it — the datafeed is written in TradingView's UDF shape so approval becomes a swap, not a rewrite |
| P8 | Current supported Codex IDE extension and CLI | Pin the tested version when Epic 11 begins; do not design the orchestrator around undocumented flags or output formats |

### 2.4 Repository location

```
F:\ShreeNexa\        (new independent git repository — not yet created)
```

`F:\Algotrading` is a separate legacy project and is out of scope. ShreeNexa must not import its modules, edit its files, or depend on it.

---

## 3. Verified external API reference

Everything in this section was verified against live documentation, not assumed. Where a fact could not be verified, it is marked **UNVERIFIED** and carries a resolution step.

### 3.1 DhanHQ v2 — subscription and access

| Item | Detail |
|---|---|
| Trading APIs | Free |
| Data API | ₹499 + GST / month, renews every 30 days. Required for live market feed, market quotes, and all historical data |
| Base docs | `https://dhanhq.co/docs/v2/` |
| Python SDK | `dhanhq` 2.2.0 (released 2026-04-24). Covers orders, feed, quotes, option chain, historical, live order updates, 200-level depth. Version 2.2.0 introduced breaking changes from 2.0.2 |

### 3.2 Live Market Feed (WebSocket)

| Property | Value |
|---|---|
| Connections per user | **5** |
| Instruments per connection | **5,000** (total 25,000) |
| Instruments per subscribe message | **100** (send multiple messages to reach 5,000) |
| Request format | JSON: `RequestCode` (int, selects mode), `InstrumentCount` (int), `InstrumentList` (array of `{ExchangeSegment, SecurityId}`) |

**Packet modes:**

| Mode | Contents |
|---|---|
| Ticker | LTP, Last Traded Time |
| Quote | LTP, last traded qty, average trade price, volume, total buy/sell qty, day OHLC. Open Interest arrives as separate packets |
| Full | All Quote fields + 5 levels of bid/ask (price, quantity, order count) + Open Interest |

**Critical design note:** the feed delivers **prices and OI only — never IV or Greeks**. Those are computed locally (see §11).

### 3.3 Full Market Depth (WebSocket)

A socket separate from the Live Market Feed, with its own limits.

| Property | Value |
|---|---|
| **20-level depth** | **Up to 50 instruments per connection** |
| **200-level depth** | **Exactly 1 instrument per connection** |
| Connections | Maximum 5. **Opening a sixth disconnects the first** |
| Request code | `23` for both modes |
| Subscription — 20 level | `RequestCode`, `InstrumentCount`, `InstrumentList[]` of `{ExchangeSegment, SecurityId}` |
| Subscription — 200 level | `RequestCode`, `ExchangeSegment`, `SecurityId` directly — no array |
| Packet | 12-byte header, then 16 bytes per level: price `float64` (8B), quantity `uint32` (4B), order count `uint32` (4B) |
| Keepalive | Server pings every 10 s; client must respond within 40 s or be disconnected |
| **Segments** | **NSE Equity and NSE Derivatives only** |

**Two consequences that shape the design:**

1. **Depth is available for many scripts at once, not one.** 50 instruments per connection at 20 levels is ample for a depth watchlist. 200-level is the exception — it consumes an entire connection for a single instrument, so it is reserved for the one explicitly focused script and subscribed on demand.
2. **BSE, MCX and currency have no Full Market Depth.** For those segments the deepest available book is the **5 levels carried in the regular feed's Full packet**. The UI must show 5 levels there and say why, rather than rendering an empty 20-level ladder that looks like a bug.

### 3.3.1 UNVERIFIED — is the 5-connection limit shared?

The Live Market Feed documents "up to five WebSocket connections per user"; Full Market Depth separately documents "maximum 5 WebSocket connections". **Whether these are two independent pools of 5, or one shared pool, is not stated.** If shared, consuming all five on the market feed would leave none for depth.

**Resolution:** feature F0.9 builds a central **connection budget manager** that owns every Dhan socket and allocates from a configured budget. Until the question is settled empirically, it defaults to the conservative assumption of **one shared pool of 5**, split 3 feed / 2 depth. If the pools turn out to be independent, the split becomes 5 / 5 as a configuration change with no code impact.

### 3.4 Option Chain (REST)

| Property | Value |
|---|---|
| Endpoint | `/optionchain` |
| Expiry list | `/optionchain/expirylist` (requires `UnderlyingScrip`, `UnderlyingSeg`) |
| Parameters | `UnderlyingScrip` (int, security id), `UnderlyingSeg` (string, exchange segment), `Expiry` (string, `YYYY-MM-DD`) |
| **Rate limit** | **One unique request every 3 seconds — total, not per underlying.** Documented rationale: OI updates more slowly than price |
| Response, per strike | Greeks (**delta, theta, gamma, vega**), implied volatility, last price, average price, bid/ask, open interest, volume, previous-day data, security identifiers — for both CE and PE |

**This rate limit is the single most consequential constraint in the entire system.** A chain screen driven by this endpoint refreshes at best every 3 seconds for one underlying; watching four underlyings means each refreshes every 12 seconds. That is unusable for options trading. The architectural response is in §11.

### 3.5 Historical data (REST)

**Daily:**

| Property | Value |
|---|---|
| Endpoint | `/charts/historical` |
| Interval | Daily (EOD) only |
| Depth | Since the instrument's inception |
| Instruments | Equities, futures, options (via `instrument` + `exchangeSegment`) |
| Required params | `securityId`, `exchangeSegment`, `instrument` |
| Response | open, high, low, close, volume, timestamp, optional open interest |

**Intraday:**

| Property | Value |
|---|---|
| Endpoint | `/charts/intraday` |
| Intervals | 1, 5, 15, 25, 60 minutes |
| Depth | Up to 5 years |
| **Max range per call** | **90 days** |
| Instruments | All active instruments, all segments |

Documentation explicitly recommends storing intraday data locally due to volume — which is what the warehouse does.

### 3.6 Expired options data (REST)

| Property | Value |
|---|---|
| Endpoint | `POST /charts/rollingoption` |
| Depth | 5 years of expired-contract data |
| Granularity | Minute-level |
| Intervals | 1, 5, 15, 25, 60 minutes |
| **Max range per call** | **30 days** |
| **Strike coverage** | **ATM ±10 strikes for index options; ATM ±3 for stock options** |
| Parameters | Exchange segment (`NSE_FNO`), security id, instrument type, expiry code, expiry flag (`WEEK`/`MONTH`), strike selection, option type (`CALL`/`PUT`) |
| Response fields | `open`, `high`, `low`, `close`, `volume`, `iv`, `oi`, `spot`, `strike`, `timestamp` |

**Two consequences:**
1. On NIFTY with 50-point strikes, ATM±10 is roughly ±500 points from spot. Confirmed sufficient — strategies are near-ATM. The engine reports `strike_unavailable` rather than silently substituting a nearby strike.
2. **No bid/ask is returned.** Option backtest fills therefore cannot model spread-crossing and must use a premium-percentage slippage model, calibrated later against real paper-trading fills.

### 3.7 Instrument master

| File | URL |
|---|---|
| Compact | `https://images.dhan.co/api-data/api-scrip-master.csv` |
| Detailed | `https://images.dhan.co/api-data/api-scrip-master-detailed.csv` |

Detailed version includes exchange/segment identifiers, security classifications, lot size, tick size, symbol names, expiry dates, strike prices, option types, bracket/cover order margins and ranges, surveillance flags, margin requirements, MTF leverage. Update frequency is not documented — synced daily.

### 3.8 Codes and enumerations

**Exchange segments:**

| Code | Value | Meaning |
|---|---|---|
| `IDX_I` | 0 | Index |
| `NSE_EQ` | 1 | NSE Equity Cash |
| `NSE_FNO` | 2 | NSE Futures & Options |
| `NSE_CURRENCY` | 3 | NSE Currency |
| `BSE_EQ` | 4 | BSE Equity Cash |
| `MCX_COMM` | 5 | MCX Commodity |
| `BSE_CURRENCY` | 7 | BSE Currency |
| `BSE_FNO` | 8 | BSE Futures & Options |

**Instrument types:** `INDEX`, `FUTIDX`, `OPTIDX`, `EQUITY`, `FUTSTK`, `OPTSTK`, `FUTCOM`, `OPTFUT`, `FUTCUR`, `OPTCUR`

**Product types:** `CNC` (cash & carry, equity delivery), `INTRADAY`, `MARGIN` (F&O carry forward), `CO` (cover order), `BO` (bracket order)

**Order statuses:** `TRANSIT`, `PENDING`, `CLOSED`, `TRIGGERED`, `REJECTED`, `CANCELLED`, `PART_TRADED`, `TRADED`

### 3.9 Order APIs

Available: Orders, Super Order (entry + target + stop-loss in one), Forever Order (GTT), Conditional Trigger, Portfolio and Positions, EDIS, Trader's Control, Funds & Margin, Statement, Postback, Live Order Update (WebSocket).

### 3.10 UNVERIFIED — rate limits

The DhanHQ rate-limit documentation page did not resolve during research (404 at both `/docs/v2/rate-limit/` and `/docs/v2/rate-limits/`). Per-second, per-minute, per-hour and per-day limits for Order / Data / Quote / Non-Trading API classes are therefore **not confirmed**.

**Resolution:** the first task of feature F0.6 is to locate the current published limits and populate `config/dhan_limits.yaml`. Until then, conservative defaults apply. Because every Dhan call routes through one central limiter, correcting these is a configuration change, not a code change.

Known exception: the Option Chain limit of 1 request / 3 seconds **is** confirmed.

### 3.11 Data Dhan does not provide

| Missing | Needed for | Source | Fragility |
|---|---|---|---|
| Index constituent lists | Sectoral watchlists, heatmap, index-weighted views | NSE archives CSV: `https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv`, `ind_niftybanklist.csv`, `ind_niftyitlist.csv`, etc. | **High.** NSE blocks bare HTTP clients — requires browser-like headers and a cookie bootstrap from the nseindia.com homepage. Mitigated by a committed JSON snapshot fallback and a manual override file; degrades to stale data with a warning rather than breaking |
| Fundamental data | P/E, ROE, growth screening | screener.in scraping, NSE/BSE filings | **Very high**, and legally grey. Out of scope |

### 3.12 Codex — verified facts for development and the later builder

| Fact | Source | Consequence |
|---|---|---|
| Codex works against a local repository, can edit files and run installed tools, and supports interactive work plus repeatable `codex exec` workflows | Official Codex CLI documentation | VS Code Codex is the supervised development workflow; `codex exec` is considered only for the stable Epic 11 automation layer |
| The VS Code extension uses open files, selections and repository context, and shows focused diffs for review | Official Codex IDE documentation | One feature is implemented in one focused chat/branch with an explicit diff review before merge |
| Codex reads `AGENTS.md` before work and supports project-specific instruction layering | Official `AGENTS.md` documentation | Repository safety, test commands, protected paths and completion-report rules live in `AGENTS.md` |
| The IDE and CLI share user and project `.codex/config.toml` layers; project configuration loads only for a trusted project | Official Codex configuration documentation | Keep personal defaults outside the repo and only narrow, reviewed project overrides inside `F:\ShreeNexa\.codex\config.toml` |
| GPT-5.6 Sol is the recommended complex-work model; Terra is the everyday workhorse; Luna suits clear repeatable tasks | Official Codex model documentation | Use Sol High/Extra High for architecture, numerical finance, concurrency and risk; use Sol Medium or Terra for scoped implementation; use Luna only for mechanical work |
| Higher reasoning can improve complex results but costs more time and usage; Medium is the default starting point | Official Codex model documentation | Do not use maximum reasoning by default; increase it only when the feature's risk or complexity justifies it |
| Authentication, plan availability, usage reporting and non-interactive output formats can change | Product boundary | Epic 11 verifies and pins the supported Codex version and interface at implementation time; no undocumented flags are embedded now |
| A ChatGPT/Codex subscription is not treated as a generic runtime API credential for ShreeNexa | Product boundary | The product's NL→StrategyIR provider remains pluggable and disabled until a separately authorized provider/authentication decision is recorded |

Official references used for this revision: [Codex CLI](https://learn.chatgpt.com/docs/codex/cli), [Codex IDE](https://learn.chatgpt.com/docs/codex/ide), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-basic), and [Codex models](https://learn.chatgpt.com/docs/models).

---

## 4. System architecture

### 4.1 Deployment topology

```
┌────────────────────────────┐          ┌──────────────────────────────────────┐
│  Vercel (free tier)        │          │  AWS Lightsail — Mumbai ap-south-1    │
│                            │  HTTPS   │                                      │
│  React / TS / Vite         │◄────────►│  api      FastAPI: REST + browser WS  │
│  static frontend           │   WSS    │  engine   strategy runner             │
│                            │          │  feedd    Dhan WS consumer            │
└────────────────────────────┘          │  worker   backfill / backtest / screen│
                                        │                                      │
                                        │  Postgres   Redis   DuckDB+Parquet   │
                                        │  Caddy (TLS, blue/green upstream)    │
                                        └──────────────┬───────────────────────┘
                                                       │
                                                       ▼
                                              DhanHQ v2 REST + WebSocket
```

**Why the split is not optional:** Vercel is serverless. It cannot hold a persistent WebSocket connection to Dhan, cannot hold tick state in memory, and cannot run a strategy engine between requests. The frontend is static and belongs on Vercel; everything stateful belongs on a persistent host.

Development runs the entire backend locally on Windows; Lightsail is provisioned last (Epic 13).

### 4.2 The four processes

| Process | Responsibility | Restarts on deploy? |
|---|---|---|
| `api` | FastAPI — REST endpoints, browser WebSocket fan-out, auth | **Yes** |
| `engine` | Strategy runner for paper and live modes | **No** — this is the point |
| `feedd` | Dhan WebSocket consumer, packet parsing, writes to Redis | No |
| `worker` | Backfill jobs, backtests, screener runs, parameter sweeps | No |

**All state lives in Postgres and Redis. No process holds authoritative state in memory.** This is what makes "goes live without affecting live working platform" literally true rather than aspirational, and it cannot be retrofitted — it is Epic 0, feature F0.3.

### 4.3 Storage split and rationale

| Store | Holds | Why this store |
|---|---|---|
| **Postgres** | Watchlists, strategy definitions, indicator definitions, screener rules, paper orders/fills/positions, backtest runs and metrics, instrument master, index constituents, dashboard layouts, build state, audit log | Relational, transactional, low volume. Exactly Postgres's strength |
| **Redis** | Last quote per instrument, live option chain snapshot, browser pub/sub fan-out, Dhan rate-limiter token buckets, job queue, feed health | In-memory, sub-millisecond, native pub/sub. ~200–300 MB for a 25,000-instrument universe |
| **DuckDB over Parquet** | All historical bars — daily, intraday, expired options | Columnar and vectorised. 5 years × 1-minute × ~250 F&O scrips is ~120 million rows; options history multiplies that. Row-oriented Postgres makes those scans slow and the indexes huge. DuckDB is serverless, MIT-licensed, and far lighter on RAM — which matters on a 2GB instance |

**Considered and rejected:** TimescaleDB (free community edition, hypertables + ~90% compression, keeps everything in one database) — simpler to operate and back up, but measurably slower on the analytical scans that dominate backtesting, and hungrier for RAM. Revisit only if operational simplicity outweighs backtest speed.

### 4.4 Directory layout

```
ShreeNexa/
├── backend/
│   ├── app/
│   │   ├── main.py                  FastAPI application
│   │   ├── config.py                pydantic-settings, env loading
│   │   ├── dhan/
│   │   │   ├── client.py            REST wrapper, typed responses, auth headers
│   │   │   ├── ratelimit.py         Redis token buckets, one per endpoint class
│   │   │   ├── feed.py              Live Market Feed WS consumer, binary parser
│   │   │   ├── depth.py             20-level depth WS
│   │   │   ├── orders.py            orders / super / forever          [PROTECTED]
│   │   │   └── instruments.py       scrip master ingest
│   │   ├── marketdata/
│   │   │   ├── store.py             DuckDB/Parquet bar store
│   │   │   ├── backfill.py          daily / intraday / rollingoption downloaders
│   │   │   ├── resample.py          1m → 3/5/15/30/60/D/W/M
│   │   │   ├── calendars.py         per-segment sessions + holidays
│   │   │   └── universe.py          index constituent ingest
│   │   ├── analytics/
│   │   │   ├── greeks.py            Black-76 pricer, IV solver
│   │   │   ├── calibrate.py         reconciliation against Dhan's chain
│   │   │   └── indicators/          TA primitives (vector + incremental)
│   │   ├── ir/
│   │   │   ├── schema.py            Pydantic node types, JSON Schema export
│   │   │   ├── compile.py           IR → executable form
│   │   │   ├── eval_vector.py       vectorised evaluator
│   │   │   └── eval_stream.py       incremental evaluator
│   │   ├── engine/
│   │   │   ├── core.py              event loop
│   │   │   ├── clock.py             SimClock | RealClock
│   │   │   ├── datasource.py        HistoricalSource | LiveSource
│   │   │   ├── broker.py            SimBroker | PaperBroker | DhanBroker [PROTECTED]
│   │   │   ├── portfolio.py         positions, MTM, margin
│   │   │   └── risk.py              kill switch, caps, guards        [PROTECTED]
│   │   ├── backtest/
│   │   │   ├── runner.py
│   │   │   ├── metrics.py           pluggable metric registry
│   │   │   └── optimize.py          parameter sweep, walk-forward
│   │   ├── compose/                 portfolio allocation, signal composition, regime
│   │   ├── screener/                runner, scheduler
│   │   ├── builders/                option_strategy, stock_strategy
│   │   ├── investing/               holdings, xirr, allocation, rebalance, sip
│   │   ├── ai/
│   │   │   ├── provider.py          Disabled/Mock | approved API provider
│   │   │   ├── strategy_gen.py      NL → StrategyIR
│   │   │   ├── feature_pipeline.py  request → spec → build → gate → sandbox → promote
│   │   │   ├── worktree.py
│   │   │   └── gates.py
│   │   ├── api/                     REST routers
│   │   ├── ws/                      browser WebSocket fan-out
│   │   └── cli/                     management commands
│   ├── alembic/                     migrations
│   └── tests/
│       ├── unit/  reference/  property/  integration/  acceptance/
│       ├── cassettes/               recorded Dhan responses
│       └── parity/                  IR parity suite                  [PROTECTED]
├── frontend/
│   └── src/
│       ├── widgets/                 self-registering panels
│       ├── layout/                  grid engine, saved layouts, presets
│       ├── lib/                     api client, ws client, udf-datafeed
│       └── routes/
├── build/                           the orchestrator (see §15)
├── infra/
│   ├── docker-compose.yml           postgres + redis for local dev
│   ├── caddy/                       TLS + blue/green upstream
│   └── lightsail/                   provisioning scripts, systemd units
├── config/
│   ├── dhan_limits.yaml             rate limits — populated in F0.6
│   ├── costs.yaml                   brokerage/STT/GST rates with effective-date ranges
│   └── metric_grades.yaml           grading bands + deployment gates (§10.4)
├── data/                            Parquet warehouse (gitignored)
├── .codex/
│   └── config.toml                  narrow, reviewed project overrides
├── docs/
│   ├── architecture/                module map, invariants, ADRs
│   └── qa/                          gates, fixtures, acceptance reports
└── AGENTS.md                        concise repository instructions
```

`[PROTECTED]` marks paths the AI builder may never edit — see §14.3.

---

## 5. Data model

### 5.1 Postgres schema

Indicative DDL; column types and indexes are finalised during implementation.

```sql
-- Instruments -------------------------------------------------------------
CREATE TABLE instrument (
    security_id      TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,          -- NSE_EQ, NSE_FNO, ...
    instrument_type  TEXT NOT NULL,          -- EQUITY, OPTIDX, FUTSTK, ...
    symbol           TEXT NOT NULL,
    trading_symbol   TEXT NOT NULL,
    isin             TEXT,
    lot_size         INTEGER,
    tick_size        NUMERIC(12,4),
    expiry_date      DATE,                   -- derivatives only
    strike_price     NUMERIC(14,4),          -- options only
    option_type      TEXT,                   -- CE | PE
    underlying_id    TEXT,                   -- links option/future to underlying
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    raw              JSONB,                  -- full scrip-master row
    synced_at        TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (exchange_segment, security_id)
);
CREATE INDEX ON instrument (symbol);
CREATE INDEX ON instrument (underlying_id, expiry_date, strike_price);

-- Index membership --------------------------------------------------------
CREATE TABLE index_constituent (
    index_name  TEXT NOT NULL,               -- 'NIFTY BANK'
    symbol      TEXT NOT NULL,
    weight      NUMERIC(8,4),
    sector      TEXT,
    valid_from  DATE NOT NULL,
    valid_to    DATE,                        -- NULL means currently effective
    source_date DATE NOT NULL,               -- date of the source snapshot
    source      TEXT NOT NULL,               -- 'nse_archive' | 'fallback' | 'manual'
    PRIMARY KEY (index_name, symbol, valid_from),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX ON index_constituent (index_name, valid_from, valid_to);

-- Watchlists --------------------------------------------------------------
CREATE TABLE watchlist (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,               -- manual | fno | sector | screener
    config      JSONB,                       -- sector name, screener ref, ...
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE watchlist_item (
    watchlist_id     BIGINT REFERENCES watchlist(id) ON DELETE CASCADE,
    exchange_segment TEXT NOT NULL,
    security_id      TEXT NOT NULL,
    sort_order       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (watchlist_id, exchange_segment, security_id)
);

-- Indicators and strategies -----------------------------------------------
CREATE TABLE indicator_def (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    formula     TEXT NOT NULL,               -- formula language source
    params      JSONB NOT NULL DEFAULT '{}',
    plot_config JSONB,                       -- pane, colour, style
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE strategy (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    ir          JSONB NOT NULL,              -- the StrategyIR document
    ir_version  INTEGER NOT NULL,
    kind        TEXT NOT NULL,               -- stock | option | investing | composite
    horizon     TEXT NOT NULL,               -- intraday | swing | positional | investing
                                             -- selects the grading band profile (§10.4.3)
    strategy_type TEXT NOT NULL,             -- trend_following | swing_trading
                                             -- | mean_reversion | option_selling | other
                                             -- selects the win-rate band only (§10.4.4)
    origin      TEXT NOT NULL,               -- manual | ai_generated
    status      TEXT NOT NULL,               -- draft | backtested | paper | live | retired
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE strategy_version (               -- full history, never overwrite
    strategy_id BIGINT REFERENCES strategy(id) ON DELETE CASCADE,
    version     INTEGER NOT NULL,
    ir          JSONB NOT NULL,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (strategy_id, version)
);

-- Screener ----------------------------------------------------------------
CREATE TABLE screener_def (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    conditions JSONB NOT NULL,               -- same node types as StrategyIR.signals
    universe   JSONB NOT NULL,
    schedule   TEXT,                         -- cron expression, nullable
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE screener_run (
    id          BIGSERIAL PRIMARY KEY,
    screener_id BIGINT REFERENCES screener_def(id) ON DELETE CASCADE,
    as_of       DATE NOT NULL,
    results     JSONB NOT NULL,              -- [{symbol, values...}]
    ran_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Backtests ---------------------------------------------------------------
CREATE TABLE backtest_run (
    id            BIGSERIAL PRIMARY KEY,
    strategy_id   BIGINT REFERENCES strategy(id),
    ir_snapshot   JSONB NOT NULL,            -- exact IR used, for reproducibility
    params        JSONB NOT NULL,
    date_from     DATE NOT NULL,
    date_to       DATE NOT NULL,
    capital       NUMERIC(18,2) NOT NULL,
    cost_model    JSONB NOT NULL,
    seed          BIGINT NOT NULL,           -- determinism (gate G3)
    status        TEXT NOT NULL,             -- queued | running | done | failed
    engine_commit TEXT NOT NULL,             -- git sha, for reproducibility
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE backtest_metric (
    run_id BIGINT REFERENCES backtest_run(id) ON DELETE CASCADE,
    name   TEXT NOT NULL,
    value  NUMERIC(20,8),
    grade  TEXT,                             -- Reject|Weak|Acceptable|Good|Excellent (§10.4)
    band   TEXT,                             -- human-readable band the value fell into
    detail JSONB,                            -- curves, buckets, breakdowns
    PRIMARY KEY (run_id, name)
);

CREATE TABLE backtest_scorecard (            -- one row per run: the overall verdict
    run_id       BIGINT PRIMARY KEY REFERENCES backtest_run(id) ON DELETE CASCADE,
    verdict      TEXT NOT NULL,              -- REJECT | INVESTIGATE | INSUFFICIENT_DATA
                                             -- | Weak | Acceptable | Good | Excellent
    flags        JSONB NOT NULL DEFAULT '[]',-- implausibility flags (§10.4.5)
    profile      TEXT NOT NULL,              -- horizon profile used: intraday|swing|
                                             -- positional|investing
    config_version INTEGER NOT NULL,         -- metric_grades.yaml version used; drives the
                                             -- "graded under v3 (current: v4)" notice (§10.4.7)
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE backtest_trade (
    run_id       BIGINT REFERENCES backtest_run(id) ON DELETE CASCADE,
    seq          INTEGER NOT NULL,
    leg          INTEGER NOT NULL DEFAULT 0, -- multi-leg option trades
    security_id  TEXT NOT NULL,
    side         TEXT NOT NULL,              -- BUY | SELL
    qty          INTEGER NOT NULL,
    entry_ts     TIMESTAMPTZ NOT NULL,
    entry_price  NUMERIC(14,4) NOT NULL,
    exit_ts      TIMESTAMPTZ,
    exit_price   NUMERIC(14,4),
    pnl          NUMERIC(18,4),
    costs        NUMERIC(18,4),
    mae          NUMERIC(18,4),              -- max adverse excursion
    mfe          NUMERIC(18,4),              -- max favourable excursion
    exit_reason  TEXT,
    PRIMARY KEY (run_id, seq, leg)
);

-- Paper and live trading --------------------------------------------------
CREATE TABLE deployment (
    id           BIGSERIAL PRIMARY KEY,
    strategy_id  BIGINT REFERENCES strategy(id),
    mode         TEXT NOT NULL,              -- paper | live
    capital      NUMERIC(18,2) NOT NULL,
    max_loss     NUMERIC(18,2),
    status       TEXT NOT NULL,              -- running | paused | stopped
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    stopped_at   TIMESTAMPTZ
);
CREATE TABLE trade_order (
    id            BIGSERIAL PRIMARY KEY,
    deployment_id BIGINT REFERENCES deployment(id),
    mode          TEXT NOT NULL,             -- paper | live
    broker_ref    TEXT,                      -- Dhan order id, live only
    security_id   TEXT NOT NULL,
    side          TEXT NOT NULL,
    qty           INTEGER NOT NULL,
    order_type    TEXT NOT NULL,
    product       TEXT NOT NULL,
    price         NUMERIC(14,4),
    trigger_price NUMERIC(14,4),
    status        TEXT NOT NULL,
    placed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason        JSONB                      -- which rule fired; audit trail
);
CREATE TABLE fill (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT REFERENCES trade_order(id),
    qty         INTEGER NOT NULL,
    price       NUMERIC(14,4) NOT NULL,
    costs       NUMERIC(14,4) NOT NULL,
    filled_at   TIMESTAMPTZ NOT NULL
);

-- Daily P&L series --------------------------------------------------------
-- ONE table serving backtest, paper AND live, so the calendar and the
-- monthly/yearly return views are identical in all three modes (§10.8).
CREATE TABLE daily_pnl (
    source_kind  TEXT NOT NULL,              -- backtest | paper | live
    source_id    BIGINT NOT NULL,            -- backtest_run.id or deployment.id
    strategy_id  BIGINT REFERENCES strategy(id),
    trade_date   DATE NOT NULL,
    realized     NUMERIC(18,4) NOT NULL DEFAULT 0,
    unrealized   NUMERIC(18,4) NOT NULL DEFAULT 0,  -- change in open-position MTM
    costs        NUMERIC(18,4) NOT NULL DEFAULT 0,
    net          NUMERIC(18,4) NOT NULL,     -- realized + unrealized - costs
    trades       INTEGER NOT NULL DEFAULT 0,
    wins         INTEGER NOT NULL DEFAULT 0,
    losses       INTEGER NOT NULL DEFAULT 0,
    cashflow     NUMERIC(18,2) NOT NULL DEFAULT 0,  -- SIP / withdrawal; drives TWR
    equity_open  NUMERIC(18,2) NOT NULL,
    equity_close NUMERIC(18,2) NOT NULL,
    return_pct   NUMERIC(12,6) NOT NULL,     -- time-weighted, cashflow-adjusted
    PRIMARY KEY (source_kind, source_id, trade_date)
);
CREATE INDEX ON daily_pnl (strategy_id, trade_date);

-- Dashboards --------------------------------------------------------------
CREATE TABLE dashboard (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    preset_key TEXT,                         -- overview | market | strategy | ...
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE dashboard_widget (
    id           BIGSERIAL PRIMARY KEY,
    dashboard_id BIGINT REFERENCES dashboard(id) ON DELETE CASCADE,
    widget_type  TEXT NOT NULL,              -- registry key
    grid_x       INTEGER NOT NULL,
    grid_y       INTEGER NOT NULL,
    grid_w       INTEGER NOT NULL,
    grid_h       INTEGER NOT NULL,
    settings     JSONB NOT NULL DEFAULT '{}'
);

-- Audit -------------------------------------------------------------------
CREATE TABLE audit_log (
    id       BIGSERIAL PRIMARY KEY,
    ts       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor    TEXT NOT NULL,                  -- user | engine | ai_builder
    action   TEXT NOT NULL,
    subject  TEXT,
    detail   JSONB
);
```

### 5.2 Parquet warehouse layout

```
data/bars/
  segment=NSE_EQ/instrument=1333/timeframe=1m/year=2024/part-000.parquet
  segment=NSE_EQ/instrument=1333/timeframe=1d/all.parquet
  segment=IDX_I/instrument=13/timeframe=1m/year=2024/part-000.parquet
data/options/
  underlying=NIFTY/expiry_flag=WEEK/expiry=2024-06-27/strike_offset=+2/type=CE/part-000.parquet
```

Bar schema: `ts` (TIMESTAMP, IST-aware), `open`, `high`, `low`, `close` (DOUBLE), `volume` (BIGINT), `oi` (BIGINT, nullable).
Options add: `iv` (DOUBLE), `spot` (DOUBLE), `strike` (DOUBLE).

Rationale for partitioning by year: keeps individual Parquet files in the tens of megabytes, so DuckDB's partition pruning skips whole years for a date-bounded backtest.

**Rows are immutable.** Backfill writes new partitions; corrections rewrite a whole partition. This makes gate G3 (determinism) achievable — a backtest over a fixed date range reads byte-identical input every time.

### 5.3 Redis key design

| Key pattern | Type | Contents | TTL |
|---|---|---|---|
| `q:{segment}:{security_id}` | Hash | ltp, ltt, volume, oi, bid, ask, day OHLC | none, overwritten |
| `chain:{underlying}:{expiry}` | Hash | per-strike computed IV + Greeks snapshot | 5 s |
| `depth:{segment}:{security_id}` | Hash | 20-level depth for the focused instrument | 5 s |
| `bar:{segment}:{security_id}:1m` | Hash | in-progress bar being built from ticks | until bar close |
| `rl:{endpoint_class}` | String | rate-limiter token bucket | rolling |
| `sub:conn:{n}` | Set | instruments subscribed on socket n (cap 5,000) | none |
| `pubsub:quotes` | Pub/Sub | fan-out channel to browser WS clients | — |
| `queue:backfill`, `queue:backtest`, `queue:screener` | List | job queues | none |
| `health:feed` | Hash | last packet time, reconnect count, subscribed count | none |

---

## 6. StrategyIR specification

### 6.1 Purpose

The StrategyIR is the single artefact that the screener, backtester, paper engine and live engine all consume. It is a JSON document with a Pydantic schema, versioned, and exportable as JSON Schema (which the AI strategy generator uses to constrain its output).

**Design rule:** anything a strategy needs to express must be representable in the IR. Where it genuinely cannot be, the `CustomPython` node is the escape hatch — but every use of it is flagged, because a Python node cannot be analysed by the look-ahead auditor (gate G2) as rigorously as a declarative node.

### 6.2 Top-level shape

```jsonc
{
  "ir_version": 1,
  "name": "ORB with RSI filter",
  "kind": "stock",                    // stock | option | investing | composite
  "horizon": "swing",                 // REQUIRED — selects the grading band PROFILE (§10.4.3)
                                      // intraday | swing | positional | investing
  "strategy_type": "trend_following", // REQUIRED — selects the WIN-RATE band only (§10.4.4)
                                      // trend_following | swing_trading
                                      // | mean_reversion | option_selling | other
  "universe": { ... },
  "timeframe": "5m",
  "session": { "segment": "NSE_EQ" }, // drives calendar + session bounds
  "indicators": { ... },
  "entries": [ ... ],
  "exits": [ ... ],
  "sizing": { ... },
  "risk": { ... }
}
```

### 6.3 Universe selectors

```jsonc
{ "type": "static",    "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}] }
{ "type": "watchlist", "watchlist_id": 4 }
{ "type": "screener",  "screener_id": 2, "refresh": "daily" }
{ "type": "index",     "index_name": "NIFTY 50" }
{ "type": "option_legs",
  "underlying": {"segment": "IDX_I", "security_id": "13"},
  "expiry_rule": {"type": "weekly", "offset": 0},       // 0 = nearest
  "legs": [
    {"id": "ce", "option_type": "CE", "strike": {"type": "atm", "offset": 0},  "side": "SELL", "lots": 1},
    {"id": "pe", "option_type": "PE", "strike": {"type": "atm", "offset": 0},  "side": "SELL", "lots": 1}
  ]
}
```

Strike selectors: `{"type":"atm","offset":N}`, `{"type":"delta","target":0.25}`, `{"type":"premium","target":120}`, `{"type":"absolute","strike":24000}`.

**Availability rule:** if a resolved strike falls outside Dhan's ATM±10 (index) / ATM±3 (stock) history window, the backtester raises `strike_unavailable` and refuses the run. It never substitutes a nearby strike.

### 6.4 Indicator declarations

```jsonc
"indicators": {
  "rsi14":  { "fn": "RSI",  "params": {"length": 14},  "source": "close" },
  "ema200": { "fn": "EMA",  "params": {"length": 200}, "source": "close" },
  "orh":    { "fn": "OPENING_RANGE_HIGH", "params": {"minutes": 15} },
  "myind":  { "fn": "custom", "indicator_def_id": 7 }
}
```

### 6.5 Signal node types

This is the vocabulary that covers the entry styles described: breakouts of a prior high/low gated by a precondition, time-based triggers, and indicator-based triggers.

| Node | Fields | Meaning |
|---|---|---|
| `PriceLevelBreak` | `level`, `direction`, `after` (optional) | Break of a reference level. `level` ∈ `prior_high(n)`, `prior_low(n)`, `opening_range_high(m)`, `opening_range_low(m)`, `prev_day_high`, `prev_day_low`, `vwap`, `custom(indicator)`. **`after` gates the break on a precondition** — this is *"breaking high/low after meeting certain condition"* |
| `Sequence` | `steps[]`, `within` (bars) | Condition A, then condition B within N bars. Ordered, stateful |
| `TimeWindow` | `from`, `to`, `mode` | `mode` ∈ `clock` (09:20–15:15), `from_open` (minutes since open), `to_close`, `dte` (days to expiry) |
| `IndicatorCompare` | `left`, `op`, `right` | `op` ∈ `>`, `<`, `>=`, `<=`, `==`. Operands are indicator refs, price fields, or constants |
| `CrossOver` / `CrossUnder` | `left`, `right` | Strict crossing on this bar |
| `PctChange` | `source`, `lookback`, `op`, `value` | Percentage move over N bars |
| `And` / `Or` / `Not` | `children[]` | Boolean composition |
| `Persist` | `child`, `bars` | Child must hold true for N consecutive bars |
| `StrategySignal` | `strategy_id`, `signal` | **Signal-level composition** — references another strategy's entry/exit signal |
| `Regime` | `detector`, `state` | Active only in a given regime (§10.6) |
| `CustomPython` | `ref` | Sandboxed escape hatch. Flagged; weaker G2 guarantees |

### 6.6 Worked example

*"Buy when price breaks the 15-minute opening range high, but only if RSI(14) was below 60 and price is above EMA(200), between 09:30 and 14:30. Exit at 2% target, 1% stop, or 15:15."*

```jsonc
{
  "ir_version": 1,
  "name": "ORB long with trend and momentum filter",
  "kind": "stock",
  "universe": { "type": "screener", "screener_id": 2, "refresh": "daily" },
  "timeframe": "5m",
  "session": { "segment": "NSE_EQ" },
  "indicators": {
    "rsi14":  { "fn": "RSI", "params": {"length": 14}, "source": "close" },
    "ema200": { "fn": "EMA", "params": {"length": 200}, "source": "close" },
    "orh":    { "fn": "OPENING_RANGE_HIGH", "params": {"minutes": 15} }
  },
  "entries": [{
    "id": "long",
    "side": "BUY",
    "when": {
      "node": "And",
      "children": [
        { "node": "TimeWindow", "mode": "clock", "from": "09:30", "to": "14:30" },
        { "node": "PriceLevelBreak",
          "level": {"ref": "orh"},
          "direction": "above",
          "after": {
            "node": "And",
            "children": [
              { "node": "IndicatorCompare", "left": {"ref": "rsi14"},  "op": "<", "right": {"const": 60} },
              { "node": "IndicatorCompare", "left": {"field": "close"}, "op": ">", "right": {"ref": "ema200"} }
            ]
          }
        }
      ]
    }
  }],
  "exits": [
    { "id": "tp",    "type": "target",     "pct": 2.0 },
    { "id": "sl",    "type": "stop",       "pct": 1.0 },
    { "id": "eod",   "type": "time",       "at": "15:15" }
  ],
  "sizing": { "type": "risk_pct", "risk_pct": 1.0, "stop_ref": "sl" },
  "risk":   { "max_positions": 5, "max_daily_loss_pct": 3.0 }
}
```

### 6.7 Sizing and risk

**Sizing:** `fixed_qty`, `fixed_value`, `pct_capital`, `risk_pct` (position sized so the stop equals N% of capital), `lots` (derivatives), `kelly_fraction` (capped).

**Risk (strategy level):** `max_positions`, `max_daily_loss_pct`, `max_daily_loss_abs`, `max_position_value_pct`, `no_trade_windows[]`, `max_trades_per_day`.

Strategy-level risk is advisory in backtest and enforced in paper/live. The **account-level** risk layer in `engine/risk.py` is separate, protected, and cannot be overridden by any strategy.

### 6.8 Versioning

`ir_version` is an integer. A migration function converts version N to N+1. Every `backtest_run` stores an `ir_snapshot` plus the `engine_commit` git SHA, so any historical result is exactly reproducible even after schema evolution.

---

## 7. Execution engine

### 7.1 The adapter table

One engine, three modes. Strategy code never changes between them.

| | Clock | DataSource | Broker |
|---|---|---|---|
| **Backtest** | `SimClock` — advances through bars | `HistoricalSource` — Parquet replay | `SimBroker` — modelled fills |
| **Paper / forward** | `RealClock` | `LiveSource` — Redis ← Dhan feed | `PaperBroker` — live prices, simulated fills |
| **Live** | `RealClock` | `LiveSource` | `DhanBroker` — real orders, behind the risk layer |

### 7.2 Event loop

```
for each clock tick:
    bars   = datasource.advance(now)
    state  = evaluator.update(bars)          # incremental in paper/live
    signals= rules.evaluate(state)
    orders = sizing.apply(signals, portfolio)
    orders = risk.filter(orders, portfolio)  # PROTECTED — never bypassed
    fills  = broker.submit(orders)
    portfolio.apply(fills)
    persist(orders, fills, portfolio)        # Postgres — survives restart
```

`risk.filter` sits on the only path to any broker. Gate G4 in §16 includes an exhaustive test that no code path reaches `DhanBroker` without traversing it.

### 7.3 Fill models

| Model | Behaviour | Use |
|---|---|---|
| `next_bar_open` | Fill at the next bar's open | Conservative default for bar strategies |
| `close` | Fill at signal bar's close | Optimistic; flagged in reports |
| `slippage_ticks` | Reference price ± N ticks | Liquid equity and futures |
| `slippage_pct` | Reference price ± N% | **Options** — required, since `rollingoption` has no bid/ask |
| `spread_cross` | Cross the recorded bid/ask | Live/paper only, where real depth exists |

Invariant enforced by property test: **no fill price ever falls outside the bar's high/low range.**

### 7.4 Indian cost model

Applied to every simulated and real fill; validated against a real Dhan contract note (feature F3.3).

| Component | Basis |
|---|---|
| Brokerage | Dhan ₹20 per order (or actual slab) |
| STT / CTT | Segment- and side-specific; different for delivery, intraday, futures, options (on premium), and options exercised |
| Exchange transaction charges | Per-segment rate on turnover |
| SEBI turnover fee | Per-crore rate |
| GST | 18% on (brokerage + transaction charges + SEBI fee) |
| Stamp duty | Buy-side only, segment-specific |

Rates live in `config/costs.yaml` with effective-date ranges, so a backtest over 2021–2026 applies the rates that actually applied at each date.

### 7.5 Restart semantics

`engine` writes every order, fill and position change to Postgres before acknowledging it. On restart it reloads open deployments, reconciles positions against the broker (live) or its own book (paper), and resumes. This is what allows `api` to be redeployed underneath a running strategy.

---

## 8. Indicator system

### 8.1 Dual implementation requirement

**Every** primitive ships in two forms:

| Form | Signature | Used by |
|---|---|---|
| Vectorised | `f(arr: np.ndarray, **params) -> np.ndarray` | Backtester, screener |
| Incremental | `class F: def update(self, bar) -> float` | Paper, live |

Gate **G1** asserts the two produce identical output on the same history, per indicator. An indicator without both forms cannot be merged.

### 8.2 Primitive catalogue (~100)

| Family | Members |
|---|---|
| Trend | SMA, EMA, WMA, HMA, DEMA, TEMA, KAMA, VWMA, ALMA, LinReg, Supertrend, PSAR, Ichimoku |
| Momentum | RSI, Stochastic, StochRSI, MACD, CCI, Williams %R, ROC, Momentum, TSI, Ultimate Oscillator, Awesome Oscillator |
| Volatility | ATR, NATR, Bollinger Bands, Keltner, Donchian, Std Dev, Historical Volatility, Chaikin Volatility |
| Volume | OBV, VWAP, Anchored VWAP, MFI, CMF, A/D Line, Volume Profile, Force Index |
| Price structure | Prior N-bar high/low, opening range, prev-day OHLC, pivot points (classic/Fibonacci/Camarilla), gap, fractals, swing high/low |
| Statistical | Correlation, beta, z-score, percentile rank, rolling regression slope, Hurst |
| Options-specific | IV rank, IV percentile, PCR, max pain, ATM IV, IV skew, term structure |
| Session | Minutes from open, minutes to close, days to expiry, day of week, is-expiry-day |

### 8.3 Formula language

A safe, small expression language — deliberately *not* Python, and deliberately *not* Pine.

```
myind = (EMA(close, 20) - EMA(close, 50)) / ATR(14)
signal = RSI(14) < 30 and close > EMA(close, 200)
band   = SMA(close, 20) + 2 * STDDEV(close, 20)
```

Available: all catalogue primitives; OHLCV fields (`open`, `high`, `low`, `close`, `volume`, `oi`); arithmetic and comparison operators; `and`/`or`/`not`; `ref(x, n)` for the value N bars ago; conditional `iif(cond, a, b)`.

**Security:** parsed to an AST and compiled to a restricted evaluator. No attribute access, no imports, no function definitions, no arbitrary calls. Gate: a fuzz suite plus explicit tests that malicious formulas are rejected at parse time rather than at execution time.

**`ref(x, n)` accepts only n ≥ 1** — negative offsets are a parse error. This makes an entire class of look-ahead bugs unrepresentable rather than merely tested for.

---

## 9. Screener

### 9.1 Design

The screener evaluates the **same node types** as `StrategyIR.signals`. This is deliberate: a condition you screen on is a condition you can trade on, with no translation.

Two evaluation contexts:

| Context | Data | Use |
|---|---|---|
| As-of a historical date | Warehouse bars truncated at that date | Backtesting the screener itself; building point-in-time universes |
| Live / latest | Warehouse + live bars | The daily shortlist |

### 9.2 Output routing

A screener run produces a ranked symbol list, which can:
- populate a watchlist,
- become a strategy's `universe` via `{"type":"screener","screener_id":N}`,
- be exported.

This is the loop closure: **screen → strategy universe → backtest → paper → live**, with the screener re-running on its own schedule and the strategy universe following it.

### 9.3 Point-in-time correctness

When a screener runs as-of a past date, it must use only data available on that date — including index membership as it stood then, not as it stands now. Membership is selected with `valid_from <= :date AND (valid_to IS NULL OR valid_to >= :date)`, while `source_date` and `source` preserve provenance. Where historical membership is unavailable, the run is flagged as **survivorship-biased** rather than silently presented as clean.

---

## 10. Backtester and metrics catalogue

### 10.1 Run configuration

Date range, capital, cost model, fill model, slippage, timeframe, seed, and the IR snapshot. Every run records the `engine_commit` git SHA.

### 10.2 Core metrics

| Metric | Definition |
|---|---|
| Total return | (final − initial) / initial |
| **CAGR** | (final/initial)^(365/days) − 1 |
| **Sharpe** | (mean excess return / std dev) × √periods_per_year |
| **Sortino** | (mean excess return / downside deviation) × √periods_per_year |
| **Calmar** | CAGR / |max drawdown| |
| **Max drawdown** | max peak-to-trough decline on the equity curve |
| Max DD duration | longest peak-to-recovery span, in days |
| Recovery factor | net profit / |max drawdown| |
| Ulcer index | RMS of drawdown depth |
| **Win rate** | winning trades / total trades |
| **Profit factor** | gross profit / gross loss |
| **Expectancy** | (win% × avg win) − (loss% × avg loss) |
| Avg win / avg loss | mean P&L of winners / losers |
| **Risk–reward ratio** | avg win / |avg loss| — the realised ratio, not the planned one |
| Largest win / loss | extremes |
| Consecutive wins / losses | longest runs |
| Exposure | % of time with an open position |
| Turnover | traded value / capital |
| **MAE / MFE** | max adverse / favourable excursion per trade |
| Trade count, avg holding period | — |

**Breakdowns:** monthly returns table, day-of-week, hour-of-day, by instrument, by exit reason.
**Curves:** equity, drawdown, rolling Sharpe, underwater plot, trade-P&L distribution.

### 10.3 Options-specific metrics

| Metric | Why it matters |
|---|---|
| Premium captured vs given back | The core economics of option selling |
| Greeks exposure over time | Net delta/gamma/theta/vega through the life of the trade |
| Days-to-expiry buckets | Performance by DTE at entry — reveals whether an edge is a theta effect |
| IV-rank bucketed returns | Whether the edge exists only in high- or low-IV regimes |
| Per-leg attribution | Which leg of a multi-leg structure actually made the money |
| Assignment / expiry-settlement events | — |
| Max margin used, margin efficiency | Return on margin, not just on notional |

The metric registry is **pluggable** — adding a metric is one function plus one registry entry.

### 10.4 Metric grading and the strategy scorecard

#### 10.4.1 Purpose

Raw metrics require interpretation every time you read them. The grading layer converts each metric into a verdict on a five-point scale — **Reject / Weak / Acceptable / Good / Excellent** — so a backtest result is legible at a glance, strategies are sortable and filterable by quality, and deployment can be gated on objective thresholds rather than judgement in the moment.

Bands live in `config/metric_grades.yaml`, versioned and editable. They are **not** hard-coded, because thresholds are a personal judgement that will be tuned with experience.

#### 10.4.2 Two independent axes

Grading depends on two things that are often conflated. They are kept as separate fields because they vary independently:

| Axis | Field | Values | Selects |
|---|---|---|---|
| **Holding horizon** | `horizon` | `intraday` \| `swing` \| `positional` \| `investing` | The **band profile** — CAGR, Sharpe, Calmar, Sortino, max drawdown, drawdown duration, consecutive losses, minimum sample |
| **Trading style** | `strategy_type` | `trend_following` \| `swing_trading` \| `mean_reversion` \| `option_selling` \| `other` | The **win-rate band** only (§10.4.4) |

"Swing" appears on both axes, and that is not a duplication — it is a horizon *and* a style. A swing-horizon mean-reversion strategy carries `horizon: swing` and `strategy_type: mean_reversion`, and each field is read by a different part of the grader.

**Boundary convention:** every band is **inclusive of its lower bound and exclusive of its upper** (`[min, max)`), so a Sharpe of exactly 1.5 grades *Good*, not *Acceptable*. For metrics where lower is better — maximum drawdown, drawdown duration, consecutive losing trades — the comparison is inverted. Enforced by a property test, because off-by-one band logic silently mis-grades every result rather than failing loudly.

#### 10.4.3 Grade bands by horizon

Defaults only. Every number below is editable from the Settings screen (§10.4.7) and every band set records its provenance.

**Provenance key:** `[U]` supplied by you, 2026-08-30 · `[R]` derived from published convention, sourced in the config · `[D]` derived by scaling from an adjacent profile with the reasoning recorded.

**Intraday** — positions closed daily. Higher turnover raises expected CAGR and Sharpe; drawdowns should be tighter because overnight risk is absent.

| Metric | Reject | Weak | Acceptable | Good | Excellent | Src |
|---|---|---|---|---|---|---|
| CAGR | — | <20% | 20–40% | 40–60% | >60% | D |
| Sharpe | — | <1.5 | 1.5–2.5 | 2.5–3.5 | >3.5 | R |
| Sortino | — | <2 | 2–3 | 3–4.5 | >4.5 | D |
| Calmar | — | <1.5 | 1.5–3 | 3–5 | >5 | R |
| Max drawdown | — | >15% | 10–15% | 5–10% | <5% | R |
| Drawdown duration | — | >3 mo | 1–3 mo | 2 wk–1 mo | <2 wk | D |
| Profit factor | <1.0 | 1.0–1.15 | 1.15–1.3 | 1.3–1.6 | >1.6 | D |
| Expectancy (R) | ≤0 | 0–0.05 | 0.05–0.10 | 0.10–0.20 | >0.20 | R |
| Recovery factor | — | <3 | 3–6 | 6–10 | >10 | D |
| Risk–reward | — | <0.8 | 0.8–1.2 | 1.2–1.8 | >1.8 | D |
| Consecutive losses | — | >25 | 15–25 | 8–15 | <8 | D |
| Min sample | — | — | — | — | — | 200 trades |

**Swing** — days to a few weeks. Closest to your supplied table; published guidance puts 10–20% drawdown as "good, typical of well-managed swing trading".

| Metric | Reject | Weak | Acceptable | Good | Excellent | Src |
|---|---|---|---|---|---|---|
| CAGR | — | <15% | 15–25% | 25–40% | >40% | D |
| Sharpe | — | <1 | 1–1.5 | 1.5–2.2 | >2.2 | U |
| Sortino | — | <1.5 | 1.5–2 | 2–3 | >3 | U |
| Calmar | — | <1 | 1–2 | 2–3 | >3 | U |
| Max drawdown | — | >25% *(Risky)* | 15–25% | 10–15% | <10% | U |
| Drawdown duration | — | >6 mo | 3–6 mo | 1–3 mo | <1 mo | D |
| Profit factor | <1.0 *(loss making)* | 1.0–1.3 | 1.3–1.5 | 1.5–2.0 | >2.0 | U |
| Expectancy (R) | ≤0 | 0–0.10 | 0.10–0.20 | 0.20–0.40 | >0.40 | R |
| Recovery factor | — | <2 | 2–4 | 4–6 | >6 | U |
| Risk–reward | — | <1 | 1.0–1.5 | 1.5–2.0 | >2.0 | U |
| Consecutive losses | — | >15 *(difficult to follow)* | 10–15 | 5–10 | <5 | U |
| Min sample | — | — | — | — | — | 50 trades |

**Positional** — weeks to months. Your supplied table, used as given.

| Metric | Reject | Weak | Acceptable | Good | Excellent | Src |
|---|---|---|---|---|---|---|
| CAGR | — | <12% | 12–20% | 20–30% | >30% | U |
| Sharpe | — | <1 | 1–1.5 | 1.5–2 | >2 | U |
| Sortino | — | <1.5 | 1.5–2 | 2–3 | >3 | U |
| Calmar | — | <1 | 1–2 | 2–3 | >3 | U |
| Max drawdown | — | >30% | 20–30% | 12–20% | <12% | D |
| Drawdown duration | — | >12 mo | 6–12 mo | 3–6 mo | <3 mo | U |
| Profit factor | <1.0 | 1.0–1.3 | 1.3–1.5 | 1.5–2.0 | >2.0 | U |
| Expectancy (R) | ≤0 | 0–0.10 | 0.10–0.25 | 0.25–0.50 | >0.50 | R |
| Recovery factor | — | <2 | 2–4 | 4–6 | >6 | U |
| Risk–reward | — | <1 | 1.0–1.5 | 1.5–2.0 | >2.0 | U |
| Consecutive losses | — | >12 | 8–12 | 4–8 | <4 | D |
| Min sample | — | — | — | — | — | 30 trades |

**Investing** — months to years, benchmark-relative. **These are deliberately far more lenient, and that is the point.** The S&P 500's own long-run Sharpe is roughly 0.5–0.7; the Nifty 50 drew down about 38% in 2020 and roughly 60% in 2008, taking around three years to recover. Judging a long-term portfolio against the swing bands would grade buy-and-hold Nifty as "Weak" on Sharpe and "Risky" on drawdown, which is not a useful verdict — it is a broken yardstick.

| Metric | Reject | Weak | Acceptable | Good | Excellent | Src |
|---|---|---|---|---|---|---|
| CAGR | — | <10% | 10–15% | 15–22% | >22% | R |
| Sharpe | — | <0.5 | 0.5–0.8 | 0.8–1.2 | >1.2 | R |
| Sortino | — | <0.7 | 0.7–1.1 | 1.1–1.6 | >1.6 | D |
| Calmar | — | <0.4 | 0.4–0.7 | 0.7–1.0 | >1.0 | R |
| Max drawdown | — | >45% | 30–45% | 20–30% | <20% | R |
| Drawdown duration | — | >36 mo | 18–36 mo | 9–18 mo | <9 mo | R |
| Profit factor | <1.0 | 1.0–1.2 | 1.2–1.5 | 1.5–2.5 | >2.5 | D |
| Expectancy (R) | ≤0 | 0–0.15 | 0.15–0.35 | 0.35–0.75 | >0.75 | D |
| Recovery factor | — | <1.5 | 1.5–3 | 3–5 | >5 | D |
| Risk–reward | — | <1 | 1.0–1.8 | 1.8–3.0 | >3.0 | D |
| Consecutive losses | — | >8 | 5–8 | 3–5 | <3 | D |
| Min sample | — | — | — | — | — | 20 trades |

Additionally, investing strategies are graded on **alpha versus a configurable benchmark** (Nifty 50 by default) — a 14% CAGR is Acceptable in isolation but poor if the benchmark returned 16% over the same window. Absolute grades alone flatter a strategy in a bull market.

#### 10.4.4 Win rate is graded against strategy type, not an absolute band

Win rate alone is meaningless — 40% is excellent for trend following and alarming for option selling. It is therefore graded relative to the expected range for the strategy's type:

| Strategy type | Typical win rate |
|---|---|
| Trend following | 35% – 50% |
| Swing trading | 45% – 60% |
| Mean reversion | 55% – 70% |
| Option selling | 60% – 85% |

**This requires a schema change:** `StrategyIR` gains a required `strategy_type` field (`trend_following` \| `swing_trading` \| `mean_reversion` \| `option_selling` \| `other`), alongside the separate `horizon` field from §10.4.2. Without `strategy_type` the grader reports win rate **ungraded** rather than guessing.

Grading rule: **within** the range → Acceptable; **above** the range → Good; **materially below** → Weak. Note that a win rate far *above* the expected band is not automatically better — for option selling in particular, a 95% win rate usually means the losses are simply rare and enormous, which is exactly what profit factor and maximum drawdown are there to catch. The scorecard therefore reads win rate alongside those two, never alone.

#### 10.4.5 Implausibility flags — grading works in both directions

A grading system that only flags weakness will happily award five stars to an overfitted backtest. Results that are *too* good are a stronger signal of a bug than of an edge, so the grader carries an upper band above Excellent that raises a **warning**, not praise:

Thresholds are **per horizon**, because a Sharpe of 3 is unremarkable intraday and extraordinary for a long-term portfolio. All are editable.

| Condition | Intraday | Swing | Positional | Investing | Flag | Most likely cause |
|---|---|---|---|---|---|---|
| Sharpe above | 8 | 4 | 3.5 | 2 | `implausible_sharpe` | Look-ahead bias, unrealistic fills, survivorship bias |
| Profit factor above | 2.5 | 5 | 5 | 6 | `implausible_pf` | Too few trades, or costs not applied |
| Win rate above | 95% | 95% | 95% | 95% | `implausible_winrate` | Untaken losses — check exit logic and expiry handling |
| Max DD below … with CAGR above | 1% / 40% | 2% / 30% | 3% / 30% | 5% / 22% | `implausible_risk_return` | Slippage or costs missing |
| Trades fewer than | 200 | 50 | 30 | 20 | `insufficient_sample` | Not statistically meaningful at this sample size |
| Out-of-sample degradation above 50% | ✓ | ✓ | ✓ | ✓ | `overfit_suspected` | Walk-forward far below in-sample |

A flagged result is displayed with its grades **struck through and the warning shown instead**, so an implausible backtest cannot be mistaken for a good one at a glance. This is deliberately the loudest thing on the scorecard.

#### 10.4.6 Configuration format

One file, four profiles, full provenance. This file is the single source of truth — the Settings screen (§10.4.7) reads and writes exactly this.

```yaml
# config/metric_grades.yaml
schema_version: 1
config_version: 1              # bumped on every save; stamped onto each scorecard
scale: [Reject, Weak, Acceptable, Good, Excellent]

defaults: &defaults            # shared across profiles unless overridden
  win_rate:
    graded_by: strategy_type   # NOT by horizon — see §10.4.4
    source: "user_supplied 2026-08-30"
    ranges:
      trend_following: [35, 50]
      swing_trading:   [45, 60]
      mean_reversion:  [55, 70]
      option_selling:  [60, 85]
    implausible_above: 95

profiles:

  positional:                  # your supplied table, used as given
    label: "Positional (weeks to months)"
    min_sample: 30
    metrics:
      cagr:
        higher_is_better: true
        unit: percent
        source: "user_supplied 2026-08-30"
        bands:
          - { lt: 12,            grade: Weak }
          - { gte: 12, lt: 20,   grade: Acceptable }
          - { gte: 20, lt: 30,   grade: Good }
          - { gte: 30,           grade: Excellent }
      max_drawdown:
        higher_is_better: false
        unit: percent
        source: "derived from user_supplied; widened for longer holds"
        bands:
          - { gt: 30,            grade: Weak,   label: Risky }
          - { gt: 20, lte: 30,   grade: Acceptable }
          - { gt: 12, lte: 20,   grade: Good }
          - { lte: 12,           grade: Excellent }
      profit_factor:
        higher_is_better: true
        source: "user_supplied 2026-08-30"
        bands:
          - { lt: 1.0,           grade: Reject, label: "Loss making" }
          - { gte: 1.0, lt: 1.3, grade: Weak }
          - { gte: 1.3, lt: 1.5, grade: Acceptable }
          - { gte: 1.5, lt: 2.0, grade: Good }
          - { gte: 2.0,          grade: Excellent }
        implausible_above: 5.0
      expectancy_r:            # expressed as an R-multiple, not currency
        higher_is_better: true
        unit: R
        source: "researched — user table gave labels but no numbers"
        bands:
          - { lte: 0,             grade: Reject }
          - { gt: 0,   lt: 0.10,  grade: Weak }
          - { gte: 0.10, lt: 0.25, grade: Acceptable }
          - { gte: 0.25, lt: 0.50, grade: Good }
          - { gte: 0.50,          grade: Excellent }
      drawdown_duration_days:
        higher_is_better: false
        unit: days               # displayed in months at 30.44 d/mo
        source: "user_supplied 2026-08-30"
        bands:
          - { gt: 365,            grade: Weak }
          - { gt: 180, lte: 365,  grade: Acceptable }
          - { gt: 90,  lte: 180,  grade: Good }
          - { lte: 90,            grade: Excellent }
      # ... sharpe, sortino, calmar, recovery_factor,
      #     risk_reward, consecutive_losses follow the same shape
    <<: *defaults

  intraday:
    label: "Intraday (closed same day)"
    min_sample: 200
    metrics: { ... }           # per §10.4.3
    <<: *defaults

  swing:
    label: "Swing (days to weeks)"
    min_sample: 50
    metrics: { ... }
    <<: *defaults

  investing:
    label: "Investing (months to years)"
    min_sample: 20
    benchmark: { index: "NIFTY 50", require_alpha: true }
    metrics: { ... }
    <<: *defaults

deployment_gates:
  to_paper: { min_verdict: Acceptable, require_no_implausible: true }
  to_live:  { min_verdict: Good, require_walk_forward: true, require_paper_days: 20 }
```

Notes on the shape:
- **Every band carries a `source`.** Three values are possible: `user_supplied <date>`, `researched — <citation>`, or `derived from <profile>; <reasoning>`. The Settings screen shows this, so six months from now you can tell which numbers were your judgement and which were defaults nobody ever examined.
- **`min_sample` is per profile**, because 30 trades is a reasonable bar for a positional strategy and far too few for an intraday one.
- **Expectancy is an R-multiple** (expected profit per unit of risk taken), not currency — currency expectancy is not comparable across strategies of different size. Your table gave the labels Negative / Around zero / Positive / Strong positive but no numbers; these boundaries are the researched defaults and are fully editable.
- **Only `investing` carries a `benchmark`** block by default; any profile may enable one.

#### 10.4.7 Editing thresholds from Settings

Every number in §10.4.3 through §10.4.6 is editable in the UI — the YAML file is the storage format, not the interface.

A **Grading Thresholds** page provides:

| Capability | Behaviour |
|---|---|
| Profile tabs | Intraday / Swing / Positional / Investing, plus **New profile** cloned from any existing one |
| Per-metric editing | Band boundaries, grade labels, `higher_is_better`, implausibility threshold |
| Live validation | Rejects overlapping or non-contiguous bands on save, so a value can never fall into two grades or none |
| Preview | Shows how your existing backtests would re-grade *before* you commit the change |
| Reset | Per metric, per profile, or all — back to shipped defaults |
| Provenance | Displays each band's source; edits are stamped `user_edited <date>` |
| Import / export | The YAML file, for backup or transfer |
| Weights | Metric weights for the overall verdict (§10.4.8) |
| Gates | Deployment gate thresholds |

**Re-grading is explicit, never silent.** Each scorecard stores the `config_version` it was graded under. Changing thresholds does not rewrite history; the UI marks affected scorecards as *graded under v3 (current: v4)* and offers a **Re-grade all** action. Without this, tightening a threshold would quietly rewrite the past and make old and new results incomparable — the sort of thing that erodes trust in the whole scorecard.

#### 10.4.8 Overall verdict and deployment gating

The scorecard produces a single verdict from the individual grades using explicit rules rather than an opaque weighted average:

1. **Any `Reject` grade → overall REJECT.** Negative expectancy or a profit factor below 1 cannot be offset by a good Sharpe.
2. **Any implausibility flag → overall INVESTIGATE.** Never a pass, never a fail — it means the result is not yet trustworthy either way.
3. **Fewer than the profile's `min_sample` → INSUFFICIENT DATA**, whatever the grades say (200 intraday, 50 swing, 30 positional, 20 investing).
4. Otherwise the verdict is the **weighted median** of grades, with weights configurable and defaulting to: expectancy and profit factor ×2, max drawdown and Calmar ×2, Sharpe and Sortino ×1, the rest ×1. Median rather than mean, so one outlier metric cannot carry a mediocre strategy.

**Deployment gating.** The `deployment_gates` block in §10.4.6 sets the minimum verdict required to promote a strategy to paper and to live. A strategy failing its gate can still be deployed, but only through an explicit override recorded in `audit_log` with your stated reason. The gate is a speed bump with a memory, not a wall — the record means a later post-mortem can tell whether a loss came from a strategy that was never properly validated.

#### 10.4.9 Presentation

Grades are colour-coded on the Backtest and Strategy dashboards, each metric showing its value, grade, and the band it fell into. The strategy list is sortable and filterable by verdict, and the comparison view aligns grades across strategies so a portfolio's weak link is obvious. Implausibility flags render as a banner above the scorecard, not a subtle icon.

### 10.5 Parameter sweep

Grid or random search over declared parameter ranges, executed by `worker`, results stored per combination. Presented as a sensitivity surface, because a parameter set that is a lone spike on that surface is overfitted regardless of its metrics.

### 10.6 Walk-forward

Rolling in-sample optimisation followed by out-of-sample evaluation. Reports in-sample vs out-of-sample degradation — the single most informative number for whether an edge is real.

### 10.7 Strategy composition

**Portfolio level.** N strategies run together, each with a capital allocation. Produces a combined equity curve, a cross-strategy correlation matrix, portfolio-level drawdown, and marginal contribution per strategy. Gate: combined metrics must reconcile with the individual runs.

**Signal level.** The `StrategySignal` node lets one strategy reference another's signal, so strategies compose with `And`/`Or`/`Not` or act as filters on one another.

**Regime switching.** A regime detector classifies the market — trending vs ranging (ADX, efficiency ratio), high vs low IV (IV rank), volatility bands (India VIX) — and the `Regime` node activates a strategy only in a given state.

**Regime models overfit very easily.** Walk-forward validation is therefore *enforced* for any strategy containing a `Regime` node: the backtester refuses to report headline metrics for a regime strategy that has not been walk-forward validated.

---

### 10.8 P&L calendar and period returns

Available identically for **backtest results, paper trading and live** — because all three write to the same `daily_pnl` table (§5.1). One implementation, three modes, exactly as with the metrics module.

#### 10.8.1 The daily P&L calendar

A month grid in the style of Zerodha Console's P&L calendar.

- **One cell per trading day**, showing net P&L in rupees and the day's return as a percentage.
- **Colour-graded by magnitude**, not just sign — a ₹200 day and a ₹20,000 day are visibly different greens, so outlier days stand out without reading numbers.
- **Non-trading days** (weekends, exchange holidays) render inert and greyed, taken from the per-segment calendars in §1.5 so MCX's different holiday set is respected.
- **Days with open positions but no closed trades** show unrealised change, marked with a dot to distinguish MTM movement from realised P&L. Conflating the two makes a calendar lie about when money was actually made.
- **Month header** carries the month total, trading-day count, win/loss day split, best and worst day.
- **Week rows** carry a weekly subtotal in the right margin.

**Click a day → the trade detail table opens below the calendar**, listing every trade on that date: time, instrument, side, quantity, entry and exit price, gross P&L, costs, net P&L, exit reason, and — for options — the leg breakdown. The row links to the chart with entry and exit markers at that timestamp, so a bad day can be inspected rather than merely observed.

Filters: by strategy, by instrument, by segment, and realised-only versus realised-plus-MTM.

#### 10.8.2 Monthly and yearly returns

Shown **per strategy**, and on the portfolio level for combined strategies.

- **Monthly returns matrix** — years as rows, `Jan…Dec` as columns, plus a **YTD** column. Each cell colour-graded. The standard hedge-fund tearsheet layout, and the fastest way to see whether an edge is seasonal or steady.
- **Yearly returns** — bar chart and table with, per year: return %, best and worst month, positive-month count, max drawdown within the year, and — for `investing` strategies — the benchmark's return for the same year alongside the alpha.
- **Rolling returns** — 3, 6 and 12-month rolling windows, which expose consistency in a way calendar-year buckets hide.
- **Lifetime timeline** — where a strategy has been backtested, then paper traded, then run live, the monthly matrix renders all three on **one continuous timeline with the mode changes marked**. This makes the question that actually matters visible at a glance: did live performance resemble the backtest?

#### 10.8.3 Returns must compound, and must be cashflow-adjusted

Two correctness rules, both enforced by property tests, because both are easy to get wrong and produce numbers that look plausible:

1. **Period returns compound; they do not sum.** A month's return is `equity_end / equity_start − 1`, never the sum of daily percentages. Summing overstates gains and understates losses, and the error compounds with volatility.
2. **Cashflows are removed via time-weighted return.** For investing strategies a SIP instalment increases equity without being a gain. Daily return is therefore computed as `(equity_close − cashflow) / equity_open − 1`, and periods chain-link those daily factors. This is the time-weighted return — it measures the *strategy*. XIRR (§10.2, money-weighted) measures *your outcome* including timing of contributions. **Both are shown, labelled distinctly**, because they answer different questions and quoting one for the other is a classic reporting error.

Property tests assert that chain-linked daily returns reproduce the period return to within floating-point tolerance, and that a pure-cashflow day with no market movement yields exactly 0% return.

## 11. Option analytics

### 11.1 The problem restated

The option chain needs LTP, bid/ask, volume, OI, change-in-OI, IV and four Greeks per strike — roughly 80 live contracts for one NIFTY expiry, more across underlyings.

Dhan offers two incompatible routes:

| | Dhan Option Chain REST | Live Market Feed WebSocket |
|---|---|---|
| IV and Greeks | **Provided** | **Not provided** |
| Update rate | **1 request / 3 seconds, total** | Tick-by-tick, no limit |
| Multi-underlying | Effectively impossible | 25,000 instruments |

### 11.2 The hybrid design

**Stream everything, compute locally, calibrate continuously.**

1. `feedd` subscribes to every strike of every underlying you track (a NIFTY chain is ~200 contracts; the budget is 25,000). Prices, volume and OI arrive tick-by-tick.
2. `analytics/greeks.py` computes IV and Greeks locally using **Black-76** — the correct model for Indian index options, which settle against a futures/forward rather than spot.
3. Once every 3 seconds, the chain endpoint is polled for **whichever underlying is currently on screen**. Our values are compared against Dhan's.
4. A calibration routine tunes the convention parameters until they agree; a **drift badge** appears on the chain if they diverge beyond tolerance.

The result is a chain that updates on every tick, for any number of underlyings, with a continuous accuracy check against the broker's own numbers.

### 11.3 Black-76 and the IV solver

Forward-based pricing:

```
d1 = [ln(F/K) + (σ²/2)T] / (σ√T)
d2 = d1 − σ√T
Call = e^(−rT) [F·N(d1) − K·N(d2)]
Put  = e^(−rT) [K·N(−d2) − F·N(−d1)]
```

**Forward F** is taken from the actual futures LTP where a future exists; otherwise a synthetic forward is derived from put-call parity at the ATM strike. Using spot instead of forward is the most common source of Greek mismatches in Indian options and is explicitly avoided.

**IV solve:** Brent's method bracketed on σ ∈ (0.001, 5.0), with a vega guard — near-zero vega (deep ITM/OTM, near expiry) makes IV numerically meaningless, and those strikes are marked `iv_unreliable` rather than reported with a fabricated number.

**Greeks:** delta, gamma, theta (per calendar day), vega (per 1 volatility point), rho — closed form once σ is known.

### 11.4 Convention parameters — the calibration targets

| Parameter | Options | Why it matters |
|---|---|---|
| Underlying | Futures LTP vs synthetic forward vs spot | Largest source of delta mismatch |
| Time to expiry | Calendar days vs trading days; expiry at 15:30 IST | **Largest source of theta mismatch** |
| Risk-free rate | Configurable; MIBOR or T-bill | Small effect on Greeks, larger on deep ITM |
| Day count | 365 vs 252 | Interacts with the above |

Calibration solves for the combination that best reproduces Dhan's published Greeks. **F8.2's acceptance test is explicitly that theta agrees**, because theta is where conventions bite hardest and where a silent mismatch would most distort an option-selling backtest.

### 11.5 Chain analytics

ATM IV, IV rank and IV percentile (computed from warehoused IV history), put-call ratio (OI and volume), max pain, IV skew and smile, term structure across expiries, OI change buckets, and net position Greeks for the strategy builder.

### 11.6 Option strategy builder

Leg construction (any combination of CE/PE, buy/sell, strikes, expiries), payoff diagram at expiry **and at T+n** using current IV, breakevens, max profit and max loss, net Greeks, and margin via Dhan's margin API. Validated against hand-computed payoffs for standard structures — straddle, strangle, iron condor, butterfly, calendar, ratio.

---

## 12. Live data layer

### 12.1 Feed consumer

Binary packet parsing for Ticker, Quote and Full modes. Validated against **captured golden packets** — real packets recorded once and committed as fixtures, so parser regressions are caught without a live market.

### 12.2 Subscription manager

Distributes instruments across 5 sockets, ≤5,000 each, batching subscribe messages at ≤100 instruments. Handles priority (visible widgets first), reconnection with automatic resubscription, and a health record in Redis (last packet time, reconnect count, subscribed count).

Property test: the manager never exceeds 5,000 per connection nor 100 per message, under any sequence of subscribe/unsubscribe operations.

### 12.3 Bar builder

Constructs 1-minute bars from ticks and merges them onto warehouse history so a chart shows continuous data across the live boundary. Acceptance test: bars built from ticks match Dhan's own 1-minute bars for the same session.

Session-aware per segment — an MCX bar at 22:45 is valid; an NSE_EQ bar at 22:45 is not.

### 12.4 Watchlists

Multiple user-defined lists; an F&O watchlist; sector-wise lists derived from index constituents; sectoral index rows that expand to their constituents. Columns configurable (LTP, change, %change, volume, OI, change-in-OI, IV rank, day range position).

### 12.5 Market depth for selected scripts

Driven by the Full Market Depth socket (§3.3), whose real limits allow far more than a single instrument.

| Mode | Coverage | Use |
|---|---|---|
| **20-level** | **Up to 50 scripts per connection** | A **depth watchlist** — pin the scripts you actively trade and see all their order books at once |
| **200-level** | **1 instrument per connection** | The single focused script, subscribed **on demand** when you open the deep book, released when you close it |

**Widgets:**
- **Depth ladder** — bid/ask price, quantity and order count per level for one script, with cumulative quantity, imbalance ratio, and total bid vs ask.
- **Depth watchlist** — a compact multi-script strip showing best bid/ask, spread, top-5 imbalance and total book size for each pinned script, so you can watch 50 books without 50 ladders.
- **Deep book (200-level)** — opened explicitly for one script; shows a connection-cost indicator, since it occupies an entire socket.

**Segment limitation, surfaced honestly in the UI.** Full Market Depth covers **NSE Equity and NSE Derivatives only**. For BSE, MCX and currency the deepest available book is the **5 levels from the regular feed's Full packet**. Those instruments render a 5-level ladder with an explicit note explaining the limit — never an empty 20-level ladder, which would read as a bug rather than a constraint.

Subscriptions are managed by the connection budget manager (§3.3.1), which owns all Dhan sockets and enforces the shared 5-connection ceiling. Opening a sixth connection would silently disconnect the first, so the budget is enforced centrally rather than trusted to call sites.

### 12.6 Heatmap

Two levels: an **index-level** view across all NSE and BSE sectoral indices, and a **constituent** drill-in for one index. Cells sized by index weight or market cap, coloured by percentage change. Sentiment measures: advance/decline ratio, percentage of constituents above previous close, and for index cells the futures basis and OI change.

---

## 13. Frontend: widget registry and layout engine

### 13.1 Why this exists

You stated you will want to rearrange dashboards. Hard-coded dashboard pages would make that a code change every time. So dashboards are **data**.

### 13.2 Widget registry

Every panel self-registers:

```ts
registerWidget({
  type: 'option_chain',
  title: 'Option Chain',
  defaultSize: { w: 8, h: 12 },
  minSize:     { w: 6, h: 8  },
  settingsSchema: z.object({
    underlying: z.string(),
    expiry:     z.string().optional(),
    strikeCount: z.number().default(20),
  }),
  component: OptionChainWidget,
});
```

Consequences: adding a widget requires no change to layout code; the "add widget" palette is generated from the registry; and any feature the AI builder adds becomes a droppable widget automatically.

### 13.3 Layout engine

Draggable, resizable grid. Layouts persist to `dashboard_widget`. Dashboards can be cloned, renamed, reordered, and reset to their shipped preset. Creating a new dashboard is a row in `dashboard`.

### 13.4 Shipped presets

| Preset | Contents |
|---|---|
| **Overview** | Index strip, heatmap, open positions, today's strategy activity, alerts, feed health |
| **Market Terminal** | Option chain, chart, watchlists, **depth ladder + depth watchlist**, order entry |
| **Strategy** | Strategy list, rule builder, indicator builder, deploy controls, **monthly/yearly returns matrix per strategy** |
| **Backtest** | Run configuration, equity and drawdown curves, scorecard, metrics table, trade list, **P&L calendar**, **monthly/yearly returns**, comparison view |
| **Paper Trading** | Live P&L, order book, trade book, positions, **P&L calendar**, **monthly/yearly returns**, divergence report |
| **Investing** | Holdings, allocation, XIRR, dividends, rebalancing signals |
| **AI Builder** | Feature request queue, live build stream, test results, sandbox vs live status, promotion history, **build progress** |

All are editable and resettable.

### 13.5 Charting

**Lightweight Charts** (Apache-2.0, no approval required) driven by a datafeed written in **TradingView's UDF shape**. That shape is the reason approval for the Advanced Charting Library becomes a front-end swap rather than a rewrite — the backend contract is already correct.

Built on top: indicator panes with drag-to-reorder, drawing tools with persistence, multi-timeframe, crosshair sync across charts, and backtest trade markers overlaid on price.

---

## 14. AI layer

### 14.1 Provider abstraction

```python
class AIProvider(Protocol):
    def generate_structured(
        self, prompt: str, *, schema: dict, timeout_s: int
    ) -> AIResult: ...
```

| Implementation | Default | Use |
|---|---:|---|
| `DisabledProvider` | **Yes** | Product works without external AI access and presents a clear disabled state |
| `MockProvider` | Tests | Deterministic fixtures for schema validation and UI acceptance tests |
| Approved API provider adapter | No | Added only after a separate decision records provider, credentials, data handling, rate limits, and cost |

**Development Codex and product runtime AI are separate concerns.** Signing into Codex in VS Code/CLI authorises development work; it is not a credential contract for ShreeNexa's deployed backend. The product must never shell out to a developer's interactive Codex session as its runtime AI provider.

### 14.2 Natural-language strategy generation

```
English description
   → selected schema-capable provider (when explicitly enabled)
   → structured output validated against the Pydantic StrategyIR model
   → rendered in the visual rule builder for your review
   → one click to backtest
```

The provider receives the minimum necessary prompt and no filesystem, shell, broker, deployment, or secret access. Schema output is untrusted until Pydantic validation and domain checks pass; invalid output becomes a visible validation error, never executable strategy state.

**It never auto-deploys.** A generated strategy lands as a `draft`; the user must review it before save and explicitly start a backtest.

### 14.3 The feature-builder pipeline

```
1. REQUEST   You file a feature request in the AI Builder dashboard
2. SPEC      Codex produces a bounded spec (files, approach, tests, risk level)
             → you edit it
3. BUILD     git worktree on feature/<slug>
             supervised Codex in VS Code first; a documented Codex CLI workflow later
4. GATE      pytest + parity suite + look-ahead audit + ruff + mypy
             + frontend typecheck/build, run INSIDE the worktree
             red → retry with filtered failure log, bounded at 3
5. SANDBOX   ── YOUR APPROVAL ──
             separate ports, sandbox_* Postgres schema, separate Redis DB index,
             read-only warehouse, broker HARD-WIRED to PaperBroker
6. PROMOTE   ── YOUR APPROVAL ──
             merge to main; new `api` starts on a second port; health checks pass;
             Caddy flips upstream; old process drains.
             `engine` is never restarted — running strategies continue.
             Rollback = flip the proxy back.
```

Epic 11 is built only after the research and paper platform is stable. Until then, the feature-by-feature VS Code plan is the authoritative workflow. Any later automation must pin and test a supported Codex CLI version and use only documented interfaces available at implementation time.

**Protected paths.** The following may never be edited by an unattended or automated AI run:

```
backend/app/engine/risk.py
backend/app/engine/broker.py
backend/app/dhan/orders.py
backend/tests/parity/
```

Enforcement is layered: narrow Codex/project scope, an explicit protected-path rule, a diff-based denial before commit, and gate G6 before promotion. Configuration is also reviewed because trusted project settings and inherited tooling can broaden what an automated run may do. **Rationale: software that modifies itself must not be able to rewrite its own kill switch.** Protected-path changes are excluded from unattended automation and require a separate, explicitly approved supervised change with independent review.

### 14.4 Sandbox isolation

| Dimension | Isolation |
|---|---|
| Network ports | Separate from live |
| Postgres | `sandbox_*` schema, separate credentials |
| Redis | Separate database index |
| Warehouse | Mounted **read-only** |
| Broker | `PaperBroker` hard-wired — the sandbox has no code path to `DhanBroker` |
| Dhan credentials | Data-API-only token where possible |

Acceptance test F11.6: the sandbox **physically cannot** place a real order.

---

## 15. Build orchestrator

### 15.1 Purpose

Track and execute the **102-feature** manifest without losing progress. Bootstrap and early epics are supervised feature-by-feature in Codex for VS Code. The productised orchestrator is deferred to Epic 11, after research and paper trading are stable; it may then use a tested, documented Codex CLI interface for repeatable bounded tasks.

### 15.2 Layout

```
build/
  manifest.yaml       epics → features → tasks; deps, QA contract, model tier, size
  state.json          per-task status, attempts, commit, gates, timestamps
  prompts/<task>.md   generated brief — auditable and diffable
  logs/<task>.jsonl   structured events when supported; otherwise bounded command logs
  reports/            per-feature QA reports; parked-feature failure writeups
  orchestrate.py      the supervisor
```

### 15.3 Manifest format

```yaml
epics:
  - id: E0
    name: Foundations
    features:
      - id: F0.6
        name: Redis token-bucket rate limiter
        depends_on: [F0.2, F0.5]
        estimate_days: 1.5
        qa: [L3, L4]
        gates: [G3, G4, G5, G6]
        acceptance:
          - "Never exceeds configured rate under 50 concurrent callers"
          - "429 response triggers exponential backoff with jitter"
          - "Every Dhan call site routes through the limiter (enforced by test)"
        tasks:
          - id: F0.6.T1
            name: Populate config/dhan_limits.yaml from published docs
            model: gpt-5.6-terra
            reasoning: medium
            scope: [config/dhan_limits.yaml, backend/tests/]
          - id: F0.6.T2
            name: Token bucket implementation over Redis
            model: gpt-5.6-sol
            reasoning: high
            scope: [backend/app/dhan/ratelimit.py, backend/tests/]
          - id: F0.6.T3
            name: Property tests for rate adherence under concurrency
            model: gpt-5.6-terra
            reasoning: high
            scope: [backend/tests/]
```

### 15.4 State format

```json
{
  "project": { "features_total": 102, "features_done": 0,
               "tasks_total": null, "tasks_done": 0, "started_at": null },
  "tasks": {
    "F0.6.T2": {
      "status": "done",
      "attempts": 1,
      "commit": "a1b2c3d",
      "started_at": "2026-09-01T09:14:02+05:30",
      "finished_at": "2026-09-01T09:41:55+05:30",
      "gates": { "G3": "pass", "G4": "pass", "G5": "pass", "G6": "pass" }
    }
  },
  "parked": [
    { "feature": "F8.2", "reason": "theta mismatch beyond tolerance after 3 attempts",
      "report": "build/reports/F8.2-failure.md" }
  ]
}
```

Statuses: `pending`, `in_progress`, `interrupted`, `qa_failed`, `done`, `parked`.

### 15.5 Task execution

1. Select the next unblocked `pending` task in topological order.
2. Compose a **self-contained brief** — task spec, acceptance criteria, files in scope, QA gates. **Never conversation history.**
3. During Epics 0–10, open the brief in VS Code and run the feature through supervised Codex. In Epic 11, the orchestrator may call `codex exec` using the supported flags and structured-output capabilities verified and pinned at that time; the implementation must not guess undocumented flags.
4. Run the task's QA gates. Green → record the reviewed commit → `done`. Red → append the **filtered** failure output to the brief, retry, bounded at 3.
5. Three failures → write a failure report, mark the feature `parked`, continue with the next unblocked feature.
6. At a **feature boundary**, pause for your review.

### 15.6 Surviving usage limits

Treat explicit availability/rate-limit messages, authentication failures, cancellation, and non-zero exits as interruptions. Mark the task `interrupted`, preserve the brief and filtered log, and stop safely. Resume or relaunch only after the user or the documented interface confirms availability; do not scrape prose for reset times or assume a particular quota window.

Durable state lives in `state.json`, task briefs, reports, and reviewed git commits—not in a conversation. The exact interruption and resumption mechanism is implemented against the Codex CLI version pinned in Epic 11 and is covered by kill/restart acceptance tests.

### 15.7 Token-efficiency measures

Each is itself a build task.

| Lever | Mechanism | Why |
|---|---|---|
| Bounded task context | One feature/task brief with explicit file scope and acceptance criteria | Reduces exploration and makes review meaningful |
| **`AGENTS.md`** | Concise repository invariants, commands, protected paths, and definition of done | Codex reads the repository guidance before work |
| Architecture references | `docs/architecture/` holds ADRs, module map, schemas, and numerical conventions | Stable details stay reviewable without bloating every brief |
| Filtered logs | Preserve failing assertions, stack traces, command, and exit code; omit repetitive passing output | Gives Codex the evidence needed for the next bounded attempt |
| **Model tiering** | GPT-5.6 Sol high/xhigh for architecture, numerical core, security, and risk; Sol/Terra medium/high for routine features; Luna for bounded mechanical work | Match reasoning capacity to risk and complexity |
| Fresh controlled task context | Start from the durable brief and current repository state | Avoid relying on opaque conversation memory |
| Durable state | Manifest, state file, reports, and git commits | Interruptions do not erase progress |

### 15.8 Progress tracking

Rendered from `state.json` two ways — `python -m build status` in the terminal, and the **Build Progress** widget on the AI Builder dashboard.

**Per feature:** tasks done / total, gate status, coverage on touched modules, attempts, current commit, and elapsed time.
**Project-wide:** features done / total weighted by estimate, burndown, parked items needing review, current task, and elapsed time. Usage is recorded only when the supported interface supplies it; no cost or token fields are fabricated.

The harness stays in the product after the build — the same widget tracks AI-built features afterwards, so it is a permanent component rather than discarded scaffolding.

---

## 16. QA standard

### 16.1 Five layers

| | Layer | Meaning here |
|---|---|---|
| **L1** | Unit | Pure functions: indicators, Greeks, metrics, cost model, IR nodes |
| **L2** | **Reference / golden** | The numeric core validated against an **independent** implementation — Greeks vs `py_vollib` *and* vs Dhan's own chain; indicators vs TA-Lib/pandas-ta; metrics vs hand-computed spreadsheet fixtures; the cost model vs a real contract note; feed parsing vs captured golden packets. **You do not unit-test a Sharpe ratio against your own Sharpe ratio** |
| **L3** | **Property-based** (Hypothesis) | Invariants that must hold for all inputs |
| **L4** | Integration | Against **recorded Dhan cassettes** (VCR-style), so tests run offline, deterministically, and never burn API rate limits |
| **L5** | Acceptance | Scripted user-visible behaviour; **Playwright** for UI |

### 16.2 Representative properties (L3)

- Put-call parity holds for computed prices
- Call delta ∈ [0,1]; put delta ∈ [−1,0]; gamma ≥ 0; vega ≥ 0
- Portfolio value = cash + Σ(position × mark) at every step
- Max drawdown ≤ 0; equity curve length = bar count
- `resample(1m → 5m)` preserves total volume; high = max, low = min
- No fill price falls outside its bar's high/low
- Order state machine never skips a state
- The rate limiter never exceeds its configured rate under concurrency
- The subscription manager never exceeds 5,000/connection or 100/message
- Capital allocations across strategies sum to total capital, with no double-spend

### 16.3 Cross-cutting gates

| | Gate | Enforcement |
|---|---|---|
| **G1** | **IR parity** — vectorised and incremental evaluators produce identical signals on the same history | Per indicator and per strategy |
| **G2** | **No look-ahead audit** — replay with data truncated at each bar; signals must be identical | Automated for every strategy and screener. **The single most common reason a good backtest loses money live** |
| **G3** | **Determinism** — same inputs and seed produce byte-identical results | Run twice, diff |
| **G4** | `ruff` + `mypy --strict` + frontend `tsc` + production build | CI |
| **G5** | Coverage floor: **90%** for `analytics/`, `ir/`, `engine/`, `backtest/`; **80%** elsewhere; **70%** UI | CI |
| **G6** | **Protected-path check** — no automated AI run touched `engine/risk.py`, `engine/broker.py`, `dhan/orders.py`, or `tests/parity/` | Codex scope/rule + diff denial + pre-promotion re-check |

### 16.4 Nightly repo-wide checks

Survivorship-bias checks on universe selection; timezone and session correctness across every supported source segment; and, once Epic 9 lands, a paper-vs-backtest reconciliation for the previous session.

### 16.5 The QA contract is written first

Each feature's acceptance criteria are recorded in `manifest.yaml` **before** any code is written for it. Acceptance is therefore defined ahead of implementation rather than negotiated afterwards — which is what stops an unattended build from drifting toward "whatever passed".

---

## 17. Feature manifest

**102 product features across 14 epics.** The manifest tables are authoritative and CI validates their generated count. QA names layers and gates beyond the always-on G3–G6.

### Epic 0 — Foundations (9 features, ~1.7 wk)

| ID | Feature | QA |
|---|---|---|
| F0.1 | Repo, Python 3.14 venv, ruff/mypy/pytest, pre-commit | L5: clean checkout builds and tests green; **lockfile pins resolve to cp314 wheels with no source builds** |
| F0.2 | Docker Compose: Postgres + Redis (WSL2 fallback) | L5: `up` → both reachable, migrations apply |
| F0.3 | **Four-process split** (`api`/`engine`/`feedd`/`worker`) + supervisor | L5: kill `api`, `engine` keeps running and holds state |
| F0.4 | Config, secrets, Dhan token-expiry monitor | L1, L5: expired token surfaces a banner, never a silent failure |
| F0.5 | Dhan REST client, typed | L4 cassettes |
| F0.6 | **Redis token-bucket rate limiter**, all calls routed through it | L3 concurrency; L4: 429 → backoff |
| F0.7 | Instrument master sync across every source segment, typed symbol search | L4, L5: "NIFTY 24000 CE" resolves to the correct security id; source segment count is discovered, not hardcoded |
| F0.8 | Index constituent ingest + committed fallback | L4, L5: NSE unreachable → falls back with staleness warning |
| F0.9 | **Connection budget manager** (§3.3.1) — owns every Dhan socket, enforces the 5-connection ceiling across feed and depth, allocates from a configured split | L3: never opens a sixth connection under any request sequence (a sixth silently kills the first); L5: budget exhaustion degrades gracefully with a clear message, never a silent drop |

### Epic 1 — Historical warehouse (7 features, ~1.5 wk)

| ID | Feature | QA |
|---|---|---|
| F1.1 | DuckDB/Parquet bar store, partitioned | L1, L3 round-trip |
| F1.2 | Daily backfill since inception | L4, L5: NIFTY daily reconciles with Dhan web |
| F1.3 | Intraday 1-min backfill, 90-day resumable windows | L5: kill mid-backfill → resumes with no gaps or duplicates |
| F1.4 | `rollingoption` backfill, 30-day windows | L4, L5: `strike_unavailable` outside ATM±10/±3, never substituted |
| F1.5 | **Per-segment session + holiday calendars** incl. MCX to 23:30 | L2 vs published calendars; L3: no bar outside session |
| F1.6 | Resampling 1m → 3/5/15/30/60/D/W | L3 aggregation invariants; L2 vs pandas |
| F1.7 | Data-quality report: gaps, zero-volume, outliers | L5: seeded corrupt file detected |

**Open item resolved here:** whether Dhan daily history is corporate-action adjusted. If not, a split/bonus adjustment layer is added before any equity backtest is trusted.

### Epic 2 — Indicators, IR, screener (9 features, ~2 wk)

| ID | Feature | QA |
|---|---|---|
| F2.1 | ~100 TA primitives, vectorised | **L2 vs TA-Lib/pandas-ta**, L3 |
| F2.2 | Incremental variant of every primitive | **G1 per indicator**, L3 |
| F2.3 | Formula language + safe evaluator | L1, L3 fuzz; L5: malicious formula rejected at parse time |
| F2.4 | Indicator builder UI + chart plotting | L5 Playwright |
| F2.5 | IR schema (Pydantic + JSON Schema export) | L1, L3 round-trip |
| F2.6 | Vectorised evaluator | L1, **G2** |
| F2.7 | Incremental evaluator | **G1 parity suite — the repo's most important test** |
| F2.8 | Screener runner, as-of any date | **G2**, L5: 3 names hand-verified |
| F2.9 | Screener scheduling + routing to watchlist/universe | L4, L5 |

### Epic 3 — Backtester and analyser (14 features, ~3.5 wk)

| ID | Feature | QA |
|---|---|---|
| F3.1 | Engine core: clock/datasource/broker interfaces | L1, L3 state machine |
| F3.2 | `SimBroker` fills + slippage models | L3: no fill outside bar range; **G2** |
| F3.3 | **Indian cost model** | **L2 vs a real contract note** |
| F3.4 | Stock strategy backtest | L5: buy-and-hold NIFTY reconciles to manual calc |
| F3.5 | Options multi-leg backtest, strike by delta/offset/premium | L2 vs hand-computed straddle |
| F3.6 | Expiry, roll, square-off handling | L3: no position survives expiry unsettled |
| F3.7 | **Core metrics module** | **L2 vs spreadsheet fixtures**, L3 |
| F3.8 | **Options metrics** | L2, L3 |
| F3.9 | Parameter sweep + walk-forward | **G3**, L5 |
| F3.10 | **Metric grading + scorecard + deployment gates** (§10.4) — **four horizon profiles** (intraday/swing/positional/investing), win rate graded separately by `strategy_type`, per-profile implausibility flags, overall verdict, benchmark-alpha grading for investing | **L2 vs a hand-graded fixture set per profile**; L3: bands are inclusive-low/exclusive-high, contiguous, non-overlapping, and correctly inverted for lower-is-better metrics; L5: an overfitted backtest is flagged INVESTIGATE, not Excellent; L5: buy-and-hold Nifty grades sanely under `investing` and poorly under `intraday` |
| F3.12 | **Daily P&L series** (§10.8) — the `daily_pnl` table written identically by backtest, paper and live; realised vs unrealised split; cashflow-adjusted time-weighted daily return | **L2 vs hand-computed fixtures**; **L3: chain-linked daily returns reproduce the period return; a pure-cashflow day with no market move returns exactly 0%**; L3: realised + unrealised − costs = net |
| F3.13 | **P&L calendar widget** (§10.8.1) — month grid, magnitude-graded colouring, per-segment non-trading days, week subtotals, month header stats; **click a day → trade detail table below**, linking to the chart with entry/exit markers | L5 Playwright: click a day, verify trades match the trade book for that date; L5: MCX holidays differ from NSE and render correctly; L5: MTM-only days are visually distinct from realised |
| F3.14 | **Monthly / yearly returns per strategy** (§10.8.2) — year×month matrix with YTD, yearly table with best/worst month and intra-year drawdown, rolling 3/6/12-month returns, benchmark alpha for investing, **continuous backtest→paper→live timeline with mode changes marked** | **L2 vs hand-computed monthly returns**; L3 compounding correctness; L5: a strategy with all three modes renders one continuous timeline |
| F3.11 | **Grading Thresholds settings UI** (§10.4.7) — profile tabs, per-metric band editing, live overlap/contiguity validation, re-grade preview, reset-to-default, provenance display, YAML import/export, explicit versioned re-grading | L5 Playwright: edit a band, preview the re-grade, save, confirm old scorecards are marked stale rather than silently rewritten; L3: invalid band sets are rejected on save |

### Epic 4 — Frontend shell, widgets, charting (8 features, ~2.5 wk)

| ID | Feature | QA |
|---|---|---|
| F4.1 | React/TS/Vite shell, theme, auth stub | L5 |
| F4.2 | **Widget registry** | L1, L5: new widget appears without touching layout code |
| F4.3 | **Layout engine** — drag/resize, save, clone, reset | L5 Playwright: rearrange, reload, persists |
| F4.4 | Seven dashboard presets | L5 |
| F4.5 | UDF-shaped datafeed adapter | L4, L2 vs warehouse |
| F4.6 | Lightweight Charts widget, panes, MTF, crosshair sync | L5 |
| F4.7 | Drawing tools + persistence | L5 |
| F4.8 | Backtest widgets: equity, drawdown, trade markers, metric tables | L5 |

### Epic 5 — AI strategy generator (4 features, ~1 wk)

| ID | Feature | QA |
|---|---|---|
| F5.1 | AI provider abstraction | L4 mocked; L5: disabled-by-default startup, misconfiguration, timeout, and redaction behavior |
| F5.2 | NL → StrategyIR through the selected schema-capable provider | L5: 20 English descriptions produce schema-valid drafts or clear validation errors |
| F5.3 | Generated IR renders in the builder for review | L5: never auto-deploys |
| F5.4 | One-click backtest of a generated strategy | L5 |

### Epic 6 — Composition and regime switching (5 features, ~1.5 wk)

| ID | Feature | QA |
|---|---|---|
| F6.1 | Strategy portfolio: capital allocation | L3: allocations sum, no double-spend |
| F6.2 | Combined equity curve + portfolio drawdown limits | **L2: reconciles with individual runs** |
| F6.3 | Cross-strategy correlation matrix | L2 vs numpy |
| F6.4 | Signal-level composition | G1, G2 |
| F6.5 | Regime detector + switching | **Walk-forward enforced**; G2 |

### Epic 7 — Live data layer (9 features, ~2 wk)

| ID | Feature | QA |
|---|---|---|
| F7.1 | Feed WS consumer, binary parsing | **L2 vs captured golden packets**, L3 |
| F7.2 | Subscription manager across 5 sockets | L3 limits; L5: forced drop resubscribes |
| F7.3 | Redis hot cache | L3, L5 |
| F7.4 | Browser WS fan-out, delta updates | L5: 3 clients stay consistent |
| F7.5 | Multiple watchlists + F&O watchlist | L5 |
| F7.6 | Sector watchlists + sectoral index drill-in | L5 |
| F7.7 | Live bar builder merged onto history | **L2: built bars match Dhan's**; G2 |
| F7.8 | **Heatmap** | L5 |
| F7.9 | **Depth ladder + depth watchlist** — 20-level for up to 50 pinned scripts; 200-level on demand for one focused script; 5-level fallback with an explicit note for BSE/MCX/currency | L2 vs captured depth packets; L3: cumulative quantities monotonic, budget never exceeds 50/connection; L5: a BSE script shows 5 levels with the reason, not an empty ladder |

### Epic 8 — Option chain and strategy builders (7 features, ~2 wk)

| ID | Feature | QA |
|---|---|---|
| F8.1 | **Black-76 pricer + IV solver** | **L2 vs `py_vollib`**; L3 parity, delta bounds, convergence |
| F8.2 | **Dhan calibration + drift badge** | **L2: Greeks match Dhan's across 20 strikes; theta convention reconciled** |
| F8.3 | Streaming chain widget | L5 |
| F8.4 | Chain analytics: ATM IV, IV rank, PCR, max pain, skew | L2 vs fixtures |
| F8.5 | Option strategy builder: legs, payoff expiry and T+n | **L2 vs hand-computed payoffs**, L3 |
| F8.6 | Net Greeks + margin via Dhan | L4, L2 vs Dhan margin calculator |
| F8.7 | Stock strategy builder | L5 |

### Epic 9 — Paper trading and forward testing (7 features, ~2.2 wk)

| ID | Feature | QA |
|---|---|---|
| F9.1 | `PaperBroker` on the live feed | L3 state machine; **G1** |
| F9.2 | Order book, trade book, positions, live P&L | **L2 vs independent calc** |
| F9.3 | Multiple concurrent strategies, isolated capital | L3: no cross-strategy leakage |
| F9.4 | Forward-test metrics reusing Epic 3 unchanged | L2 |
| F9.5 | **Live-vs-backtest divergence report** | L5: same-day backtest vs paper reconciles |
| F9.7 | **Paper P&L calendar + monthly/yearly returns** — reuses F3.12–F3.14 unchanged, writing `daily_pnl` with `source_kind='paper'`, marked-to-market at each session close | L2: calendar day totals reconcile with the trade book; L5: the same widgets render for paper as for backtest with no code fork |
| F9.6 | Deploy/pause/stop lifecycle | L3, L5: `api` restart does not disturb running strategies |

### Epic 10 — Long-term investing (5 features, ~1.5 wk)

| ID | Feature | QA |
|---|---|---|
| F10.1 | Holdings, average cost, realised/unrealised P&L | L4, L5: reconciles with your Dhan account |
| F10.2 | **XIRR** + sector/asset allocation | **L2 vs Excel XIRR fixtures**, L3 |
| F10.3 | Dividend tracking | L4 |
| F10.4 | SIP, calendar and threshold rebalancing | L2, G2 |
| F10.5 | Sectoral momentum rotation | G2, walk-forward |

### Epic 11 — AI feature-builder pipeline (7 features, ~2.5 wk)

| ID | Feature | QA |
|---|---|---|
| F11.1 | Feature request → structured spec | L5 |
| F11.2 | Git worktree isolation | L3: never writes outside the worktree |
| F11.3 | Codex task runner streamed to browser with durable task state | L5: interrupt/restart recovers from repository state rather than chat history |
| F11.4 | **Test-gate harness** (G1–G6) | L5: deliberately broken feature is blocked |
| F11.5 | **Layered protected-path Codex rule/guard** | **L5: an automated run editing `engine/risk.py` is denied and audited even if one layer is bypassed** |
| F11.6 | Sandbox stack | **L5: sandbox physically cannot place a real order** |
| F11.7 | Blue/green promote + rollback + history | **L5: promote during a live paper session — `engine` never restarts** |

### Epic 12 — Live trading (6 features, ~1.5 wk) — *gated on explicit go-ahead*

| ID | Feature | QA |
|---|---|---|
| F12.1 | `DhanBroker` order placement | L4 cassettes; L3 state machine |
| F12.2 | Live Order Update WS + postback reconciliation | L3: no lost or duplicated fills |
| F12.3 | Order ticket UI with confirmations | L5 |
| F12.4 | **Risk layer: kill switch, capital and loss caps, orders/min, price bands** | **L3 exhaustive: no path reaches `DhanBroker` bypassing risk**; L5: kill switch halts within one tick |
| F12.5 | Position/order reconciliation vs Dhan | L5 |
| F12.6 | Audit log of every order decision | L5 |

### Epic 13 — Deploy (5 features, ~1 wk)

| ID | Feature | QA |
|---|---|---|
| F13.1 | Dockerise all four processes | L5 |
| F13.2 | Lightsail Mumbai + systemd + Caddy TLS | L5 |
| F13.3 | Single-user auth (password + TOTP) | L5 |
| F13.4 | Nightly Postgres + Parquet backups, tested restore | **L5: restore into a clean box succeeds** |
| F13.5 | Uptime + feed-health monitoring, alerts | L5 |

### 17.1 Totals and sequencing

**102 product features / task count generated from the manifest.** The original **~23–25 week** figure is an initial planning hypothesis, not a commitment. Re-estimate after the first 10 representative features using measured cycle time, review time, prerequisite work, and blocker rate.

Epics 0–5 deliver the research foundation, but numeric epic order is not execution order where dependencies disagree:

- Build F4.1–F4.3 before UI-dependent F2.4, F3.11, F3.13, and F3.14.
- Build F8.1 before delta-based option selection in F3.5.
- Complete production paper deployment and its proof in F13 before any F12 live-trading activation.
- Run F11.7 only after F13.1–F13.3 provide the deployment substrate.

Usage and model availability can change. Work stays resumable through bounded briefs, durable state, reviewed commits, and feature-boundary pauses; schedule impact is reforecast from evidence instead of assuming a particular quota window.

---

## 18. Risks and open items

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **Dhan rate-limit numbers unverified** (docs page 404) | Medium | First task of F0.6. Conservative defaults meanwhile. One central limiter, so correcting them is a config change |
| R2 | **NSE constituent scraping fragility** — blocks bare clients, may change without notice | **High** | Committed fallback snapshot + manual override file; degrades to stale data with a warning rather than breaking (F0.8) |
| R3 | **Corporate-action adjustment in Dhan daily history unknown** | **High** — silently corrupts every equity backtest if unadjusted | Verified in Epic 1. If unadjusted, a split/bonus layer is built before any equity backtest is trusted |
| R4 | **Option fills unrealistic** — `rollingoption` has no bid/ask | Medium | Premium-% slippage model; F9.5's divergence report calibrates it against real paper fills |
| R5 | **Greek convention mismatch**, especially theta | Medium | F8.2 calibration with explicit theta reconciliation and a live drift badge |
| R6 | **Look-ahead bias** | **Critical** | Gate G2 automated for every strategy and screener; `ref(x, n)` rejects negative offsets at parse time |
| R7 | **Backtest/live divergence** | **Critical** | Gate G1 parity suite; F9.5 divergence report |
| R8 | **Regime models overfit** | Medium | Walk-forward enforced, not optional (F6.5) |
| R9 | **Codex plan or model availability throttles the build** | Medium | Model tiering, bounded tasks, durable state, and evidence-based reforecasting; never assume a quota window |
| R10 | **Codex CLI or interface changes break the Epic 11 orchestrator** | Medium | Pin and acceptance-test a supported version when Epic 11 begins; use documented interfaces only |
| R11 | **AI builder drifts over long unattended runs** | Medium | Feature-boundary pauses, parked-feature policy, QA contract written before code |
| R12 | **AI builder modifies safety-critical code** | **Critical** | Protected paths enforced by Codex scope/rules, diff denial, and gate G6; excluded from unattended runs |
| R13 | **Trusted project configuration or inherited tooling broadens permissions** | Medium | Keep `.codex/config.toml` narrow, sandbox automated work, inspect effective scope, and re-check protected diffs before promotion |
| R14 | **Secrets leaking to the frontend or git** | **Critical** | Server-side env only; pre-commit secret scanning; frontend never receives Dhan credentials |
| R15 | **TradingView Advanced approval delayed or refused** | Low | UDF-shaped datafeed makes it a swap; Lightweight Charts is fully functional alone |
| R16 | **Survivorship bias in screener backtests** | Medium | Point-in-time index membership where available; runs flagged as biased where not |
| R17 | ~~Python 3.14 / numba incompatibility~~ **RESOLVED** | — | Verified against PyPI 2026-08-30: numba 0.67.0 and the entire compiled stack ship cp314 `win_amd64` wheels. Build target is **Python 3.14.5**, already installed. See §2.1 |
| R19 | **Dhan's 5-connection limit may be shared between market feed and depth** — unstated in the docs. If shared, five feed sockets leave none for depth, and a sixth connection *silently disconnects the first* | **High** | F0.9's connection budget manager owns all sockets and defaults to the conservative assumption of one shared pool (3 feed / 2 depth). Verified empirically early; if independent, the split is a config change (§3.3.1) |
| R20 | **No Full Market Depth on BSE, MCX or currency** — those segments cap at the 5 levels in the regular feed's Full packet | Low | UI renders 5 levels with an explicit reason rather than an empty 20-level ladder (§12.5) |
| R18 | A future dependency with compiled extensions lacks cp314 wheels | Low | F0.1's acceptance test asserts the lockfile resolves entirely to binary wheels with no source builds, so a regression fails CI rather than surfacing as a mysterious install error |
| R21 | **ShreeNexa accidentally imports or mutates the legacy trading project** | **High** | `F:\Algotrading` is forbidden in `AGENTS.md`, bootstrap acceptance, code search, and dependency review; any later historical import must be separately approved and read-only |

---

## 19. Glossary

| Term | Meaning |
|---|---|
| **StrategyIR** | The JSON intermediate representation of a strategy — the single artefact shared by screener, backtester, paper and live engines |
| **Parity suite** | Tests asserting the vectorised and incremental evaluators produce identical signals (gate G1) |
| **Look-ahead audit** | Replaying a strategy with data truncated at each bar to prove no future information leaks in (gate G2) |
| **Golden packet** | A real Dhan binary feed packet captured once and committed as a test fixture |
| **Cassette** | A recorded Dhan HTTP response used for offline, deterministic integration tests |
| **Drift badge** | UI indicator shown when locally computed Greeks diverge from Dhan's beyond tolerance |
| **Protected path** | A file the AI builder may never edit — the risk layer, brokers, order placement, parity suite |
| **Blue/green promotion** | Starting the new build alongside the old, health-checking, flipping the proxy, draining the old |
| **Feature boundary** | The point at which the unattended build loop pauses for your review |
| **Parked feature** | A feature whose QA gates failed three times; set aside with a report while the loop continues elsewhere |
| **ATM±10** | Dhan's expired-options strike coverage: ten strikes either side of at-the-money (index); ±3 for stock options |
| **UDF** | TradingView's Universal Data Feed format — implementing it makes the Advanced Charting Library a drop-in swap |
| **Black-76** | The forward-based option pricing model appropriate for Indian index options |
| **Scorecard** | The graded view of a backtest — every metric mapped to Reject/Weak/Acceptable/Good/Excellent plus one overall verdict (§10.4) |
| **Implausibility flag** | A warning raised when a result is *too* good — Sharpe above 4, win rate above 95%, too few trades. Marks a result untrustworthy rather than excellent |
| **Deployment gate** | The minimum scorecard verdict required to promote a strategy to paper or live. Overridable, but the override is recorded in the audit log |
| **Strategy type** | `trend_following` / `swing_trading` / `mean_reversion` / `option_selling`. Required on every strategy, because win rate is only meaningful relative to its style. **Distinct from horizon** |
| **Horizon** | `intraday` / `swing` / `positional` / `investing`. Selects which grading band profile applies. A long-term portfolio and a scalping strategy cannot share one yardstick |
| **Grading profile** | One complete set of bands for a horizon. Four ship by default; more can be cloned and edited |
| **Provenance** | Recorded per band: whether a threshold came from you, from published convention, or was derived — so it is always clear which numbers were examined and which were inherited |
| **Daily P&L series** | The `daily_pnl` table — one row per strategy per trading day, written identically by backtest, paper and live. The shared substrate under the calendar and the monthly/yearly return views |
| **Time-weighted return (TWR)** | Return with cashflows removed — measures the *strategy*. Used for monthly and yearly returns |
| **Money-weighted return (XIRR)** | Return including the timing of your contributions — measures *your outcome*. Shown alongside TWR, never confused with it |
| **Connection budget manager** | The single owner of all Dhan sockets, enforcing the 5-connection ceiling across market feed and depth. A sixth connection silently disconnects the first, so this is centralised rather than trusted to call sites |

---

## Appendix A — Reference URLs

| Resource | URL |
|---|---|
| DhanHQ v2 docs | https://dhanhq.co/docs/v2/ |
| Option Chain API | https://dhanhq.co/docs/v2/option-chain/ |
| Live Market Feed | https://dhanhq.co/docs/v2/live-market-feed/ |
| Historical Data | https://dhanhq.co/docs/v2/historical-data/ |
| Expired Options Data | https://dhanhq.co/docs/v2/expired-options-data/ |
| Instrument master (detailed) | https://images.dhan.co/api-data/api-scrip-master-detailed.csv |
| Data API subscription | https://dhan.co/support/platforms/dhanhq-api/how-does-the-dhanhq-data-api-subscription-work/ |
| dhanhq Python SDK | https://pypi.org/project/dhanhq/ |
| NSE index constituents | https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv |
| Codex CLI | https://learn.chatgpt.com/docs/codex/cli |
| Codex IDE extension | https://learn.chatgpt.com/docs/codex/ide |
| Codex `AGENTS.md` guidance | https://learn.chatgpt.com/docs/agent-configuration/agents-md |
| Codex configuration | https://learn.chatgpt.com/docs/config-file/config-basic |
| Codex models | https://learn.chatgpt.com/docs/models |

## Appendix B — Decisions and their rationale

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Historical store | DuckDB + Parquet | TimescaleDB; plain Postgres | Columnar scans dominate backtesting; lowest RAM on a small instance |
| Product AI provider | Pluggable and disabled until approved | Coupling runtime to the development sign-in | Development Codex is not a product API credential; provider, privacy, and cost are separate decisions |
| Resumption after interruption | Durable manifest + git state | Conversation-only state | Recovery remains independent of a chat or session |
| Greeks | Computed locally, calibrated | Dhan endpoint alone | 1 req/3 s makes the endpoint unusable as a live data source |
| Charting | Lightweight Charts + UDF datafeed | Waiting for TV Advanced; KLineChart | No approval needed, and the UDF shape keeps the upgrade path open |
| Rule authoring | Visual builder + formula language + Python hatch | Pine-like DSL; Python only | Pine is proprietary; a custom DSL is the most work and the most bug-prone |
| Dashboards | Widget registry + layout engine | Hard-coded pages | You will rearrange them; this makes that drag-and-drop |
| Process topology | Four separate processes | Single monolith | Zero-downtime promotion is impossible in a monolith |
| Frontend hosting | Vercel | Lightsail-only | Free, fast, and the backend must be persistent anyway |
| Repository root | `F:\ShreeNexa` | `F:\Algotrading`; the old `C:\Users\chand\nifty-terminal` draft path | Greenfield isolation and more space for the Parquet warehouse |
| Build model policy | GPT-5.6 Sol/Terra/Luna tiering by risk and complexity | One model/effort for every task | Reserve deeper reasoning for architecture, numerical correctness, security, and risk |
