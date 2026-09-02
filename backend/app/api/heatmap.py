"""REST API endpoints for market index and constituent heatmaps with breadth."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.marketdata.universe import get_constituents_at_date

router = APIRouter(prefix="/api/v1/heatmap", tags=["heatmap"])


def get_db_engine() -> Engine:
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


class MarketBreadth(BaseModel):
    """Aggregated market breadth and sentiment metrics."""

    total_count: int
    advances: int
    declines: int
    unchanged: int
    advance_decline_ratio: float
    pct_above_prev_close: float
    weighted_breadth: float
    sentiment_posture: str


class IndexHeatmapCell(BaseModel):
    """Index-level heatmap cell."""

    index_name: str
    sector: str
    weight: float
    change_pct: float
    ltp: float
    advances: int
    declines: int
    unchanged: int
    futures_basis: float
    oi_change_pct: float
    weighting_source: str = "OFFICIAL_NSE"


class ConstituentHeatmapCell(BaseModel):
    """Constituent-level heatmap cell with transparent weighting source."""

    symbol: str
    sector: str
    weight: float
    is_weight_fallback: bool = False
    weighting_source: str = "OFFICIAL_NSE"
    change_pct: float
    ltp: float
    volume: int = 0


class ConstituentHeatmapResponse(BaseModel):
    """Aggregated constituent heatmap response with breadth and cell totals."""

    index_name: str
    breadth: MarketBreadth
    cell_total_weight: float
    constituents: list[ConstituentHeatmapCell] = Field(default_factory=list)


INDEX_SEED_HEATMAP: list[IndexHeatmapCell] = [
    IndexHeatmapCell(
        index_name="NIFTY 50",
        sector="Large Cap Benchmark",
        weight=25.0,
        change_pct=0.85,
        ltp=25250.0,
        advances=32,
        declines=16,
        unchanged=2,
        futures_basis=42.5,
        oi_change_pct=2.8,
    ),
    IndexHeatmapCell(
        index_name="NIFTY BANK",
        sector="Banking",
        weight=20.0,
        change_pct=1.40,
        ltp=52150.0,
        advances=9,
        declines=3,
        unchanged=0,
        futures_basis=65.0,
        oi_change_pct=4.1,
    ),
    IndexHeatmapCell(
        index_name="NIFTY IT",
        sector="Information Technology",
        weight=15.0,
        change_pct=-0.65,
        ltp=41800.0,
        advances=3,
        declines=7,
        unchanged=0,
        futures_basis=-15.0,
        oi_change_pct=-1.2,
    ),
    IndexHeatmapCell(
        index_name="NIFTY AUTO",
        sector="Automotive",
        weight=10.0,
        change_pct=1.85,
        ltp=26400.0,
        advances=11,
        declines=4,
        unchanged=0,
        futures_basis=30.0,
        oi_change_pct=3.5,
    ),
    IndexHeatmapCell(
        index_name="NIFTY PHARMA",
        sector="Pharmaceuticals",
        weight=8.0,
        change_pct=0.35,
        ltp=22900.0,
        advances=12,
        declines=8,
        unchanged=0,
        futures_basis=12.0,
        oi_change_pct=0.8,
    ),
    IndexHeatmapCell(
        index_name="NIFTY FMCG",
        sector="FMCG",
        weight=8.0,
        change_pct=-0.40,
        ltp=58300.0,
        advances=5,
        declines=10,
        unchanged=0,
        futures_basis=-5.0,
        oi_change_pct=-0.5,
    ),
    IndexHeatmapCell(
        index_name="NIFTY METAL",
        sector="Metals & Mining",
        weight=7.0,
        change_pct=2.45,
        ltp=9650.0,
        advances=12,
        declines=3,
        unchanged=0,
        futures_basis=25.0,
        oi_change_pct=5.2,
    ),
    IndexHeatmapCell(
        index_name="NIFTY ENERGY",
        sector="Energy",
        weight=7.0,
        change_pct=0.75,
        ltp=39100.0,
        advances=6,
        declines=4,
        unchanged=0,
        futures_basis=18.0,
        oi_change_pct=1.5,
    ),
]


@router.get("/indices", response_model=list[IndexHeatmapCell])
def get_index_heatmap() -> list[IndexHeatmapCell]:
    """Retrieve index-level heatmap across major Indian market sectors."""
    return INDEX_SEED_HEATMAP


@router.get("/{index_name}/constituents", response_model=ConstituentHeatmapResponse)
def get_constituent_heatmap(
    engine: DbEngineDep,
    index_name: str,
) -> ConstituentHeatmapResponse:
    """Retrieve constituent-level heatmap with breadth and deterministic missing-weight handling."""
    records = get_constituents_at_date(engine, index_name=index_name)

    if not records:
        from app.marketdata.universe import ingest_fallback_constituents

        ingest_fallback_constituents(engine)
        records = get_constituents_at_date(engine, index_name=index_name)

    # 1. Deterministic missing-weight handling
    total_known_weight = sum(float(r.weight) for r in records if r.weight is not None)
    unweighted_records = [r for r in records if r.weight is None or float(r.weight) <= 0.0]
    unweighted_count = len(unweighted_records)

    assigned_fallback_weight = 0.0
    if unweighted_count > 0:
        remaining_weight = max(0.0, 100.0 - total_known_weight)
        assigned_fallback_weight = (
            round(remaining_weight / unweighted_count, 4)
            if remaining_weight > 0
            else round(100.0 / len(records), 4)
        )

    # Deterministic mock prices & returns for demonstration and testing
    cells: list[ConstituentHeatmapCell] = []
    for r in records:
        is_fallback = r.weight is None or float(r.weight) <= 0.0
        weight = (
            float(r.weight)
            if not is_fallback and r.weight is not None
            else assigned_fallback_weight
        )
        source = "FALLBACK_EQUAL_WEIGHT" if is_fallback else "OFFICIAL_NSE"

        # Deterministic variation based on symbol hash
        sym_hash = sum(ord(c) for c in r.symbol)
        change_pct = round(((sym_hash % 600) - 280) / 100.0, 2)  # between -2.8% and +3.2%
        ltp = round(100.0 + (sym_hash % 3000), 2)
        vol = (sym_hash * 1234) % 10000000

        cells.append(
            ConstituentHeatmapCell(
                symbol=r.symbol,
                sector=r.sector or "General",
                weight=round(weight, 2),
                is_weight_fallback=is_fallback,
                weighting_source=source,
                change_pct=change_pct,
                ltp=ltp,
                volume=vol,
            )
        )

    # Normalize total weight to exactly 100.0%
    curr_total = sum(c.weight for c in cells)
    if curr_total > 0 and len(cells) > 0:
        diff = round(100.0 - curr_total, 2)
        cells[0].weight = round(cells[0].weight + diff, 2)

    cell_total = round(sum(c.weight for c in cells), 2)

    # 2. Compute Market Breadth metrics
    advances = sum(1 for c in cells if c.change_pct > 0)
    declines = sum(1 for c in cells if c.change_pct < 0)
    unchanged = sum(1 for c in cells if c.change_pct == 0)
    total_count = len(cells)

    ad_ratio = round(advances / max(declines, 1), 2)
    pct_positive = round((advances / max(total_count, 1)) * 100.0, 1)
    weighted_breadth = round(sum((c.weight * c.change_pct) for c in cells) / 100.0, 2)

    if pct_positive >= 70.0:
        posture = "Strong Bullish"
    elif pct_positive >= 55.0:
        posture = "Moderate Bullish"
    elif pct_positive >= 45.0:
        posture = "Neutral"
    elif pct_positive >= 30.0:
        posture = "Moderate Bearish"
    else:
        posture = "Strong Bearish"

    breadth = MarketBreadth(
        total_count=total_count,
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        advance_decline_ratio=ad_ratio,
        pct_above_prev_close=pct_positive,
        weighted_breadth=weighted_breadth,
        sentiment_posture=posture,
    )

    return ConstituentHeatmapResponse(
        index_name=index_name,
        breadth=breadth,
        cell_total_weight=cell_total,
        constituents=cells,
    )
