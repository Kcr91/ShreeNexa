"""Export formats and routing utilities for screener execution results."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.screener.models import ScreenerResult
from app.strategy.ir import InstrumentRef, StaticUniverse


def export_screener_csv(result: ScreenerResult) -> str:
    """Export screener matches to RFC-4180 compliant CSV string."""
    output = io.StringIO()
    # Discover all indicator keys across matches
    ind_keys: list[str] = []
    for m in result.matches:
        for k in m.indicator_values:
            if k not in ind_keys:
                ind_keys.append(k)

    fieldnames = [
        "security_id",
        "symbol",
        "exchange_segment",
        "as_of",
        "rank_value",
        *ind_keys,
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for m in result.matches:
        row: dict[str, Any] = {
            "security_id": m.security_id,
            "symbol": m.symbol,
            "exchange_segment": m.exchange_segment,
            "as_of": m.as_of.isoformat(),
            "rank_value": m.rank_value if m.rank_value is not None else "",
        }
        for k in ind_keys:
            val = m.indicator_values.get(k)
            row[k] = val if val is not None else ""
        writer.writerow(row)

    return output.getvalue()


def export_screener_json(result: ScreenerResult) -> str:
    """Export screener result to formatted JSON string."""
    return json.dumps(result.model_dump(mode="json"), indent=2)


def route_to_watchlist(
    result: ScreenerResult,
    watchlist_name: str,
    watchlist_store: dict[str, list[str]] | None = None,
) -> list[str]:
    """Route matched symbols into a named watchlist."""
    matched_ids = [m.security_id for m in result.matches]
    if watchlist_store is not None:
        current = watchlist_store.setdefault(watchlist_name, [])
        for mid in matched_ids:
            if mid not in current:
                current.append(mid)
    return matched_ids


def route_to_static_universe(result: ScreenerResult) -> StaticUniverse:
    """Transform screener matches into a valid StrategyIR StaticUniverse."""
    if not result.matches:
        raise ValueError(
            "Cannot route empty screener matches to StaticUniverse; at least 1 match is required."
        )
    instruments = [
        InstrumentRef(segment=m.exchange_segment, security_id=m.security_id) for m in result.matches
    ]
    return StaticUniverse(instruments=instruments)
