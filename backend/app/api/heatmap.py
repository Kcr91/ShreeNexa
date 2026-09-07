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
    category: str | None = "SECTORAL"
    constituent_count: int | None = None
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
        change_pct=-0.50,
        ltp=23779.15,
        advances=13,
        declines=37,
        unchanged=0,
        futures_basis=22.5,
        oi_change_pct=1.8,
        category="BROAD_MARKET",
        constituent_count=50,
    ),
    IndexHeatmapCell(
        index_name="NIFTY BANK",
        sector="Banking",
        weight=20.0,
        change_pct=-0.49,
        ltp=57088.30,
        advances=4,
        declines=8,
        unchanged=0,
        futures_basis=65.0,
        oi_change_pct=3.2,
        category="SECTORAL",
        constituent_count=12,
    ),
    IndexHeatmapCell(
        index_name="NIFTY IT",
        sector="Information Technology",
        weight=15.0,
        change_pct=-2.29,
        ltp=39995.20,
        advances=1,
        declines=9,
        unchanged=0,
        futures_basis=-85.0,
        oi_change_pct=-3.5,
        category="SECTORAL",
        constituent_count=10,
    ),
    IndexHeatmapCell(
        index_name="NIFTY AUTO",
        sector="Automotive",
        weight=10.0,
        change_pct=-0.04,
        ltp=27098.75,
        advances=7,
        declines=8,
        unchanged=0,
        futures_basis=18.0,
        oi_change_pct=1.4,
        category="SECTORAL",
        constituent_count=15,
    ),
    IndexHeatmapCell(
        index_name="NIFTY PHARMA",
        sector="Pharmaceuticals",
        weight=8.0,
        change_pct=0.75,
        ltp=26675.50,
        advances=15,
        declines=5,
        unchanged=0,
        futures_basis=32.0,
        oi_change_pct=4.1,
        category="SECTORAL",
        constituent_count=20,
    ),
    IndexHeatmapCell(
        index_name="NIFTY FMCG",
        sector="FMCG",
        weight=8.0,
        change_pct=-0.66,
        ltp=65592.15,
        advances=4,
        declines=11,
        unchanged=0,
        futures_basis=-25.0,
        oi_change_pct=-0.8,
        category="SECTORAL",
        constituent_count=15,
    ),
    IndexHeatmapCell(
        index_name="NIFTY METAL",
        sector="Metals & Mining",
        weight=7.0,
        change_pct=-1.24,
        ltp=13152.90,
        advances=3,
        declines=8,
        unchanged=0,
        futures_basis=-20.0,
        oi_change_pct=0.5,
        category="SECTORAL",
        constituent_count=11,
    ),
    IndexHeatmapCell(
        index_name="NIFTY ENERGY",
        sector="Energy",
        weight=7.0,
        change_pct=-0.25,
        ltp=37973.35,
        advances=3,
        declines=7,
        unchanged=0,
        futures_basis=20.0,
        oi_change_pct=1.5,
        category="THEMATIC",
        constituent_count=10,
    ),
    IndexHeatmapCell(
        index_name="NIFTY COMMODITIES",
        sector="Commodities Producers",
        weight=5.0,
        change_pct=-1.04,
        ltp=9702.10,
        advances=8,
        declines=22,
        unchanged=0,
        futures_basis=-15.0,
        oi_change_pct=0.8,
        category="THEMATIC",
        constituent_count=30,
    ),
    IndexHeatmapCell(
        index_name="NIFTY NEXT 50",
        sector="Large Cap Emerging",
        weight=12.0,
        change_pct=-0.42,
        ltp=72575.75,
        advances=18,
        declines=32,
        unchanged=0,
        futures_basis=35.0,
        oi_change_pct=0.9,
        category="BROAD_MARKET",
        constituent_count=50,
    ),
]


@router.get("/indices", response_model=list[IndexHeatmapCell])
def get_index_heatmap(category: str | None = None) -> list[IndexHeatmapCell]:
    """Retrieve index-level heatmap across major Indian market sectors."""
    if not category:
        return INDEX_SEED_HEATMAP

    clean_cat = category.strip().upper()
    filtered = [
        c
        for c in INDEX_SEED_HEATMAP
        if c.category and c.category.upper() == clean_cat
    ]
    return filtered if filtered else INDEX_SEED_HEATMAP


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
