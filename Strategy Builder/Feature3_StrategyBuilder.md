# Feature 3: Strategy Builder, Execution Rule Engine & Python Code Generator
### ShreeNexa — Dhan F&O Algo Trading Integration

> **Status**: Finalized — Ready for Development  
> **ShreeNexa Runtime**: `worker` process (backtest & execution) + `api` process (strategy builder & Python code exporter endpoints) + React UI  
> **Last Updated**: 2026-10-02

---

## Table of Contents

1. [Overview & Dual Execution Architecture](#1-overview--dual-execution-architecture)
2. [4-Part Modular Strategy Definition Schema](#2-4-part-modular-strategy-definition-schema)
3. [Stock Strategy Blueprint](#3-stock-strategy-blueprint)
4. [Options Strategy Blueprint (Dual-Price Reference)](#4-options-strategy-blueprint-dual-price-reference)
5. [MCX Commodity Market Adaptations](#5-mcx-commodity-market-adaptations)
6. [Standalone Python Code Generator & Exporter Module](#6-standalone-python-code-generator--exporter-module)
7. [PostgreSQL Schema & Strategy Versioning](#7-postgresql-schema--strategy-versioning)
8. [FastAPI Endpoints](#8-fastapi-endpoints)
9. [Form-Based Strategy Builder UI Specification](#9-form-based-strategy-builder-ui-specification)
10. [Build Checklist](#10-build-checklist)

---

## 1. Overview & Dual Execution Architecture

The **Strategy Builder Engine** enables creating, parameterizing, versioning, executing, and exporting trading strategies across **Equity (Stocks)**, **Index Options**, **Stock Options**, and **MCX Commodities** without writing code.

Strategies support **Dual Execution Paths**:
1. **Internal Engine Execution**: Strategies are stored as declarative JSON/JSONB in PostgreSQL and evaluated by ShreeNexa's high-speed DuckDB/NumPy interpreter for backtesting, paper trading, and live execution.
2. **Standalone Python Script Export (`code_generator.py`)**: Convert any strategy into a self-contained, fully commented Python file (`.py`) utilizing `dhanhq` SDK, `pandas`, and `ta-lib` to run independently or sell to clients.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FORM-BASED STRATEGY BUILDER (UI)                        │
│                                                                             │
│  ┌─────────────────┐ ┌──────────────────┐ ┌───────────────┐ ┌─────────────┐ │
│  1. Instrument     │ │ 2. Entry         │ │ 3. Stoploss   │ │ 4. Target & │ │
│     Scope & Strike │ │    Conditions    │ │    System     │ │    Trailing │ │
│  └────────┬────────┘ └────────┬─────────┘ └───────┬───────┘ └──────┬──────┘ │
└───────────┼───────────────────┼───────────────────┼────────────────┼────────┘
            └───────────────────┼───────────────────┘                │
                                ▼                                    │
                  FastAPI `/strategy/configs`                        │
                                │                                    │
                                ▼                                    │
                 PostgreSQL `strategy_configs`                       │
                                │                                    │
           ┌────────────────────┴────────────────────┐               │
           ▼                                         ▼               │
┌─────────────────────────────┐         ┌──────────────────────────┐ │
│ INTERNAL INTERPRETER ENGINE │         │ PYTHON CODE GENERATOR    │ │
│ (DuckDB / NumPy / Dhan API) │         │ Export standalone .py    │ ◄┘
│ • Backtest, Paper & Live    │         │ • Run on any VPS/Server  │
│ • Sub-500ms Execution       │         │ • Sell/Share with client │
└─────────────────────────────┘         └──────────────────────────┘
```

---

## 2. 4-Part Modular Strategy Definition Schema

Every strategy is structured into **4 distinct, user-configurable sections**:

```
Part 1: Instrument Scope & Strike Selection
Part 2: Entry Rules & Trigger Conditions
Part 3: Stop-Loss Rules (Fixed / Indicator / Candle Level)
Part 4: Exit Targets & Trailing Stop-Loss Sizing
```

---

## 3. Stock Strategy Blueprint

Applies to Intraday and Positional Equity stocks (NSE / BSE).

```json
{
  "strategy_type": "STOCK",
  "name": "Intraday Breakout Strategy",
  "version": 1,
  
  "part_1_scope": {
    "source_type": "SCREENER",                 
    "screener_config_id": 12,                  
    "fallback_watchlist": ["RELIANCE", "TCS", "INFY", "TATASTEEL"],
    "trading_session": {
      "start_time": "09:16:00",
      "no_new_entries_after": "14:30:00",
      "force_square_off": "15:15:00"
    }
  },

  "part_2_entry": {
    "direction": "LONG",
    "trigger_timeframe": "15min",
    "logic": "AND",
    "conditions": [
      {
        "timeframe": "daily",
        "indicator": "EMA",
        "period": 200,
        "operator": "close_above"
      },
      {
        "timeframe": "15min",
        "indicator": "RSI",
        "period": 14,
        "operator": "crosses_above",
        "value": 60
      }
    ]
  },

  "part_3_stoploss": {
    "sl_type": "CANDLE_LOW",                   
    "candle_lookback": 1,
    "buffer_percentage": 0.2
  },

  "part_4_exit": {
    "targets": [
      { "target_number": 1, "reward_risk_ratio": 2.0, "exit_lots_percentage": 50 },
      { "target_number": 2, "reward_risk_ratio": 4.0, "exit_lots_percentage": 50 }
    ],
    "trailing_sl": {
      "enabled": true,
      "mode": "SPOT_POINTS",
      "trail_after_target": 1,
      "step_points": 10.0
    }
  }
}
```

---

## 4. Options Strategy Blueprint (Dual-Price Reference)

Applies to Index Options (NIFTY, BANKNIFTY, FINNIFTY) and Stock Options (208 F&O Stocks).  
Supports **Dual-Price Reference**: Entry/SL/Exit rules check the **Underlying Spot Price**, the **Option Premium**, or **Both**.

```json
{
  "strategy_type": "OPTION",
  "name": "Nifty Open-High Put Buying",
  "version": 1,

  "part_1_scope": {
    "underlying_symbol": "NIFTY",             
    "option_right": "PE",                      
    "expiry_type": "CURRENT_WEEK",             
    "strike_selection": {
      "mode": "ATM_OFFSET",                    
      "offset": 0                              
    },
    "trading_session": {
      "start_time": "09:16:00",
      "no_new_entries_after": "14:30:00",
      "force_square_off": "15:15:00"
    }
  },

  "part_2_entry": {
    "logic": "AND",
    "conditions": [
      {
        "price_reference": "SPOT",             
        "timeframe": "1min",
        "pattern": "OPEN_EQ_HIGH"
      },
      {
        "price_reference": "SPOT",
        "timeframe": "daily",
        "indicator": "RSI",
        "period": 14,
        "operator": ">",
        "value": 60
      },
      {
        "price_reference": "OPTION_PREMIUM",    
        "timeframe": "1min",
        "indicator": "VOLUME_RATIO",
        "avg_period": 20,
        "operator": ">",
        "value": 1.5
      }
    ]
  },

  "part_3_stoploss": {
    "sl_reference": "OPTION_PREMIUM",          
    "sl_type": "PERCENTAGE",                   
    "percentage_val": 20.0                     
  },

  "part_4_exit": {
    "exit_reference": "OPTION_PREMIUM",
    "targets": [
      { "target_number": 1, "percentage_gain": 30.0, "exit_lots_percentage": 50 },
      { "target_number": 2, "percentage_gain": 60.0, "exit_lots_percentage": 50 }
    ],
    "trailing_sl": {
      "enabled": true,
      "mode": "OPTION_PERCENTAGE",
      "trail_after_target": 1,
      "step_percentage": 10.0
    }
  }
}
```

---

## 5. MCX Commodity Market Adaptations

MCX Commodities (Gold, Gold Mini, Silver, Crude Oil, Natural Gas, Copper) require distinct rules:

| Rule Category | NSE Equity / F&O | MCX Commodities |
|---|---|---|
| **Trading Session** | `09:15:00` to `15:30:00` IST | `09:00:00` to `23:30:00` / `23:55:00` IST |
| **Expiry Rules** | Weekly / Monthly Thursdays | Monthly / Bi-monthly tenders |
| **Lot Size Multipliers** | Stock specific (e.g., RELIANCE 250) | Gold (100), Gold Mini (10), Silver (30), Crude (100) |
| **Tick Sizes** | ₹0.05 | Gold (₹1.00), Crude Oil (₹1.00), Natural Gas (₹0.10) |

---

## 6. Standalone Python Code Generator & Exporter Module (`code_generator.py`)

### Exporter Responsibilities

When the user clicks **`[ 🐍 EXPORT AS STANDALONE PYTHON ALGO SCRIPT (.py) ]`** on the dashboard, `code_generator.py`:
1. Reads the strategy JSON config.
2. Translates all indicator rules, entry conditions, SL/Target logic, and contract resolution into clean, PEP-8 compliant Python code.
3. Generates a self-contained `.py` file incorporating `dhanhq` SDK calls, `pandas`, and `ta-lib` / `ta`.
4. Adds Dhan API authentication headers, error handling, logging, and continuous polling/loop functions.

### Sample Generated Python Output Structure (`nifty_open_high_put_algo.py`)

```python
# ==============================================================================
# STRATEGY: Nifty Open-High Put Buying Strategy
# Generated by ShreeNexa Algo Engine (Standalone Exporter)
# Broker API: Dhan API v2 (dhanhq SDK)
# ==============================================================================

import time
import logging
from dhanhq import dhanhq
import pandas as pd
import ta

# --- BROKER CONFIGURATION ---
CLIENT_ID = "YOUR_DHAN_CLIENT_ID"
ACCESS_TOKEN = "YOUR_DHAN_ACCESS_TOKEN"
dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# --- STRATEGY PARAMETERS ---
UNDERLYING = "NIFTY"
OPTION_RIGHT = "PE"
SL_PERCENTAGE = 20.0
TARGET_PERCENTAGE = 40.0
QUANTITY_LOTS = 1

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def check_entry_conditions():
    # 1. Fetch 1-min candle for spot
    # 2. Check Open == High
    # 3. Fetch daily RSI and verify > 60
    pass


def execute_dhan_order(security_id, transaction_type, qty):
    # Sends live order via dhanhq SDK
    pass


def main():
    logging.info("🚀 Starting Standalone Dhan Algo Script for NIFTY PE...")
    while True:
        try:
            if check_entry_conditions():
                logging.info("🎯 Signal Triggered! Executing Order...")
                # Order execution and SL/Target tracking loop
            time.sleep(60)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")


if __name__ == "__main__":
    main()
```

---

## 7. PostgreSQL Schema & Strategy Versioning

```sql
-- Master Strategy Configurations
CREATE TABLE strategy_configs (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    strategy_type       TEXT NOT NULL CHECK (strategy_type IN ('STOCK', 'OPTION', 'MCX_FUTURES', 'MCX_OPTION')),
    current_version     INTEGER DEFAULT 1,
    is_active           BOOLEAN DEFAULT TRUE,
    config_json         JSONB NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Strategy Version History (enables strategy versioning)
CREATE TABLE strategy_versions (
    id                  SERIAL PRIMARY KEY,
    strategy_id         INTEGER REFERENCES strategy_configs(id) ON DELETE CASCADE,
    version             INTEGER NOT NULL,
    change_summary      TEXT,
    config_json         JSONB NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (strategy_id, version)
);
```

---

## 8. FastAPI Endpoints (`/strategy/*`)

Mounted at `/strategy` in `src/api/routers/strategy.py`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/strategy/configs` | Create a new strategy |
| `GET` | `/strategy/configs` | List all saved strategies (with filter by type) |
| `GET` | `/strategy/configs/{id}` | Get strategy detail JSON |
| `PUT` | `/strategy/configs/{id}` | Update strategy (auto-increments version) |
| `DELETE` | `/strategy/configs/{id}` | Delete strategy |
| `GET` | `/strategy/configs/{id}/versions` | List version history |
| `POST` | `/strategy/configs/{id}/export-json` | Export strategy JSON/YAML |
| `POST` | `/strategy/configs/{id}/export-python` | **Export standalone Python script (.py)** |
| `POST` | `/strategy/configs/import` | Import strategy JSON/YAML |

---

## 9. Form-Based Strategy Builder UI Specification

A step-by-step visual wizard built in **React + TypeScript**:

```
Step 1: Basic Info & Segment (Stock / Option / MCX)
Step 2: Instrument Scope (Watchlist or Screener selection + Strike Selection)
Step 3: Entry Rules Builder (Multi-timeframe + Spot/Option indicator dropdowns)
Step 4: Stoploss Configuration (Fixed % / Points / Indicator / Candle level)
Step 5: Targets & Trailing Stoploss Setup (Multi-target lot exit % + Trailing steps)

UI ACTION BUTTONS:
[ ▶ SAVE & RUN BACKTEST ]  [ 🐍 EXPORT AS STANDALONE PYTHON ALGO (.py) ]  [ 📄 EXPORT JSON ]
```

---

## 10. Build Checklist (~28 hours)

| # | Task | File | Est. Time |
|---|---|---|---|
| 1 | Alembic migration for `strategy_configs` & `strategy_versions` | `alembic/versions/` | 1h |
| 2 | SQLAlchemy Models | `src/strategy/models.py` | 1h |
| 3 | Core Strategy Parser & Validation Engine | `src/strategy/parser.py` | 4h |
| 4 | Options Strike & Expiry Resolver Module | `src/strategy/strike_resolver.py` | 3h |
| 5 | Dual-Price Indicator Evaluator (Spot + Option) | `src/strategy/evaluator.py` | 4h |
| 6 | MCX Hours & Session Constraint Handler | `src/strategy/mcx_handler.py` | 2h |
| 7 | **Standalone Python Code Generator (`code_generator.py`)** | `src/strategy/code_generator.py` | 4h |
| 8 | FastAPI Strategy Router (9 routes including Python Exporter) | `src/api/routers/strategy.py` | 3h |
| 9 | Strategy Export/Import Manager (JSON/YAML/Python) | `src/strategy/importer.py` | 2h |
| 10 | Integration Unit Tests (Stock, Option, MCX, Python Exporter) | `tests/test_strategy.py` | 4h |

---

**Feature 3 is fully updated and finalized.**
