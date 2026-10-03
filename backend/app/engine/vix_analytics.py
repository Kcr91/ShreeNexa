"""Volatility Regime Heatmap Analytics Engine (VIX vs IV Performance)."""

from __future__ import annotations

from typing import Any

from app.engine.variant_models import VixHeatmapCell, VixHeatmapResponse

VIX_BUCKETS = ["<12", "12-15", "15-18", "18-22", ">22"]
IV_BUCKETS = ["<20%", "20-30%", "30-40%", ">40%"]


def categorize_vix(vix: float | None) -> str:
    """Classify a numeric VIX value into a categorical bucket."""
    if vix is None:
        return "12-15"
    if vix < 12.0:
        return "<12"
    elif vix < 15.0:
        return "12-15"
    elif vix < 18.0:
        return "15-18"
    elif vix < 22.0:
        return "18-22"
    return ">22"


def categorize_iv(iv: float | None) -> str:
    """Classify an option IV % into a categorical bucket."""
    if iv is None:
        return "20-30%"
    if iv < 20.0:
        return "<20%"
    elif iv < 30.0:
        return "20-30%"
    elif iv < 40.0:
        return "30-40%"
    return ">40%"


def generate_vix_iv_heatmap(trades: list[dict[str, Any]]) -> VixHeatmapResponse:
    """Build a 2D performance matrix grouping trades by VIX and IV buckets."""
    grid: dict[tuple[str, str], list[dict[str, Any]]] = {
        (v, i): [] for v in VIX_BUCKETS for i in IV_BUCKETS
    }

    for t in trades:
        v_cat = categorize_vix(t.get("entry_india_vix") or t.get("entry_vix"))
        i_cat = categorize_iv(t.get("entry_option_iv") or t.get("entry_iv"))
        grid[(v_cat, i_cat)].append(t)

    cells: list[VixHeatmapCell] = []
    best_vix_pnl: dict[str, float] = {v: 0.0 for v in VIX_BUCKETS}
    best_iv_pnl: dict[str, float] = {i: 0.0 for i in IV_BUCKETS}

    for (v_cat, i_cat), cell_trades in grid.items():
        count = len(cell_trades)
        wins = sum(1 for tr in cell_trades if float(tr.get("realized_pnl", 0.0) or 0.0) > 0)
        tot_pnl = sum(float(tr.get("realized_pnl", 0.0) or 0.0) for tr in cell_trades)
        win_rate = (wins / count * 100.0) if count > 0 else 0.0
        avg_pnl = (tot_pnl / count) if count > 0 else 0.0

        best_vix_pnl[v_cat] += tot_pnl
        best_iv_pnl[i_cat] += tot_pnl

        cells.append(
            VixHeatmapCell(
                vix_bucket=v_cat,
                iv_bucket=i_cat,
                trade_count=count,
                win_rate_pct=round(win_rate, 2),
                total_pnl=round(tot_pnl, 2),
                avg_pnl=round(avg_pnl, 2),
            )
        )

    best_vix = max(best_vix_pnl.items(), key=lambda x: x[1])[0] if trades else "12-15"
    best_iv = max(best_iv_pnl.items(), key=lambda x: x[1])[0] if trades else "20-30%"

    return VixHeatmapResponse(
        profitable_vix_range=f"{best_vix} VIX Zone",
        profitable_iv_zone=f"{best_iv} IV Zone",
        cells=cells,
    )
