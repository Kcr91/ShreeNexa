"""Per-symbol, per-month view of what has been downloaded and what looked odd.

Built directly on the backfill window ledger rather than on the Parquet files, because
a window is exactly one API call for exactly one calendar month. That makes "2022-03
downloaded, 2022-04 never fetched" a stored fact rather than something inferred from
gaps in a bar series - which matters when the upstream archive itself is unreliable and
a gap could equally mean "not fetched yet", "fetched and genuinely empty", or "the
exchange was closed".

Nothing here judges whether data is usable. Windows carry the anomalies recorded at
fetch time and the report surfaces them; deciding what to do about them is a separate
task performed against stored data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.engine import Engine

from app.worker.backfill_queue import backfill_job_table, backfill_window_table

logger = logging.getLogger(__name__)

# Window states that mean "we have asked the API and recorded the answer".
SETTLED_STATES = ("done", "empty")


@dataclass
class MonthEntry:
    """One calendar month of one series."""

    month: str
    state: str
    rows: int = 0
    suspect: bool = False
    reasons: list[str] = field(default_factory=list)
    in_hours: int = 0
    out_of_hours: int = 0
    distinct_days: int = 0
    unexpected_dates: list[str] = field(default_factory=list)
    attempts: int = 0
    last_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "state": self.state,
            "rows": self.rows,
            "suspect": self.suspect,
            "reasons": self.reasons,
            "in_hours": self.in_hours,
            "out_of_hours": self.out_of_hours,
            "distinct_days": self.distinct_days,
            "unexpected_dates": self.unexpected_dates,
            "attempts": self.attempts,
            "last_error": self.last_error,
        }


@dataclass
class SeriesReport:
    """Every month of one addressable series."""

    symbol: str
    dataset: str
    exchange_segment: str
    interval: str
    underlying_symbol: str | None
    expiry_flag: str | None
    expiry_code: int | None
    strike_offset: int | None
    option_type: str | None
    tier: int
    months: list[MonthEntry] = field(default_factory=list)

    @property
    def downloaded_months(self) -> int:
        return sum(1 for m in self.months if m.state in SETTLED_STATES)

    @property
    def pending_months(self) -> int:
        return sum(1 for m in self.months if m.state in ("pending", "running"))

    @property
    def failed_months(self) -> int:
        return sum(1 for m in self.months if m.state == "failed")

    @property
    def suspect_months(self) -> int:
        return sum(1 for m in self.months if m.suspect)

    @property
    def total_rows(self) -> int:
        return sum(m.rows for m in self.months)

    def label(self) -> str:
        """Human-readable name for the series, including the option leg when present."""
        parts = [self.symbol]
        if self.option_type:
            offset = self.strike_offset or 0
            strike = "ATM" if offset == 0 else f"ATM{offset:+d}"
            parts.append(
                f"{self.expiry_flag or ''}{self.expiry_code or ''} {strike} {self.option_type}"
            )
        parts.append(f"[{self.interval}]")
        return " ".join(p for p in parts if p)

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "label": self.label(),
            "dataset": self.dataset,
            "exchange_segment": self.exchange_segment,
            "interval": self.interval,
            "underlying_symbol": self.underlying_symbol,
            "expiry_flag": self.expiry_flag,
            "expiry_code": self.expiry_code,
            "strike_offset": self.strike_offset,
            "option_type": self.option_type,
            "tier": self.tier,
            "downloaded_months": self.downloaded_months,
            "pending_months": self.pending_months,
            "failed_months": self.failed_months,
            "suspect_months": self.suspect_months,
            "total_rows": self.total_rows,
            "first_month": self.months[0].month if self.months else None,
            "last_month": self.months[-1].month if self.months else None,
            "months": [m.as_dict() for m in self.months],
        }


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _row_to_entry(row: dict[str, Any]) -> MonthEntry:
    quality = row.get("quality") or {}
    return MonthEntry(
        month=_month_key(row["window_start"]),
        state=str(row["state"]),
        rows=int(row.get("rows") or 0),
        suspect=bool(row.get("suspect")),
        reasons=list(quality.get("suspect_reasons") or []),
        in_hours=int(quality.get("in_hours") or 0),
        out_of_hours=int(quality.get("out_of_hours") or 0),
        distinct_days=int(row.get("distinct_days") or quality.get("distinct_days") or 0),
        unexpected_dates=list(quality.get("unexpected_dates") or []),
        attempts=int(row.get("attempts") or 0),
        last_error=row.get("last_error"),
    )


def build_report(
    engine: Engine,
    symbol: str | None = None,
    dataset: str | None = None,
    tier: int | None = None,
    suspect_only: bool = False,
    limit_series: int = 200,
) -> dict[str, Any]:
    """Assemble the per-series, per-month download report."""
    j = backfill_job_table
    w = backfill_window_table

    conditions = []
    if symbol:
        conditions.append(j.c.symbol == symbol.upper())
    if dataset:
        conditions.append(j.c.dataset == dataset)
    if tier is not None:
        conditions.append(j.c.tier == tier)
    if suspect_only:
        conditions.append(w.c.suspect.is_(True))

    stmt = (
        select(
            j.c.job_id,
            j.c.symbol,
            j.c.dataset,
            j.c.exchange_segment,
            j.c.interval,
            j.c.underlying_symbol,
            j.c.expiry_flag,
            j.c.expiry_code,
            j.c.strike_offset,
            j.c.option_type,
            j.c.tier,
            w.c.window_start,
            w.c.state,
            w.c.rows,
            w.c.suspect,
            w.c.quality,
            w.c.distinct_days,
            w.c.attempts,
            w.c.last_error,
        )
        .select_from(w.join(j, w.c.job_id == j.c.job_id))
        .order_by(j.c.tier, j.c.symbol, j.c.dataset, w.c.window_start)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    series: dict[str, SeriesReport] = {}
    with engine.connect() as conn:
        for row in conn.execute(stmt).mappings():
            key = str(row["job_id"])
            report = series.get(key)
            if report is None:
                if len(series) >= limit_series:
                    continue
                report = SeriesReport(
                    symbol=str(row["symbol"]),
                    dataset=str(row["dataset"]),
                    exchange_segment=str(row["exchange_segment"]),
                    interval=str(row["interval"]),
                    underlying_symbol=row["underlying_symbol"],
                    expiry_flag=row["expiry_flag"],
                    expiry_code=row["expiry_code"],
                    strike_offset=row["strike_offset"],
                    option_type=row["option_type"],
                    tier=int(row["tier"]),
                )
                series[key] = report
            report.months.append(_row_to_entry(dict(row)))

    ordered = sorted(series.values(), key=lambda s: (s.tier, s.symbol, s.dataset, s.interval))
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "totals": report_totals(engine),
        "series_returned": len(ordered),
        "series": [s.as_dict() for s in ordered],
    }


def report_totals(engine: Engine) -> dict[str, Any]:
    """Queue-wide counts, so the report header does not depend on the page shown."""
    w = backfill_window_table
    stmt = select(
        func.count().label("windows"),
        func.coalesce(func.sum(w.c.rows), 0).label("bars"),
        func.count().filter(w.c.state == "done").label("done"),
        func.count().filter(w.c.state == "empty").label("empty"),
        func.count().filter(w.c.state.in_(["pending", "running"])).label("pending"),
        func.count().filter(w.c.state == "failed").label("failed"),
        func.count().filter(w.c.suspect.is_(True)).label("suspect"),
    )
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().one()

    counts = {k: int(v or 0) for k, v in row.items()}
    settled = counts["done"] + counts["empty"]
    totals: dict[str, Any] = dict(counts)
    totals["settled"] = settled
    totals["percent_complete"] = (
        round(100.0 * settled / counts["windows"], 1) if counts["windows"] else 0.0
    )
    return totals


def missing_months(engine: Engine, symbol: str, dataset: str | None = None) -> list[str]:
    """Months of a symbol that have not been settled yet.

    Reported separately from the grid so a caller can ask the narrow question without
    pulling every month of every series.
    """
    j = backfill_job_table
    w = backfill_window_table
    conditions = [j.c.symbol == symbol.upper(), w.c.state.notin_(SETTLED_STATES)]
    if dataset:
        conditions.append(j.c.dataset == dataset)

    stmt = (
        select(w.c.window_start)
        .select_from(w.join(j, w.c.job_id == j.c.job_id))
        .where(and_(*conditions))
        .order_by(w.c.window_start)
    )
    with engine.connect() as conn:
        return sorted({_month_key(r[0]) for r in conn.execute(stmt).all()})
