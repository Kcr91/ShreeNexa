# Feature 6: Dhan Live Trading, Risk Guardrails & Safety Engine
### ShreeNexa — Dhan F&O Algo Trading Integration

> **Status**: Finalized — Ready for Development  
> **ShreeNexa Runtime**: `worker` process (live execution & async queue) + `api` process (broker & safety routes) + React UI Dashboard  
> **Last Updated**: 2026-10-02

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [Process Stage 1: Dhan API v2 Live Order Execution Adapter](#2-process-stage-1-dhan-api-v2-live-order-execution-adapter)
3. [Process Stage 2: Sub-500ms Latency Pipeline & Async Queue](#3-process-stage-2-sub-500ms-latency-pipeline--async-queue)
4. [Process Stage 3: Multi-Layer Risk Guardrails & Auto-Kill Switch](#4-process-stage-3-multi-layer-risk-guardrails--auto-kill-switch)
5. [Process Stage 4: Live Tradebook & Reconciliation Engine](#5-process-stage-4-live-tradebook--reconciliation-engine)
6. [Process Stage 5: Emergency Control Center & Instant Notifications](#6-process-stage-5-emergency-control-center--instant-notifications)
7. [PostgreSQL Schema & Persistence](#7-postgresql-schema--persistence)
8. [Dashboard UI Specification & Emergency Controls](#8-dashboard-ui-specification--emergency-controls)
9. [FastAPI Endpoints](#9-fastapi-endpoints)
10. [Build Checklist](#10-build-checklist)

---

## 1. Overview & Architecture

**Feature 6** connects the unified live algo engine directly to **Dhan API v2** for real-money execution. It acts as the final production execution and safety layer, ensuring all orders are placed with **sub-500ms latency** and protected by **multi-layer risk guardrails**, **auto-kill switches**, and **instant Telegram alerts**.

```
                [LIVE MARKET FEED: STRATEGY SIGNAL TRIGGERED]
                                      │
                                      ▼
               [STAGE 3: MULTI-LAYER SAFETY GUARDRAILS CHECK]
               ├── Max Daily Loss Limit OK? (e.g., PnL > -3%)  [YES]
               ├── Single Trade Exposure OK? (e.g., < 10% Cap)  [YES]
               ├── Max Open Positions OK? (e.g., < 5 Trades)    [YES]
               └── Circuit Breaker / Freeze Check OK?          [YES]
                                      │
                                      ▼
               [STAGE 2: SUB-500ms ASYNC ORDER PIPELINE]
               ├── Resolves Symbol ──► Dhan Security ID         (~20ms)
               ├── Prepares Order Payload & Signatures          (~10ms)
               └── Sends Order via Dhan API v2 (dhanhq SDK)     (~150ms)
                                      │
                                      ▼
               [STAGE 1 & 4: DHAN ORDER FILLED & TRADEBOOK LOGGED]
               ├── Dhan Order ID: #DH-948102
               ├── Logged in Live Tradebook + VIX/IV Context
               └── Telegram Notification Pushed Instantly
```

---

## 2. Process Stage 1: Dhan API v2 Live Order Execution Adapter

- **Dhan API v2 Order Placement**: Direct execution using official `dhanhq` Python SDK supporting `MARKET`, `LIMIT`, `SL-LIMIT`, and `SL-MARKET` order types.
- **Dynamic Security ID Mapping**: Converts spot trading signals (e.g., Nifty @ 25,010) into exact Dhan `security_id` values for active ATM or OTM option contracts.
- **Order State Tracking**: Tracks real-time order lifecycle events (`PENDING` $\rightarrow$ `TRADED` / `CANCELLED` / `REJECTED`).

---

## 3. Process Stage 2: Sub-500ms Latency Pipeline & Async Queue

- **Latency Guarantee**: Signal Generation $\rightarrow$ Risk Validation $\rightarrow$ Dhan API Order Submission is executed in **$< 500$ milliseconds**.
- **Non-Blocking Async Queue**: Built on Python `asyncio` task queues so order submission latency never stalls or delays live WebSocket market feed ingestion.

---

## 4. Process Stage 3: Multi-Layer Risk Guardrails & Auto-Kill Switch (`safety_guard.py`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MULTI-LAYER SAFETY GUARDRAILS                         │
│                                                                             │
│  GUARD 1: Max Daily Loss Auto-Kill Switch                                   │
│  • Trigger: Realized + Unrealized Daily Loss >= 3% of Total Capital         │
│  • Action : 1. Cancel all pending orders on Dhan API                       │
│             2. Market square off all open positions immediately             │
│             3. Lock system and halt trading for rest of day                 │
│                                                                             │
│  GUARD 2: Single Trade Exposure Cap                                         │
│  • Max capital allocated to 1 trade capped at 10% of total capital          │
│                                                                             │
│  GUARD 3: Max Concurrent Positions Limit                                    │
│  • Max 5 active open trades allowed simultaneously                          │
│                                                                             │
│  GUARD 4: Circuit Breaker & Freeze Check                                    │
│  • Rejects orders if stock/contract is within 0.5% of upper/lower circuit  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Process Stage 4: Live Tradebook & Reconciliation Engine

- **Live Real-Money Tradebook**: Every executed order is logged into the `live_tradebook` table with Dhan Order ID, execution fill price, slippage, brokerage, STT/taxes, realized PnL, plus entry/exit VIX, IV, and Greeks snapshots.
- **Broker Position Reconciler**: Runs every 5 minutes during market hours, calling `dhan.get_positions()` to verify that local position records match broker positions 1:1, auto-flagging any position drift or manual broker intervention.

---

## 6. Process Stage 5: Emergency Control Center & Instant Notifications

- **Telegram / WhatsApp Alert Bot**: Pushes instant notifications for:
  - Trade Entry & Order Fill confirmation
  - Target Hit & Partial Lot Exits
  - Stop-Loss Hit
  - Auto-Kill Switch Triggered
- **Emergency Physical Kill-Switch**: A prominent red button on your terminal dashboard: **`[ EMERGENCY SQUARE OFF ALL & STOP TRADING ]`**.

---

## 7. PostgreSQL Schema & Persistence

```sql
-- 1. Live Trading System Controls & Risk Settings
CREATE TABLE live_risk_settings (
    id                      SERIAL PRIMARY KEY,
    max_daily_loss_pct      NUMERIC(5,2) DEFAULT 3.00,       -- 3% max daily loss auto-kill
    max_trade_exposure_pct NUMERIC(5,2) DEFAULT 10.00,      -- 10% max single trade cap
    max_concurrent_trades   INTEGER DEFAULT 5,
    circuit_buffer_pct      NUMERIC(5,2) DEFAULT 0.50,
    kill_switch_active      BOOLEAN DEFAULT FALSE,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Real-Money Live Tradebook (Dhan API Executed Orders)
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

-- 3. Safety Audit & System Event Logs
CREATE TABLE live_safety_events (
    id                      SERIAL PRIMARY KEY,
    event_type              TEXT CHECK (event_type IN ('KILL_SWITCH_TRIGGERED', 'EXPOSURE_CAP_EXCEEDED', 'POSITION_LIMIT_REACHED', 'CIRCUIT_BREAKER_BLOCKED', 'RECONCILIATION_MISMATCH')),
    description             TEXT NOT NULL,
    metadata_json           JSONB,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Dashboard UI Specification & Emergency Controls

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  LIVE REAL-MONEY TRADING CONTROL CENTER                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LIVE SYSTEM STATUS: [ 🟢 TRADING ACTIVE ]  [ DHAN API: CONNECTED ]        │
│  DAILY P&L         : +₹4,500.00 (Max Daily Loss Limit: -₹15,000.00 / 3%)   │
│  OPEN POSITIONS    : 2 / 5 Max Allowed                                      │
│                                                                             │
│  🚨 EMERGENCY CONTROLS                                                      │
│  [ EMERGENCY SQUARE OFF ALL & STOP TRADING ]  <-- RED PHYSICAL KILL SWITCH  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  OPEN REAL-MONEY POSITIONS                                                  │
│  • NIFTY 25000 PE | Qty: 3 Lots | Buy: ₹150.00 | LTP: ₹158.00 | PnL: +₹2,400│
│  [Square Off]  [Modify SL]  [Modify Target]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. FastAPI Endpoints (`/live/*`)

Mounted at `/live` in `src/api/routers/live_engine.py`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/live/status` | Current system health, Dhan API status, and daily PnL |
| `GET` | `/live/positions` | List open real-money positions on Dhan |
| `POST` | `/live/kill-switch` | **EMERGENCY KILL SWITCH: Square off all & halt trading** |
| `POST` | `/live/square-off/{trade_id}` | Manually square off a specific real-money trade |
| `GET` | `/live/tradebook` | Real-money tradebook with VIX/IV snapshots & costs |
| `GET` | `/live/risk-settings` | Get active risk settings & daily loss limits |
| `PUT` | `/live/risk-settings` | Update max daily loss % or exposure caps |
| `POST` | `/live/reconcile` | Force immediate position reconciliation with Dhan broker |

---

## 10. Build Checklist (~26 hours)

| # | Task | File | Est. Time |
|---|---|---|---|
| 1 | Alembic migration for `live_risk_settings`, `live_tradebook`, `live_safety_events` | `alembic/versions/` | 1h |
| 2 | SQLAlchemy Models | `src/live/models.py` | 1h |
| 3 | Dhan API v2 Live Order Execution Adapter | `src/live/dhan_adapter.py` | 5h |
| 4 | Dynamic Option Security ID Resolver | `src/live/security_resolver.py` | 3h |
| 5 | Multi-Layer Safety Guardrails Engine (`safety_guard.py`) | `src/live/safety_guard.py` | 4h |
| 6 | Broker Position Reconciliation Engine | `src/live/reconciler.py` | 3h |
| 7 | Telegram & WhatsApp Instant Notification Bot | `src/utils/telegram_bot.py` | 3h |
| 8 | FastAPI Live Control Router (`/live/*` - 8 endpoints) | `src/api/routers/live_engine.py` | 3h |
| 9 | React UI Emergency Control Panel & Red Kill Switch | frontend | TBD |

---

**Feature 6 (Dhan Live Trading, Risk Guardrails & Safety Engine) is fully finalized.**
