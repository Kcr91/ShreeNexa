# Feature 5: Paper Trading Engine & Real-Time Shadow Tracker
### ShreeNexa — Dhan F&O Algo Trading Integration

> **Status**: Finalized — Ready for Development  
> **ShreeNexa Runtime**: `worker` process (live feed ingestion & execution simulation) + `api` process (multi-algo paper dashboard routes) + React UI  
> **Last Updated**: 2026-10-02

---

## Table of Contents

1. [Overview & Unified "1-Click Switch" Architecture](#1-overview--unified-1-click-switch-architecture)
2. [Process Stage 1: Live Feed Handler & Tick Aggregator](#2-process-stage-1-live-feed-handler--tick-aggregator)
3. [Process Stage 2: Live Execution Simulator & Fill Delay Engine](#3-process-stage-2-live-execution-simulator--fill-delay-engine)
4. [Process Stage 3: Real-Time Shadow Variant Tracker](#4-process-stage-3-real-time-shadow-variant-tracker)
5. [Process Stage 4: Multi-Algo Dashboard & Quick Comparison Panel](#5-process-stage-4-multi-algo-dashboard--quick-comparison-panel)
6. [Process Stage 5: Deep-Dive Drift Analytics & Go/No-Go Readiness Score](#6-process-stage-5-deep-dive-drift-analytics--gono-go-readiness-score)
7. [PostgreSQL Schema & Persistence](#7-postgresql-schema--persistence)
8. [Dashboard UI Specification & Inspection Card](#8-dashboard-ui-specification--inspection-card)
9. [FastAPI Endpoints](#9-fastapi-endpoints)
10. [Build Checklist](#10-build-checklist)

---

## 1. Overview & Unified "1-Click Switch" Architecture

The **Paper Trading Engine** uses the **Unified Live Execution Engine Architecture**: The exact same strategy, screener, risk rules, and multi-variant engine run in both Paper Mode and Live Mode.

Only the **Execution Adapter** changes via a dashboard toggle:

```
                    ┌──────────────────────────────────────────┐
                    │    UNIFIED LIVE ALGO ENGINE (SAME CODE)  │
                    └────────────────────┬─────────────────────┘
                                         │
                         [MODE TOGGLE IN DASHBOARD]
                                         │
           ┌─────────────────────────────┴─────────────────────────────┐
           ▼                                                           ▼
┌──────────────────────────────────────┐            ┌──────────────────────────────────────┐
│  MODE = "PAPER"                      │            │  MODE = "LIVE"                       │
│  • Uses Paper Execution Adapter      │            │  • Uses Dhan Live API v2 Adapter     │
│  • Simulates orders locally on feed  │            │  • Sends REAL orders to Dhan API v2  │
│  • Shadow variants tracked in memory │            │  • Real money executed on broker     │
└──────────────────────────────────────┘            └──────────────────────────────────────┘
```

### Key Advantages

- **Zero Code Rewriting**: When a strategy completes paper trading validation, you click **`[SWITCH TO LIVE]`** on the dashboard. The exact same strategy starts placing real orders on Dhan API.
- **100% Code Path Verification**: Paper trading tests the exact same WebSocket stream, screener speed, indicator calculation, and risk checks that execute real money.
- **Simultaneous Real + Shadow Tracking**: In Live mode, real money is executed on your Primary Baseline while all test variations continue running as Shadow Variants in background memory.

---

## 2. Process Stage 1: Live Feed Handler & Tick Aggregator

1. **Dhan WebSocket Feed Connector**: Connects to Dhan live market data WebSocket servers.
2. **Dynamic Feed Subscription**:
   - Subscribes to live ticks for 208 F&O stocks, index spots (Nifty, BankNifty, FinNifty, Sensex), active option contracts (ATM $\pm N$), and India VIX.
3. **Real-Time Candle Aggregator**:
   - Converts raw tick data streams into 1-minute OHLCV candles in memory.
   - Emits a `candle_closed` event every 60 seconds to trigger strategy evaluation.

---

## 3. Process Stage 2: Live Execution Simulator & Fill Delay Engine

When a strategy condition evaluates `TRUE` on a closed 1-minute candle:

1. **Simulated Order Placement**: Captures live Ask/Bid prices from the order book tick.
2. **Fill Delay Simulation**: Adds realistic network & execution delay (100–200ms) to model real broker latency.
3. **Slippage & Cost Simulator**: Deducts configurable slippage (e.g. ₹0.50 per option contract) plus STT, exchange turnover fees, and Dhan brokerage (₹20/order).

---

## 4. Process Stage 3: Real-Time Shadow Variant Tracker

- **Primary Paper Trade**: Executes your Core Strategy Baseline (`Variant 0`) as the main active paper position.
- **Shadow Variants**: Runs all selected library variations (Partial Exits, Trailing SL, VWAP SL) concurrently in background memory on the exact same live tick stream.
- **Real-Time Leaderboard**: Monitors if a shadow variant is outperforming your primary paper baseline.

---

## 5. Process Stage 4: Multi-Algo Dashboard & Quick Comparison Panel

### View A: Multi-Algo Active Overview List
Shows all currently running paper algos in a clean overview table:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ACTIVE PAPER TRADING ALGOS (3 RUNNING)                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ALGO NAME                     INSTRUMENT    OPEN P&L   PAPER P&L  STATUS   │
│  1. Nifty Open-High Put        NIFTY PE      +₹2,400    +₹18,500   ACTIVE ► │
│  2. BankNifty EMA Crossover    BANKNIFTY CE  -₹800      +₹9,200    ACTIVE ► │
│  3. Reliance Intraday Breakout RELIANCE EQ   ₹0         -₹1,100    ACTIVE ► │
└─────────────────────────────────────────────────────────────────────────────┘
```

### View B: Strategy Inspection View (Click any strategy to open)
Opening a specific running strategy displays its **Quick Live vs Backtest Comparison Card**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STRATEGY: Nifty Open-High Put Buying   [MODE: PAPER TRADING] [SWITCH LIVE] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 QUICK LIVE PAPER vs. BACKTEST COMPARISON (LAST 30 DAYS)                 │
│  ┌─────────────────────────┬──────────────────┬──────────────────┐          │
│  │ METRIC                  │ LIVE PAPER       │ BACKTEST EXPECTED│          │
│  ├─────────────────────────┼──────────────────┼──────────────────┤          │
│  │ Total Realized PnL      │ +₹18,500         │ +₹19,200         │ ✅ ON TRACK│
│  │ Win Rate (%)            │ 64.2%            │ 66.0%            │ ✅ STABLE │
│  │ Max Drawdown (%)        │ -4.8%            │ -5.2%            │ ✅ SAFE   │
│  │ Total Trades Executed   │ 28 Trades        │ 30 Trades        │ ✅ MATCH  │
│  └─────────────────────────┴──────────────────┴──────────────────┘          │
│                                                                             │
│  🟢 ACTIVE POSITIONS (1 Open Trade)                                         │
│  • NIFTY 25000 PE | Qty: 3 Lots | Buy: ₹150.00 | LTP: ₹158.00 | PnL: +₹2,400│
│  [Square Off Now]  [Modify SL: ₹120]  [Modify Target: ₹210]                 │
│                                                                             │
│  👥 SHADOW VARIANTS LEADERBOARD                                             │
│  • Variant 0 (Baseline Default) : +₹18,500 PnL (Currently Live)              │
│  • Variant 1 (Multi-Target Grid): +₹22,100 PnL ⚡ Outperforming Baseline!    │
│  • Variant 2 (Trailing SL Grid) : +₹16,400 PnL                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Process Stage 5: Deep-Dive Drift Analytics & Go/No-Go Readiness Score

### 3-Month Performance Drift Analysis
- **Win Rate Drift**: Compares live paper win rate vs backtest expected win rate.
- **Slippage & Latency Impact**: Calculates exact loss attributed to fill delay and slippage.
- **Drawdown Safety Check**: Verifies paper trading max drawdown stays within historical parameters.

### Go / No-Go Readiness Score Engine (0–100%)

$$\text{Readiness Score} = 0.40(\text{PnL Match}) + 0.30(\text{Win Rate Stability}) + 0.20(\text{Drawdown Safety}) + 0.10(\text{Sample Size Weight})$$

- **Score $\ge 80\%$**: Marked as **`✅ READY FOR LIVE REAL-MONEY DEPLOYMENT`**.
- **Score $< 80\%$**: Marked as **`⚠️ NEEDS FURTHER VALIDATION / TUNING`**.

---

## 7. PostgreSQL Schema & Persistence

```sql
-- 1. Active Paper Trading Sessions
CREATE TABLE paper_sessions (
    session_id          SERIAL PRIMARY KEY,
    strategy_id         INTEGER REFERENCES strategy_configs(id),
    session_name        TEXT NOT NULL,
    status              TEXT CHECK (status IN ('RUNNING', 'PAUSED', 'COMPLETED', 'SWITCHED_TO_LIVE')),
    initial_capital     NUMERIC(12,2) DEFAULT 500000.00,
    current_capital     NUMERIC(12,2),
    start_time          TIMESTAMPTZ DEFAULT NOW(),
    end_time            TIMESTAMPTZ,
    readiness_score     NUMERIC(5,2) DEFAULT 0.00
);

-- 2. Open Paper Positions
CREATE TABLE paper_positions (
    position_id         SERIAL PRIMARY KEY,
    session_id          INTEGER REFERENCES paper_sessions(session_id) ON DELETE CASCADE,
    symbol              TEXT NOT NULL,
    signal_type         TEXT NOT NULL,
    entry_time          TIMESTAMPTZ NOT NULL,
    entry_price         NUMERIC(12,4) NOT NULL,
    current_price       NUMERIC(12,4),
    quantity            INTEGER NOT NULL,
    unrealized_pnl      NUMERIC(12,2),
    active_sl           NUMERIC(12,4),
    active_target       NUMERIC(12,4),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Paper Trade History (Matches Live Tradebook Schema)
CREATE TABLE paper_tradebook (
    trade_id            SERIAL PRIMARY KEY,
    session_id          INTEGER REFERENCES paper_sessions(session_id),
    symbol              TEXT NOT NULL,
    signal_type         TEXT NOT NULL,
    entry_time          TIMESTAMPTZ NOT NULL,
    exit_time           TIMESTAMPTZ,
    entry_price         NUMERIC(12,4) NOT NULL,
    exit_price          NUMERIC(12,4),
    quantity            INTEGER NOT NULL,
    realized_pnl        NUMERIC(12,2),
    exit_reason         TEXT,
    entry_vix           NUMERIC(6,2),
    exit_vix            NUMERIC(6,2),
    entry_iv            NUMERIC(6,2),
    exit_iv             NUMERIC(6,2),
    simulated_slippage  NUMERIC(10,2),
    simulated_brokerage NUMERIC(10,2)
);
```

---

## 8. Dashboard UI Specification & Inspection Card

1. **Multi-Algo Overview Table**: Lists all active running paper strategies with status, paper PnL, open positions count.
2. **Strategy Inspection Card**:
   - Single-click open for any strategy.
   - Quick comparison card (Live Paper vs Backtest Expected PnL, Win Rate, Drawdown).
3. **Manual Action Buttons**:
   - `[Square Off Now]` — Closes active paper position immediately.
   - `[Modify SL / Target]` — Opens quick slider/input modal to adjust active SL or Target.
   - `[Pause Strategy]` — Suspends new paper signals.
   - `[SWITCH TO LIVE REAL-MONEY]` — Flips execution mode adapter to Dhan API v2.

---

## 9. FastAPI Endpoints (`/paper/*`)

Mounted at `/paper` in `src/api/routers/paper_engine.py`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/paper/sessions` | List all active and historical paper trading sessions |
| `POST` | `/paper/sessions` | Start a new paper trading session for a strategy |
| `POST` | `/paper/sessions/{id}/pause` | Pause an active paper trading session |
| `POST` | `/paper/sessions/{id}/resume` | Resume a paused paper trading session |
| `POST` | `/paper/sessions/{id}/squareoff` | Manually square off active paper position |
| `GET` | `/paper/sessions/{id}/quick-compare` | Fetch live paper vs backtest expected metrics for inspection card |
| `GET` | `/paper/sessions/{id}/drift-analysis` | Detailed Stage 5 performance drift & readiness score calculation |
| `POST` | `/paper/sessions/{id}/switch-to-live` | Toggle strategy mode from `PAPER` to `LIVE` real-money execution |

---

## 10. Build Checklist (~24 hours)

| # | Task | File | Est. Time |
|---|---|---|---|
| 1 | Alembic migration for `paper_sessions`, `paper_positions`, `paper_tradebook` | `alembic/versions/` | 1h |
| 2 | SQLAlchemy Models | `src/paper/models.py` | 1h |
| 3 | Dhan Live WebSocket Connector & 1-min Candle Aggregator | `src/paper/feed_aggregator.py` | 4h |
| 4 | Unified Execution Engine Paper Adapter | `src/paper/paper_adapter.py` | 4h |
| 5 | Real-Time Shadow Variant Tracker | `src/paper/shadow_tracker.py` | 3h |
| 6 | Quick Comparison Metrics Engine (Live vs Backtest) | `src/paper/quick_comparator.py` | 3h |
| 7 | Deep-Dive Drift Analytics & Readiness Score Engine | `src/analytics/readiness_engine.py` | 3h |
| 8 | FastAPI Router (`/paper/*` - 8 endpoints) | `src/api/routers/paper_engine.py` | 3h |
| 9 | React UI: Multi-Algo Overview & Strategy Inspection Card | frontend | TBD |

---

**Feature 5 (Paper Trading Engine & Real-Time Shadow Tracker) is fully finalized.**
