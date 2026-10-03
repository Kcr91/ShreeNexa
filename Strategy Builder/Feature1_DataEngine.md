# Feature 1: Data Engine & Storage Pipeline
### ShreeNexa — Dhan F&O Algo Trading Integration

> **Status**: Finalized — Ready for Development
> **ShreeNexa Runtime**: `worker` process (tasks) + `api` process (routes)
> **Last Updated**: 2026-10-02

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [Existing CSV Structure](#2-existing-csv-structure)
3. [PostgreSQL Schema](#3-postgresql-schema)
4. [NSE Segment Groups](#4-nse-segment-groups)
5. [Parquet Warehouse Layout](#5-parquet-warehouse-layout)
6. [Worker Task Modules](#6-worker-task-modules)
7. [FastAPI Endpoints](#7-fastapi-endpoints)
8. [API Quota Manager](#8-api-quota-manager)
9. [Build Checklist](#9-build-checklist)

---

## 1. Overview & Architecture

The Data Engine runs inside ShreeNexa's existing `worker` runtime process. It integrates
with the **existing ShreeNexa instrument universe** — no new instrument/segment tables are
created if they already exist. OHLCV data tables are the only net-new schema additions.

```
worker process
  A. BULK IMPORTER       — Local CSV → PostgreSQL + Parquet  (one-time)
  B. INCREMENTAL UPDATER — Dhan API → PostgreSQL + Parquet   (daily 4PM IST + manual)
  C. PARQUET ARCHIVER    — PostgreSQL rows → Parquet append   (after each sync)

Storage
  PostgreSQL  mkt_ohlcv_equity / mkt_ohlcv_futures / mkt_ohlcv_options
  Parquet     data/market/equity | futures | options / ...
  Redis       mkt:quota:{date}  (shared budget with feedd process)

api process
  11 FastAPI routes at /data/*  (query, sync control, CSV export)
```

### Key Design Principles

- **Reuse ShreeNexa universe**: All OHLCV tables reference the existing instrument
  table via foreign key. No duplicate instrument or segment definitions.
- **Dual storage**: PostgreSQL for transactional queries & API responses; Parquet
  for DuckDB-powered high-speed backtesting.
- **Resumable**: Bulk import and incremental sync are both interruptible and
  resumable via `mkt_download_state`.
- **Quota-aware**: All Dhan API requests metered against a shared Redis budget
  (100,000 requests/day) shared with the `feedd` process.

---

## 2. Existing CSV Structure

### 2.1 Confirmed File Layout (Your Downloads)

```
<base_csv_path>/
 RELIANCE.csv                           Equity spot OHLCV
 NIFTY.csv                              Index spot OHLCV

 RELIANCE/
   Month_1/
     ATM_Call.csv    ATM_Put.csv        ATM CE/PE, Month 1 expiry
     ATM+1_Call.csv  ATM+1_Put.csv
     ATM-1_Call.csv  ATM-1_Put.csv
     ...
     ATM-3_Put.csv                      Stocks: ATM ± 3 strikes
   Month_2/
   Month_3/

 NIFTY/
   Month_1/
     ATM_Call.csv
     ATM+10_Call.csv ... ATM-10_Put.csv  Index: ATM ± 10 strikes
   Week_1/  Week_2/  Week_3/  Week_4/
```

### 2.2 CSV Column Mapping

All CSV files share this confirmed column structure:

| CSV Column     | DB Column        | Type            | Notes                        |
|----------------|------------------|-----------------|------------------------------|
| `timestamp`    | `ts`             | `BIGINT`        | Unix epoch milliseconds IST  |
| `datetime_ist` | `datetime_ist`   | `TIMESTAMPTZ`   | IST stored as UTC+05:30      |
| `open`         | `open`           | `NUMERIC(12,4)` |                              |
| `high`         | `high`           | `NUMERIC(12,4)` |                              |
| `low`          | `low`            | `NUMERIC(12,4)` |                              |
| `close`        | `close`          | `NUMERIC(12,4)` |                              |
| `volume`       | `volume`         | `BIGINT`        |                              |
| `open_interest`| `oi`             | `BIGINT`        | NULL for equity spot         |
| `iv`           | `iv`             | `NUMERIC(8,4)`  | NULL for equity/futures      |
| `spot`         | `underlying_spot`| `NUMERIC(12,4)` | NULL for equity spot table   |
| `strike`       | —                | —               | Stored in instruments table  |

### 2.3 Path-to-Instrument Parser Rules

The bulk importer derives instrument metadata purely from the file path:

| File Path Pattern                    | Parsed As                            |
|--------------------------------------|--------------------------------------|
| `{SYMBOL}.csv`                       | type=EQ                              |
| `{SYMBOL}/Month_{N}/ATM_Call.csv`    | type=CE, monthly expiry, offset=0    |
| `{SYMBOL}/Month_{N}/ATM+{X}_Call.csv`| type=CE, strike offset +X above ATM |
| `{SYMBOL}/Month_{N}/ATM-{X}_Put.csv` | type=PE, strike offset -X below ATM |
| `{SYMBOL}/Week_{N}/ATM_Call.csv`     | type=CE, weekly expiry, offset=0     |

---

## 3. PostgreSQL Schema

> All new tables prefixed `mkt_` to avoid collision with existing ShreeNexa tables.
> Managed via existing **Alembic** migrations.
> All instrument FKs reference **ShreeNexa's existing instrument table**.

### 3.1 `mkt_ohlcv_equity` — Equity & Index OHLCV

```sql
CREATE TABLE mkt_ohlcv_equity (
    instrument_id   INTEGER NOT NULL,  -- FK → ShreeNexa existing instruments table
    datetime_ist    TIMESTAMPTZ NOT NULL,
    open            NUMERIC(12,4) NOT NULL,
    high            NUMERIC(12,4) NOT NULL,
    low             NUMERIC(12,4) NOT NULL,
    close           NUMERIC(12,4) NOT NULL,
    volume          BIGINT DEFAULT 0,
    PRIMARY KEY (instrument_id, datetime_ist)
) PARTITION BY RANGE (datetime_ist);

CREATE TABLE mkt_ohlcv_equity_2021 PARTITION OF mkt_ohlcv_equity FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE mkt_ohlcv_equity_2022 PARTITION OF mkt_ohlcv_equity FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE mkt_ohlcv_equity_2023 PARTITION OF mkt_ohlcv_equity FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE mkt_ohlcv_equity_2024 PARTITION OF mkt_ohlcv_equity FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE mkt_ohlcv_equity_2025 PARTITION OF mkt_ohlcv_equity FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE mkt_ohlcv_equity_2026 PARTITION OF mkt_ohlcv_equity FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX idx_mkt_eq_inst_ts ON mkt_ohlcv_equity (instrument_id, datetime_ist DESC);
```

### 3.2 `mkt_ohlcv_futures` — Futures OHLCV

```sql
CREATE TABLE mkt_ohlcv_futures (
    instrument_id   INTEGER NOT NULL,
    datetime_ist    TIMESTAMPTZ NOT NULL,
    open            NUMERIC(12,4) NOT NULL,
    high            NUMERIC(12,4) NOT NULL,
    low             NUMERIC(12,4) NOT NULL,
    close           NUMERIC(12,4) NOT NULL,
    volume          BIGINT DEFAULT 0,
    oi              BIGINT DEFAULT 0,
    underlying_spot NUMERIC(12,4),
    PRIMARY KEY (instrument_id, datetime_ist)
) PARTITION BY RANGE (datetime_ist);

-- Same yearly partition pattern as equity (2021–2026)
```

### 3.3 `mkt_ohlcv_options` — Options OHLCV

```sql
CREATE TABLE mkt_ohlcv_options (
    instrument_id   INTEGER NOT NULL,
    datetime_ist    TIMESTAMPTZ NOT NULL,
    open            NUMERIC(12,4) NOT NULL,
    high            NUMERIC(12,4) NOT NULL,
    low             NUMERIC(12,4) NOT NULL,
    close           NUMERIC(12,4) NOT NULL,
    volume          BIGINT DEFAULT 0,
    oi              BIGINT DEFAULT 0,
    iv              NUMERIC(8,4),           -- Implied Volatility %
    underlying_spot NUMERIC(12,4),
    PRIMARY KEY (instrument_id, datetime_ist)
) PARTITION BY RANGE (datetime_ist);

-- Same yearly partition pattern (2021–2026)
CREATE INDEX idx_mkt_opt_inst_ts ON mkt_ohlcv_options (instrument_id, datetime_ist DESC);
```

### 3.4 `mkt_download_state` — Per-Instrument Sync Tracker

```sql
CREATE TABLE mkt_download_state (
    instrument_id     INTEGER PRIMARY KEY,  -- FK → ShreeNexa instruments table
    last_candle_ts    TIMESTAMPTZ,          -- Last successfully stored candle
    last_sync_at      TIMESTAMPTZ,
    sync_status       TEXT DEFAULT 'PENDING'
        CHECK (sync_status IN ('PENDING','RUNNING','DONE','FAILED')),
    error_message     TEXT,
    total_candles     BIGINT DEFAULT 0,
    api_requests_used INTEGER DEFAULT 0
);
```

### 3.5 `mkt_api_quota` — Daily API Budget Ledger

```sql
CREATE TABLE mkt_api_quota (
    date            DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    daily_limit     INTEGER DEFAULT 100000,
    used_historical INTEGER DEFAULT 0,   -- Consumed by data engine
    used_live       INTEGER DEFAULT 0,   -- Consumed by feedd process
    reserved_live   INTEGER DEFAULT 5000,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. NSE Segment Groups

> Seeded INTO ShreeNexa's existing segment/group tables — not new tables.
> 27 segments total.

| Code                       | Name                          | Category |
|----------------------------|-------------------------------|----------|
| `INDEX_NIFTY50`            | Nifty 50                      | INDEX    |
| `INDEX_NIFTY_NEXT50`       | Nifty Next 50                 | INDEX    |
| `INDEX_NIFTY500`           | Nifty 500                     | INDEX    |
| `INDEX_NIFTY_MIDCAP150`    | Nifty Midcap 150              | INDEX    |
| `INDEX_NIFTY_SMALLCAP250`  | Nifty Smallcap 250            | INDEX    |
| `INDEX_NIFTY_MIDSMALLCAP400` | Nifty MidSmallcap 400       | INDEX    |
| `INDEX_BANKNIFTY`          | Nifty Bank (Bank Nifty)       | INDEX    |
| `INDEX_FINNIFTY`           | Nifty Financial Services      | INDEX    |
| `INDEX_MIDCPNIFTY`         | Nifty Midcap Select           | INDEX    |
| `INDEX_SENSEX`             | BSE Sensex 30                 | INDEX    |
| `INDEX_SENSEX50`           | BSE Sensex 50                 | INDEX    |
| `FNO_208`                  | NSE F&O Eligible Stocks (208) | EQUITY   |
| `SECTOR_BANK`              | Nifty Bank Sector             | SECTOR   |
| `SECTOR_IT`                | Nifty IT Sector               | SECTOR   |
| `SECTOR_AUTO`              | Nifty Auto Sector             | SECTOR   |
| `SECTOR_PHARMA`            | Nifty Pharma Sector           | SECTOR   |
| `SECTOR_METAL`             | Nifty Metal Sector            | SECTOR   |
| `SECTOR_ENERGY`            | Nifty Energy (Oil & Gas)      | SECTOR   |
| `SECTOR_FMCG`              | Nifty FMCG Sector             | SECTOR   |
| `SECTOR_REALTY`            | Nifty Realty Sector           | SECTOR   |
| `SECTOR_MEDIA`             | Nifty Media Sector            | SECTOR   |
| `SECTOR_HEALTHCARE`        | Nifty Healthcare Sector       | SECTOR   |
| `SECTOR_INFRA`             | Nifty Infra Sector            | SECTOR   |
| `SECTOR_PSE`               | Nifty PSE (Public Sector)     | SECTOR   |
| `SECTOR_PSU_BANK`          | Nifty PSU Bank                | SECTOR   |
| `SECTOR_PRIVATE_BANK`      | Nifty Private Bank            | SECTOR   |
| `SECTOR_MNC`               | Nifty MNC                     | SECTOR   |

---

## 5. Parquet Warehouse Layout

Stored inside ShreeNexa's existing `data/` directory:

```
data/
└── market/
    ├── equity/
    │   └── {SYMBOL}/
    │       └── {YEAR}/
    │           └── {MM}.parquet
    │           # e.g. data/market/equity/RELIANCE/2024/01.parquet
    │
    ├── futures/
    │   └── {SYMBOL}/
    │       └── {EXPIRY_YYYY_MM}/
    │           └── candles.parquet
    │           # e.g. data/market/futures/RELIANCE/2024_01/candles.parquet
    │
    └── options/
        └── {SYMBOL}/
            └── {EXPIRY_YYYY_MM}/
                └── {STRIKE}_{CE|PE}.parquet
                # e.g. data/market/options/RELIANCE/2024_01/2500.00_CE.parquet
```

### DuckDB Query Examples (used by Strategy Engine)

```sql
-- All RELIANCE equity candles Q1 2024
SELECT * FROM read_parquet('data/market/equity/RELIANCE/2024/0[123].parquet')
WHERE datetime_ist BETWEEN '2024-01-01' AND '2024-03-31'
ORDER BY datetime_ist;

-- All NIFTY ATM options January 2024 expiry
SELECT * FROM read_parquet('data/market/options/NIFTY/2024_01/*.parquet')
ORDER BY datetime_ist;
```

---

## 6. Worker Task Modules

### File Structure (inside ShreeNexa `worker/`)

```
worker/
└── tasks/
    └── data_engine/
        ├── __init__.py
        ├── bulk_importer.py        # A: Local CSV → PostgreSQL + Parquet
        ├── incremental_updater.py  # B: Dhan API → PostgreSQL + Parquet
        ├── parquet_archiver.py     # C: PostgreSQL rows → Parquet append
        ├── segment_seeder.py       # D: Seed 27 NSE segments into existing tables
        ├── quota_manager.py        # Shared Redis quota tracker
        └── models.py               # SQLAlchemy models for mkt_* tables
```

### A. Bulk Importer (`bulk_importer.py`)

**Purpose**: One-time job. Reads all existing 5-year local CSVs into PostgreSQL + Parquet.

```
1. Scan base_csv_path recursively → collect all CSV file paths
2. Parse instrument metadata from path structure (see §2.3)
3. Look up instrument_id from ShreeNexa's existing instruments table
4. Read CSV → validate columns → batch upsert (5,000 rows/batch)
5. Write/append Parquet partition file
6. Update mkt_download_state.last_candle_ts
7. Log progress to stdout
```

Config in `config.yaml`:
```yaml
data_engine:
  bulk_import:
    base_csv_path: "C:/path/to/your/csv/data"
    batch_size: 5000
    skip_existing: true    # Skip instruments already fully loaded
    dry_run: false         # Set true to test without DB writes
```

### B. Incremental Updater (`incremental_updater.py`)

**Purpose**: Downloads missing candles from `last_candle_ts + 1min` to today via Dhan API.

**Scheduling**:
- **Auto**: 16:00 IST daily via `worker/scheduler.py`
- **Manual**: `POST /data/sync/start`
- **During paper trading**: Runs in background using remaining quota

**Daily Quota Budget**:

| Category                              | Requests/Day |
|---------------------------------------|--------------|
| Equity incremental (208 + indices)    | ~215         |
| Futures incremental                   | ~215         |
| Stock options (ATM±3 × 208 × CE+PE)  | ~2,912       |
| Index options (ATM±10 × 3 × CE+PE)   | ~126         |
| **Total daily sync**                  | **~3,468**   |
| **Remaining for paper/live**          | **~91,532**  |

### C. Parquet Archiver (`parquet_archiver.py`)

- Runs automatically after each incremental batch.
- **Append-only** — never rewrites existing Parquet partitions.
- Appends new rows to the correct monthly Parquet file.

---

## 7. FastAPI Endpoints

New router: `src/api/routers/data_engine.py` — mounted at `/data`

| Method | Endpoint                      | Description                                      |
|--------|-------------------------------|--------------------------------------------------|
| `GET`  | `/data/instruments`           | List — filter by `segment`, `type`, `symbol`     |
| `GET`  | `/data/instruments/{symbol}`  | Detail + download state + last candle date       |
| `GET`  | `/data/candles/{symbol}`      | OHLCV with `type`, `from`, `to`, `strike` params |
| `GET`  | `/data/segments`              | List all 27 segments with constituent count      |
| `GET`  | `/data/segments/{code}/stocks`| All instruments in a segment                     |
| `POST` | `/data/sync/start`            | Trigger manual incremental sync                  |
| `POST` | `/data/sync/pause`            | Pause running sync job                           |
| `POST` | `/data/sync/resume`           | Resume paused sync job                           |
| `GET`  | `/data/sync/status`           | Live progress (WebSocket upgradeable)            |
| `GET`  | `/data/quota`                 | Today's budget — used / remaining / reserved     |
| `GET`  | `/data/export`                | Streaming CSV download                           |

### CSV Export — `GET /data/export`

```
?symbol=RELIANCE
&type=CE                      # EQ | FUT | CE | PE
&from=2024-01-01
&to=2024-03-31
&strike=2500
&expiry=2024-01-25
&segment=SECTOR_ENERGY        # Export all stocks in segment
&columns=datetime_ist,open,high,low,close,volume,oi,iv,underlying_spot
```

Response: streaming `text/csv` with `Content-Disposition: attachment` header.

---

## 8. API Quota Manager

Shared between `worker` and `feedd` via **Redis** (existing ShreeNexa Redis):

```
Redis Key  : mkt:quota:{YYYY-MM-DD}
Type       : Hash
TTL        : 48 hours
Fields     : limit | used_historical | used_live | reserved_live
```

Guard function called before every Dhan historical API request:

```python
async def can_make_historical_request() -> bool:
    quota = await redis.hgetall(f"mkt:quota:{today}")
    available = int(quota["limit"]) - int(quota["used_historical"]) - int(quota["reserved_live"])
    return available > 0
```

---

## 9. Build Checklist (~33 hours)

| #  | Task                                                   | Est.  |
|----|--------------------------------------------------------|-------|
| 1  | Review ShreeNexa existing instrument table schema      | 1h    |
| 2  | Alembic: `mkt_ohlcv_*` tables + yearly partitions     | 2h    |
| 3  | Alembic: `mkt_download_state` + `mkt_api_quota`       | 0.5h  |
| 4  | `segment_seeder.py` — 27 NSE segments                  | 2h    |
| 5  | `models.py` — SQLAlchemy for all `mkt_*` tables       | 1h    |
| 6  | `quota_manager.py` — Redis hash budget tracker         | 1h    |
| 7  | `bulk_importer.py` — path parser + CSV + batch upsert | 4h    |
| 8  | Test bulk import on 10 symbols (dry_run then live)     | 1h    |
| 9  | Full bulk import of all 5-year CSVs (runtime)          | 4–6h  |
| 10 | `parquet_archiver.py` — append-only Parquet sync       | 2h    |
| 11 | `incremental_updater.py` — Dhan API batch with quota  | 4h    |
| 12 | Auto-scheduler at 16:00 IST in `worker/scheduler.py`  | 1h    |
| 13 | `/data/*` FastAPI router — all 11 endpoints            | 3h    |
| 14 | CSV streaming export endpoint                          | 1h    |
| 15 | WebSocket `/data/sync/status` real-time progress       | 1h    |
| 16 | React UI: Data Engine status panel + export button     | 4h    |

---

## Open Items

| Item                              | Action Required                                |
|-----------------------------------|------------------------------------------------|
| ShreeNexa instrument table schema | Share model file → confirm FK column name      |
| ShreeNexa segment/grouping tables | Confirm: extend existing or create `mkt_seg`   |
| Local CSV base path               | Confirm exact Windows path for `config.yaml`   |
