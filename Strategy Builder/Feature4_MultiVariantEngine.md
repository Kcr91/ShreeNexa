# Feature 4: Multi-Variant Engine, Volatility Context & Live Tradebook
### ShreeNexa — Dhan F&O Algo Trading Integration

> **Status**: Finalized — Ready for Development  
> **ShreeNexa Runtime**: `worker` process (parallel backtesting & paper shadow tracking) + `api` process (variant, library & tradebook routes) + React UI Dashboard  
> **Last Updated**: 2026-10-02

---

## Table of Contents

1. [Overview & Merged System Concept](#1-overview--merged-system-concept)
2. [Strategy Baseline & Dashboard Condition Library](#2-strategy-baseline--dashboard-condition-library)
3. [Volatility & Market Context Engine (VIX, IV & Greeks)](#3-volatility--market-context-engine-vix-iv--greeks)
4. [Process Stage 1: Strategy Baseline & Variant Matrix Configuration](#4-process-stage-1-strategy-baseline--variant-matrix-configuration)
5. [Process Stage 2: Signal Generator & Variant Spawner](#5-process-stage-2-signal-generator--variant-spawner)
6. [Process Stage 3: Intra-Candle Dual-Price & Volatility Loop](#6-process-stage-3-intra-candle-dual-price--volatility-loop)
7. [Process Stage 4: Multi-Lot Partial Exit & Cost Simulator](#7-process-stage-4-multi-lot-partial-exit--cost-simulator)
8. [Process Stage 5: Real-Money Live Tradebook & Shadow Tracker](#8-process-stage-5-real-money-live-tradebook--shadow-tracker)
9. [Process Stage 6: Database Schema & Volatility Heatmap Analytics](#9-process-stage-6-database-schema--volatility-heatmap-analytics)
10. [Dashboard UI Layout & Custom Condition Builder Specification](#10-dashboard-ui-layout--custom-condition-builder-specification)
11. [FastAPI Endpoints](#11-fastapi-endpoints)
12. [Build Checklist](#12-build-checklist)

---

## 1. Overview & Merged System Concept

Traditional algo systems separate backtesting, trade tracking, and market context recording into fragmented modules.

This merged **Multi-Variant Engine & Volatility Tradebook** combines four critical operations into a single high-performance pipeline:
1. **Parallel Universes Execution**: Evaluates your Core Strategy Baseline (`Variant 0`) and $N$ selected test variations simultaneously in one single pass.
2. **Dual-Price Tracking**: Evaluates entry, stop-loss, targets, and trailing exits against both the **Underlying Spot Price** (Index/Stock) and the **Option Premium** chart.
3. **Volatility & Greeks Snapshots**: Automatically captures **India VIX**, **Option IV %**, and **Greeks** ($\Delta, \Gamma, \Theta, \nu$) at the exact moment of trade entry and trade exit.
4. **Unified Real-Money Tradebook**: Persists complete trade records for Backtests, Paper Trading, and Real-Money Live Orders (Dhan API) into a single database for post-trade audit and strategy optimization.

```
                    [STRATEGY BUY SIGNAL: NIFTY 25000 CE @ ₹150]
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       ▼                                  ▼                                  ▼
[BASELINE: Strategy Default]   [VARIANT 1: Partial Exits]        [VARIANT 2: Trailing SL]
• 1 Lot                        • 3 Lots                          • 3 Lots
• Fixed 20% Option SL          • 50% exit @ T1 (+30%)            • SL at Spot VWAP
• Target 1: +40% (100% exit)   • 50% exit @ T2 (+60%)            • Trail 10% on Premium
       │                                  │                                  │
       ├── Entry VIX: 14.25               ├── Entry VIX: 14.25                ├── Entry VIX: 14.25
       ├── Entry IV : 28.5%               ├── Entry IV : 28.5%                ├── Entry IV : 28.5%
       │                                  │                                  │
       ▼                                  ▼                                  ▼
Exit PnL: +₹2,400              Exit PnL: +₹4,800                 Exit PnL: +₹3,500
Exit VIX: 15.10 (+0.85)        Exit VIX: 15.10 (+0.85)           Exit VIX: 15.10 (+0.85)
Exit IV : 31.2% (+2.7%)        Exit IV : 31.2% (+2.7%)           Exit IV : 31.2% (+2.7%)
Exit Reason: TARGET_1          Exit Reason: TARGET_2             Exit Reason: TRAILING_SL
```

---

## 2. Strategy Baseline & Dashboard Condition Library

### The User Workflow

1. **Strategy Core Baseline (`Variant 0`)**:
   - When creating a strategy, you define its **Core Entry, Default Stop-Loss, and Default Target/Exit Rules**.
   - This core rule set automatically runs as **Variant 0 (Primary Baseline)**.
2. **Optional Test Variations (Dashboard Library Selection)**:
   - On the Strategy Dashboard, you can select additional tracking conditions from a **Pre-defined Condition Library** using simple checkboxes.
   - You can **Edit** existing library conditions or click **`[+ Add Custom Condition]`** to build new tracking rules (Time-based, Price-based, Indicator-based).
3. **Save to Library for Future Use**:
   - Any custom condition or tweaked variation set can be saved to your personal **Condition Library** in PostgreSQL, making it reusable across all future strategies.

---

## 3. Volatility & Market Context Engine (VIX, IV & Greeks)

### Automatic Snapshots at Entry and Exit

For **every trade** (Backtest, Paper, or Real-Money Live Trading), the engine automatically captures:

```
ENTRY SNAPSHOT:
├── entry_india_vix        : India VIX 1-min candle value at entry (e.g. 14.25)
├── entry_option_iv       : Black-Scholes implied volatility % of contract (e.g. 28.5%)
├── entry_greeks          : Delta (0.52), Gamma (0.004), Theta (-12.5), Vega (18.2)
└── entry_underlying_spot : Spot price of index/stock at signal timestamp

EXIT SNAPSHOT:
├── exit_india_vix         : India VIX 1-min candle value at exit (e.g. 15.10)
├── vix_change             : exit_india_vix - entry_india_vix (+0.85)
├── exit_option_iv        : Contract IV % at exit (e.g. 31.20%)
├── iv_change              : exit_option_iv - entry_option_iv (+2.70% IV expansion)
├── exit_greeks           : Exit Delta, Gamma, Theta, Vega
└── exit_reason            : TARGET_1 | TARGET_2 | SL_FIXED | SL_SPOT | SL_TRAILING | TIME_EXIT | SQUARE_OFF_315
```

---

## 4. Process Stage 1: Strategy Baseline & Variant Matrix Configuration

```json
{
  "strategy_id": 5,
  "run_name": "Nifty Open-High Put Strategy — Backtest & Volatility Run",
  
  "baseline_execution": {
    "capital": 500000.0,
    "quantity_mode": "FIXED_LOTS",
    "lots": 1,
    "sl_type": "OPTION_PERCENTAGE",
    "sl_value": 20.0,
    "target_type": "OPTION_PERCENTAGE",
    "target_value": 40.0
  },

  "selected_library_variations": [
    {
      "condition_id": 101,
      "name": "Multi-Target Partial Exit (50/50)",
      "override_params": { "target_1": 30.0, "target_2": 60.0 }
    },
    {
      "condition_id": 105,
      "name": "Trailing SL on Premium",
      "override_params": { "trail_step_pct": 10.0 }
    }
  ]
}
```

---

## 5. Process Stage 2: Signal Generator & Variant Spawner

1. Strategy condition evaluates `TRUE` $\rightarrow$ Produces **1 Base Signal** (e.g. `BUY NIFTY 25000 CE @ ₹150.00`).
2. Engine fetches current **India VIX** and calculates option contract **IV & Greeks**.
3. Engine creates a master `TradeGroup` with entry volatility snapshot.
4. Engine instantiates $1 + N$ independent `VariantTrade` state instances in memory:
   - `Variant 0`: Your Primary Core Strategy Baseline.
   - `Variant 1..N`: Selected optional tracking variations from your Library.

---

## 6. Process Stage 3: Intra-Candle Dual-Price & Volatility Loop

On every 1-minute candle during execution:

1. Updates Underlying Spot Price (Index / Stock) and Option Premium Price.
2. Evaluates Stop-Loss, Targets, and Trailing SL rules independently for each variant.
3. **Conservative Intra-Candle OHLC Resolution**:
   - If both SL and Target fall within the candle's High-Low range, the simulator conservatively assumes **SL was hit first** (worst-case assumption).
4. **Dual-Price Evaluation**:
   - Evaluates whether SL/Exit condition was triggered by Spot price movement or Option premium movement.

---

## 7. Process Stage 4: Multi-Lot Partial Exit & Cost Simulator

### Partial Lot Exits & Remaining Position Management
- Exit partial lots at Target 1, update realized PnL, adjust remaining quantity, and auto-move Stop-Loss to Breakeven for remaining lots.

### Exchange & Brokerage Cost Calculations

| Fee / Cost Category | Equity Cash | F&O Options | F&O Futures |
|---|---|---|---|
| **Dhan Brokerage** | ₹0 (Free) | ₹20 per executed order | ₹20 per executed order |
| **STT / CTT** | 0.1% on Buy & Sell | 0.125% on Option Premium (Sell side) | 0.0125% on Sell side |
| **Exchange Turnover Fee** | NSE 0.00297% | NSE Options 0.0355% | NSE Futures 0.0019% |
| **Slippage Model** | Configurable (0.05% or ₹0.10) | Configurable (Fixed ₹0.50/pt or %) | Configurable (0.05%) |

---

## 8. Process Stage 5: Real-Money Live Tradebook & Shadow Tracker

In **Paper Trading** or **Live Real-Money Trading**:

```
[LIVE SIGNAL GENERATED]
           │
           ├── REAL EXECUTION (Dhan API):  Variant 0 (Primary Baseline Order) ──► Real Order Sent & Logged
           │
           ├── SHADOW VARIANT (Simulated): Variant 1 (Partial Exit Grid)      ──► Tracked in Memory
           └── SHADOW VARIANT (Simulated): Variant 2 (Trailing SL Grid)        ──► Tracked in Memory
```

- Real orders placed via Dhan API for your **Primary Baseline** are saved into the `live_tradebook` table.
- Stores Dhan Order ID, Fill Time, Realized PnL, Taxes/Brokerage, Slippage, **Entry/Exit VIX**, **Entry/Exit IV**, **Greeks**, and **Exit Reason**.
- All shadow test variations run in memory against live feeds for real-time comparison.

---

## 9. Process Stage 6: Database Schema & Volatility Heatmap Analytics

```sql
-- 1. Reusable Tracking Condition Library (Persisted for Future Use)
CREATE TABLE variant_library_conditions (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    category            TEXT CHECK (category IN ('SL_VARIANT', 'TARGET_VARIANT', 'PARTIAL_EXIT', 'TRAILING_SL', 'TIME_EXIT', 'INDICATOR_EXIT')),
    condition_config    JSONB NOT NULL,
    is_built_in         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Master Strategy Execution Runs
CREATE TABLE variant_runs (
    run_id              SERIAL PRIMARY KEY,
    strategy_id         INTEGER REFERENCES strategy_configs(id),
    run_type            TEXT CHECK (run_type IN ('BACKTEST', 'PAPER', 'LIVE')),
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ NOT NULL,
    total_signals       INTEGER,
    total_variants_run  INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Tradebook & Detailed Variant Trade Logs (Includes Merged VIX, IV & Greeks)
CREATE TABLE variant_trades (
    id                      SERIAL PRIMARY KEY,
    run_id                  INTEGER REFERENCES variant_runs(run_id),
    variant_name            TEXT NOT NULL,
    symbol                  TEXT NOT NULL,
    signal_type             TEXT NOT NULL,
    entry_time              TIMESTAMPTZ NOT NULL,
    entry_spot_price        NUMERIC(12,4),
    entry_option_price      NUMERIC(12,4),
    entry_india_vix         NUMERIC(6,2),         -- Merged VIX at entry
    entry_option_iv         NUMERIC(6,2),         -- Merged IV % at entry
    entry_delta             NUMERIC(6,3),         -- Greeks at entry
    entry_gamma             NUMERIC(6,4),
    entry_theta             NUMERIC(8,2),
    entry_vega              NUMERIC(8,2),
    exit_time               TIMESTAMPTZ,
    exit_spot_price         NUMERIC(12,4),
    exit_option_price       NUMERIC(12,4),
    exit_india_vix          NUMERIC(6,2),         -- Merged VIX at exit
    exit_option_iv          NUMERIC(6,2),         -- Merged IV % at exit
    vix_change              NUMERIC(6,2),
    iv_change               NUMERIC(6,2),
    exit_reason             TEXT NOT NULL,        -- TARGET_1 | TARGET_2 | SL_FIXED | SL_SPOT | SL_TRAILING | TIME_EXIT | SQUARE_OFF_315
    quantity                INTEGER,
    realized_pnl            NUMERIC(12,2),
    max_favorable_excursion NUMERIC(12,4),
    max_adverse_excursion   NUMERIC(12,4)
);

-- 4. Real-Money Live Tradebook (Dhan API Executed Orders)
CREATE TABLE live_tradebook (
    trade_id                SERIAL PRIMARY KEY,
    dhan_order_id           TEXT UNIQUE NOT NULL,
    strategy_id             INTEGER REFERENCES strategy_configs(id),
    symbol                  TEXT NOT NULL,
    signal_type             TEXT NOT NULL,
    fill_time               TIMESTAMPTZ NOT NULL,
    buy_price               NUMERIC(12,4) NOT NULL,
    sell_price              NUMERIC(12,4),
    quantity                INTEGER NOT NULL,
    entry_vix               NUMERIC(6,2),
    exit_vix                NUMERIC(6,2),
    entry_iv                NUMERIC(6,2),
    exit_iv                 NUMERIC(6,2),
    exit_reason             TEXT,
    realized_pnl            NUMERIC(12,2),
    brokerage_charges       NUMERIC(10,2),
    stt_taxes               NUMERIC(10,2),
    slippage_amount         NUMERIC(10,2),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. Dashboard UI Layout & Custom Condition Builder Specification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STRATEGY BUILDER DASHBOARD                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SECTION 1: CORE STRATEGY SETUP (Primary Baseline)                          │
│  ├── Strategy Name : [ Nifty Open-High Put Strategy                      ]  │
│  ├── Instrument    : [ NIFTY Index Options (PE)                         ]  │
│  ├── Entry Rule    : [ 1min Candle Open == High  AND  Daily RSI > 60   ]  │
│  ├── Default SL    : [ Fixed 20% on Option Premium                      ]  │
│  └── Default Exit  : [ Target 1: 40% Premium Gain (100% Exit)           ]  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SECTION 2: ADDITIONAL VARIANT TRACKER (Select / Edit / Save Library)       │
│  "Select additional tracking conditions from your library to test alongside":│
│                                                                             │
│  [✓] 1. Multi-Target Partial Exit  [Edit]  [Delete]                         │
│         ↳ Exit 50% @ +30%, Exit 50% @ +60%                                  │
│                                                                             │
│  [✓] 2. Trailing Stop-Loss        [Edit]  [Delete]                         │
│         ↳ Trail 10% premium step after Target 1                             │
│                                                                             │
│  [ ] 3. Spot VWAP Level SL        [Edit]  [Delete]                         │
│         ↳ Exit if underlying spot crosses below VWAP                        │
│                                                                             │
│  [+ ADD NEW CUSTOM CONDITION]   [SAVE CONDITION TO LIBRARY FOR FUTURE USE]  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  SECTION 3: VOLATILITY REGIME HEATMAP ANALYTICS                             │
│  ├── Profitable VIX Range : 12.0 – 16.5 VIX (Win Rate: 68%, Profit: +₹4.2k) │
│  └── Profitable IV Zone   : 22.0% – 32.0% IV (IV Expansion Sweet Spot)     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ ▶ RUN BACKTEST / DEPLOY LIVE TRADEBOOK ]                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. FastAPI Endpoints (`/variant/*` & `/tradebook/*`)

Mounted at `/variant` and `/tradebook` in `src/api/routers/`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/variant/library` | List all saved & built-in tracking conditions in library |
| `POST` | `/variant/library` | Save a new custom tracking condition to library for future use |
| `PUT` | `/variant/library/{id}` | Update an existing library condition |
| `DELETE` | `/variant/library/{id}` | Delete a library condition |
| `POST` | `/variant/run` | Execute multi-variant backtest run with VIX/IV snapshots |
| `GET` | `/variant/results/{run_id}` | Get summary & ranking table (Baseline vs Variations) |
| `GET` | `/variant/analytics/vix-heatmap` | Generate PnL & Win Rate heatmaps grouped by VIX & IV range |
| `GET` | `/tradebook/live` | Fetch real-money live tradebook logs with VIX/IV & Exit Reasons |

---

## 12. Build Checklist (~28 hours)

| # | Task | File | Est. Time |
|---|---|---|---|
| 1 | Alembic migration for `variant_library_conditions`, `variant_runs`, `variant_trades`, `live_tradebook` | `alembic/versions/` | 1.5h |
| 2 | SQLAlchemy Models | `src/engine/models.py` | 1h |
| 3 | Black-Scholes IV & Options Greeks Engine | `src/engine/greeks_calc.py` | 3h |
| 4 | India VIX Ingestor & Real-Time Streamer | `src/engine/vix_streamer.py` | 2h |
| 5 | Library Manager & Condition Parser | `src/engine/library_manager.py` | 3h |
| 6 | Signal Generator & Spawner with Volatility Snapshots | `src/engine/spawner.py` | 3h |
| 7 | Dual-Price Intra-Candle Simulation Loop | `src/engine/multi_variant_loop.py` | 4h |
| 8 | Multi-Lot Partial Exit & Cost Simulator | `src/engine/cost_simulator.py` | 3h |
| 9 | Dhan Live Real-Money Tradebook & Shadow Tracker | `src/live/live_tradebook.py` | 4h |
| 10 | Volatility Regime Heatmap Analytics Engine | `src/analytics/vix_analytics.py` | 3.5h |

---

**Feature 4 (Merged Engine, Volatility Context & Live Tradebook) is fully finalized.**
