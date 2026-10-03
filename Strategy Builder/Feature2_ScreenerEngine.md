# Feature 2: Dynamic Screener Engine
### ShreeNexa — Dhan F&O Algo Trading Integration

> **Status**: Finalized — Ready for Development
> **ShreeNexa Runtime**: `worker` process (scan execution) + `api` process (routes)
> **Last Updated**: 2026-10-02

---

## Table of Contents

1. [Overview & Two Modes](#1-overview--two-modes)
2. [Condition Schema — AND / OR Tree](#2-condition-schema--and--or-tree)
3. [Supported Indicators](#3-supported-indicators)
4. [Timeframe Aggregation](#4-timeframe-aggregation)
5. [PostgreSQL Schema](#5-postgresql-schema)
6. [FastAPI Endpoints](#6-fastapi-endpoints)
7. [File Structure](#7-file-structure)
8. [How Modes Differ](#8-how-modes-differ)
9. [Build Checklist](#9-build-checklist)

---

## 1. Overview & Two Modes

The Screener Engine is a **shared module** serving two distinct use cases from one engine:

```
┌─────────────────────────────────┐  ┌──────────────────────────────────┐
│   MODE 1: STRATEGY MODE         │  │   MODE 2: LIVE SCAN MODE         │
│                                 │  │                                  │
│  Called by: Strategy Engine     │  │  Called by: User clicks Run Scan │
│  At: specific candle time       │  │  At: any time, on demand         │
│                                 │  │                                  │
│  e.g. Find Open=High stocks     │  │  e.g. RSI > 60 on Monthly        │
│  in top loser sectors at 09:16  │  │  AND RSI > 60 on Weekly          │
│                                 │  │  AND 35 < RSI < 45 on Daily      │
│  Returns → Tradeable list       │  │                                  │
│  fed into strategy logic        │  │  Returns → Watchlist snapshot    │
│                                 │  │  displayed in terminal panel     │
└─────────────────────────────────┘  └──────────────────────────────────┘
                   │                               │
       ┌───────────▼───────────────────────────────▼──────────┐
       │                    SHARED CORE                        │
       │  1. Load universe from ShreeNexa existing instruments │
       │  2. Aggregate 1-min Parquet → requested timeframe     │
       │  3. Compute indicators via DuckDB SQL                 │
       │  4. Evaluate AND / OR condition tree                  │
       │  5. Return matched symbols + indicator values         │
       └───────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Manual trigger only** — No auto-refresh, no background polling.
- **Universe from ShreeNexa** — Uses existing instrument universe; no duplication.
- **DuckDB for computation** — All indicator math runs as SQL over Parquet files.
- **Saved configs** — Screener conditions stored in PostgreSQL as reusable named configs.
- **Static snapshot output** — Point-in-time result; no live-updating watchlist.

---

## 2. Condition Schema — AND / OR Tree

Conditions stored in PostgreSQL as **JSONB** — recursive AND/OR nesting,
no custom query language needed.

### Structure Rules

- A **group node** has `"logic": "AND"` or `"logic": "OR"` and a `"conditions"` array.
- A **leaf node** has `indicator`, `period` (optional), `timeframe`, `operator`, `value`.
- Groups can be nested inside other groups (fully recursive).

### Example 1 — Your RSI Multi-Timeframe Setup (pure AND)

```json
{
  "logic": "AND",
  "conditions": [
    {
      "indicator": "RSI",
      "period": 14,
      "timeframe": "monthly",
      "operator": ">",
      "value": 60
    },
    {
      "indicator": "RSI",
      "period": 14,
      "timeframe": "weekly",
      "operator": ">",
      "value": 60
    },
    {
      "indicator": "RSI",
      "period": 14,
      "timeframe": "daily",
      "operator": "between",
      "value": [35, 45]
    }
  ]
}
```

### Example 2 — With Nested OR Group

```json
{
  "logic": "AND",
  "conditions": [
    {
      "indicator": "RSI",
      "period": 14,
      "timeframe": "monthly",
      "operator": ">",
      "value": 60
    },
    {
      "logic": "OR",
      "conditions": [
        {
          "indicator": "EMA",
          "period": 200,
          "timeframe": "daily",
          "operator": "close_above"
        },
        {
          "indicator": "VOLUME_RATIO",
          "avg_period": 20,
          "timeframe": "daily",
          "operator": ">",
          "value": 1.5
        }
      ]
    }
  ]
}
```

### Supported Operators

| Operator        | Description                      | Example                     |
|-----------------|----------------------------------|-----------------------------|
| `>`             | Greater than                     | `RSI > 60`                  |
| `<`             | Less than                        | `RSI < 40`                  |
| `>=`            | Greater than or equal            | `RSI >= 60`                 |
| `<=`            | Less than or equal               | `RSI <= 40`                 |
| `=`             | Equals                           | `RSI = 50`                  |
| `between`       | Inclusive range                  | `RSI between [35, 45]`      |
| `close_above`   | Close above indicator value      | `Close > EMA(200)`          |
| `close_below`   | Close below indicator value      | `Close < EMA(200)`          |
| `crosses_above` | Crosses above vs previous bar    | `MACD crosses Signal`       |
| `crosses_below` | Crosses below vs previous bar    | `MACD crosses below Signal` |
| `is_bullish`    | Indicator state is bullish       | `Supertrend is_bullish`     |
| `is_bearish`    | Indicator state is bearish       | `Supertrend is_bearish`     |

---

## 3. Supported Indicators

### Phase 1 — Initial Indicator Library (10 indicators)

| Indicator       | Parameters                   | Operator Support                       | Notes                            |
|-----------------|------------------------------|----------------------------------------|----------------------------------|
| **RSI**         | `period` (default 14)        | `>`, `<`, `>=`, `<=`, `=`, `between`  | All timeframes                   |
| **EMA**         | `period`                     | `close_above/below`, `crosses_*`      | All timeframes                   |
| **SMA**         | `period`                     | `close_above/below`, `crosses_*`      | All timeframes                   |
| **MACD**        | `fast`(12), `slow`(26), `signal`(9) | `crosses_*`, `>`, `<`         | MACD line vs Signal line         |
| **Bollinger Bands** | `period`(20), `std_dev`(2) | `close_above/below`                 | Upper/lower band as reference    |
| **VWAP**        | none                         | `close_above/below`                   | Intraday only (1min–4h), resets daily |
| **Volume Ratio**| `avg_period` (default 20)    | `>`, `<`, `between`                   | `current_vol / avg_vol`          |
| **ATR**         | `period` (default 14)        | `>`, `<`, `between`                   | Volatility filter                |
| **Supertrend**  | `period`(10), `multiplier`(3) | `is_bullish`, `is_bearish`           | State-based                      |
| **OI Change %** | `period` (default 1 day)     | `>`, `<`, `between`                   | F&O instruments only             |

### Candlestick Pattern Conditions

| Pattern Code        | Condition Logic                                   |
|---------------------|---------------------------------------------------|
| `OPEN_EQ_HIGH`      | `open == high` on last closed candle              |
| `OPEN_EQ_LOW`       | `open == low` on last closed candle               |
| `INSIDE_BAR`        | `high < prev_high AND low > prev_low`             |
| `BULLISH_ENGULFING` | Current body engulfs previous bearish candle body |
| `BEARISH_ENGULFING` | Current body engulfs previous bullish candle body |

---

## 4. Timeframe Aggregation

Only **1-minute base candles** are stored in Parquet. All higher timeframes are
computed at scan time via DuckDB SQL aggregation — no pre-computed storage needed.

| Requested TF | DuckDB Grouping                                    |
|--------------|----------------------------------------------------|
| `1min`       | Raw data — no aggregation                          |
| `5min`       | `time_bucket('5 minutes', datetime_ist)`           |
| `15min`      | `time_bucket('15 minutes', datetime_ist)`          |
| `1h`         | `time_bucket('1 hour', datetime_ist)`              |
| `4h`         | `time_bucket('4 hours', datetime_ist)`             |
| `daily`      | `DATE(datetime_ist AT TIME ZONE 'Asia/Kolkata')`   |
| `weekly`     | `DATE_TRUNC('week', datetime_ist)`                 |
| `monthly`    | `DATE_TRUNC('month', datetime_ist)`                |

**OHLCV aggregation rules**: O=first, H=MAX, L=MIN, C=last, V=SUM, OI=last per bucket.

---

## 5. PostgreSQL Schema

### `screener_configs` — Saved Screener Configurations

```sql
CREATE TABLE screener_configs (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    description      TEXT,
    universe_filter  TEXT DEFAULT 'FNO_208',   -- Any segment code
    condition_tree   JSONB NOT NULL,            -- AND/OR nested condition JSON
    is_strategy_mode BOOLEAN DEFAULT FALSE,     -- TRUE = called by strategy engine
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_screener_configs_universe ON screener_configs(universe_filter);
```

### `screener_results` — Scan Run History

```sql
CREATE TABLE screener_results (
    id               SERIAL PRIMARY KEY,
    config_id        INTEGER REFERENCES screener_configs(id) ON DELETE SET NULL,
    run_at           TIMESTAMPTZ DEFAULT NOW(),
    matched_symbols  TEXT[],                   -- Array of matched symbol strings
    total_scanned    INTEGER,
    total_matched    INTEGER,
    run_duration_ms  INTEGER,
    result_snapshot  JSONB                     -- Full result with per-stock indicator values
);

CREATE INDEX idx_screener_results_config ON screener_results(config_id, run_at DESC);
```

---

## 6. FastAPI Endpoints

New router: `src/api/routers/screener.py` — mounted at `/screener`

| Method   | Endpoint                 | Description                                |
|----------|--------------------------|--------------------------------------------|
| `POST`   | `/screener/configs`      | Save a new screener configuration          |
| `GET`    | `/screener/configs`      | List all saved screener configs            |
| `GET`    | `/screener/configs/{id}` | Get one config with full condition tree    |
| `PUT`    | `/screener/configs/{id}` | Update an existing screener config         |
| `DELETE` | `/screener/configs/{id}` | Delete a screener config                   |
| `POST`   | `/screener/run/{id}`     | **Run scan manually — returns results**    |
| `GET`    | `/screener/results/{id}` | Get results of a previous run              |
| `GET`    | `/screener/results`      | Run history for a config (`?config_id=N`)  |

### `POST /screener/run/{id}` — Response Shape

```json
{
  "run_id": 42,
  "config_name": "RSI Pullback Setup",
  "universe": "FNO_208",
  "total_scanned": 208,
  "total_matched": 14,
  "duration_ms": 312,
  "run_at": "2026-10-02T15:30:00+05:30",
  "results": [
    {
      "symbol": "RELIANCE",
      "display_name": "Reliance Industries Ltd",
      "segments": ["INDEX_NIFTY50", "SECTOR_ENERGY", "FNO_208"],
      "last_close": 2543.50,
      "change_pct": -0.82,
      "volume": 1234567,
      "indicator_values": {
        "RSI_14_monthly": 63.2,
        "RSI_14_weekly": 61.8,
        "RSI_14_daily": 41.3
      },
      "conditions_met": [
        "RSI_monthly > 60 ✓",
        "RSI_weekly > 60 ✓",
        "RSI_daily BETWEEN 35-45 ✓"
      ]
    }
  ]
}
```

---

## 7. File Structure

```
src/
├── api/
│   └── routers/
│       └── screener.py             # 8 FastAPI endpoints
│
└── screener/
    ├── __init__.py
    ├── engine.py                   # Orchestrator: universe → aggregate → compute → evaluate
    ├── aggregator.py               # 1-min Parquet → any timeframe via DuckDB SQL
    ├── indicators.py               # All 10 indicators + 5 candlestick patterns
    ├── condition_evaluator.py      # Recursive AND/OR JSON tree walker
    └── models.py                   # SQLAlchemy: screener_configs, screener_results
```

### `condition_evaluator.py` — Core Recursive Logic

```python
def evaluate(node: dict, indicator_row: dict) -> bool:
    if "logic" in node:  # Group node
        results = [evaluate(c, indicator_row) for c in node["conditions"]]
        return all(results) if node["logic"] == "AND" else any(results)
    else:  # Leaf condition
        return evaluate_leaf(node, indicator_row)
```

### `engine.py` — Orchestration Flow

```
1. Receive config_id + optional universe override
2. Load condition_tree and universe_filter from DB
3. Fetch all instrument_ids for universe from ShreeNexa instruments
4. For each unique timeframe required in conditions:
   a. Call aggregator.py → build TF candles via DuckDB
   b. Call indicators.py → compute required indicators
5. For each instrument, call condition_evaluator.py
6. Collect matched instruments → build result payload
7. Persist to screener_results
8. Return result to API layer
```

---

## 8. How Modes Differ

| Aspect               | Mode 1: Strategy Mode                | Mode 2: Live Scan Mode               |
|----------------------|--------------------------------------|--------------------------------------|
| **Trigger**          | Strategy Engine internally           | User clicks "Run Scan" in UI         |
| **Timing**           | At backtest candle or live time      | On demand, any time                  |
| **Universe**         | Defined per strategy config          | Defined per screener config          |
| **Output consumer**  | Strategy `on_candle()` receives list | Terminal UI watchlist panel          |
| **Result persistence**| Optional                            | Always stored in `screener_results`  |
| **Example**          | Open=High filter at 09:16           | RSI pullback stocks for manual review|

---

## 9. Build Checklist (~17 hours backend)

| #  | Task                                                        | Est.  |
|----|-------------------------------------------------------------|-------|
| 1  | Alembic: `screener_configs` + `screener_results`            | 0.5h  |
| 2  | `models.py` — SQLAlchemy models                             | 0.5h  |
| 3  | `aggregator.py` — 1-min → 8 timeframes via DuckDB          | 2h    |
| 4  | `indicators.py` — RSI, EMA, SMA, MACD, Bollinger Bands      | 3h    |
| 5  | `indicators.py` — VWAP, Volume Ratio, ATR, Supertrend, OI, Candlestick | 3h |
| 6  | `condition_evaluator.py` — recursive AND/OR tree walker     | 2h    |
| 7  | `engine.py` — full scan pipeline orchestrator               | 2h    |
| 8  | `screener.py` FastAPI router — 8 endpoints                  | 2h    |
| 9  | Integration test: RSI Monthly + Weekly + Daily example      | 1h    |
| 10 | Strategy Mode integration hook (Feature 3 entry point)      | 1h    |
| 11 | React UI: Screener Builder (condition tree editor)          | TBD   |
| 12 | React UI: Scan Results Watchlist Panel                      | TBD   |

**Total Backend Dev Time: ~17 hours**

---

## Open Items

| Item                               | Notes                                           |
|------------------------------------|-------------------------------------------------|
| Frontend screener builder UI       | Design to be confirmed when building UI         |
| Watchlist panel live data display  | Details to be given at UI build time            |
| Phase 2 indicators                 | PCR, India VIX overlay, Pivot Points            |
