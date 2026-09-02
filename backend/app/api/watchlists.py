"""REST API endpoints for managing multiple user watchlists, columns, and symbol ordering."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/watchlists", tags=["watchlists"])


class WatchlistItemModel(BaseModel):
    """Normalized symbol item stored in a watchlist."""

    symbol: str
    segment: str = "NSE_EQ"
    security_id: str = ""
    trading_symbol: str = ""
    order: int = 0
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None


class WatchlistCreateModel(BaseModel):
    """Request payload to create a new watchlist."""

    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    columns: list[str] = Field(default_factory=lambda: ["symbol", "ltp", "changePct", "volume"])
    items: list[WatchlistItemModel] = Field(default_factory=list)


class WatchlistUpdateModel(BaseModel):
    """Request payload to update watchlist metadata or column configurations."""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    columns: list[str] | None = None


class WatchlistReorderModel(BaseModel):
    """Request payload to stably reorder symbols in a watchlist."""

    ordered_symbols: list[str]


class WatchlistResponse(BaseModel):
    """Response model representing a user watchlist."""

    id: str
    name: str
    description: str
    is_default: bool = False
    columns: list[str]
    items: list[WatchlistItemModel]


# In-memory storage for watchlists with initial seed defaults
_WATCHLISTS_STORE: dict[str, dict[str, Any]] = {
    "wl-nifty50": {
        "id": "wl-nifty50",
        "name": "NIFTY 50",
        "description": "Top large cap Indian equities",
        "is_default": True,
        "columns": ["symbol", "ltp", "changePct", "volume", "highLow"],
        "items": [
            {
                "symbol": "RELIANCE",
                "segment": "NSE_EQ",
                "security_id": "2885",
                "trading_symbol": "RELIANCE-EQ",
                "order": 0,
            },
            {
                "symbol": "TCS",
                "segment": "NSE_EQ",
                "security_id": "11536",
                "trading_symbol": "TCS-EQ",
                "order": 1,
            },
            {
                "symbol": "HDFCBANK",
                "segment": "NSE_EQ",
                "security_id": "1333",
                "trading_symbol": "HDFCBANK-EQ",
                "order": 2,
            },
            {
                "symbol": "INFY",
                "segment": "NSE_EQ",
                "security_id": "1594",
                "trading_symbol": "INFY-EQ",
                "order": 3,
            },
            {
                "symbol": "ICICIBANK",
                "segment": "NSE_EQ",
                "security_id": "4963",
                "trading_symbol": "ICICIBANK-EQ",
                "order": 4,
            },
        ],
    },
    "wl-banknifty-fno": {
        "id": "wl-banknifty-fno",
        "name": "BANK NIFTY F&O",
        "description": "Active Bank Nifty weekly and monthly derivative contracts",
        "is_default": False,
        "columns": ["symbol", "ltp", "changePct", "oi", "oiChangePct", "volume"],
        "items": [
            {
                "symbol": "BANKNIFTY-FUT",
                "segment": "NSE_FNO",
                "security_id": "52001",
                "trading_symbol": "BANKNIFTY26SEPFUT",
                "order": 0,
                "expiry": "2026-09-30",
            },
            {
                "symbol": "BANKNIFTY-52000-CE",
                "segment": "NSE_FNO",
                "security_id": "52002",
                "trading_symbol": "BANKNIFTY26SEP52000CE",
                "order": 1,
                "expiry": "2026-09-30",
                "strike": 52000.0,
                "option_type": "CE",
            },
            {
                "symbol": "BANKNIFTY-51500-PE",
                "segment": "NSE_FNO",
                "security_id": "52003",
                "trading_symbol": "BANKNIFTY26SEP51500PE",
                "order": 2,
                "expiry": "2026-09-30",
                "strike": 51500.0,
                "option_type": "PE",
            },
        ],
    },
}


@router.get("", response_model=list[WatchlistResponse])
@router.get("/", response_model=list[WatchlistResponse])
def list_watchlists() -> list[dict[str, Any]]:
    """List all available user watchlists."""
    return list(_WATCHLISTS_STORE.values())


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(payload: WatchlistCreateModel) -> dict[str, Any]:
    """Create a new custom user watchlist."""
    wl_id = f"wl-{uuid4().hex[:8]}"
    items_data = [item.model_dump() for item in payload.items]
    # Assign order indices if missing
    for idx, item in enumerate(items_data):
        item["order"] = idx

    watchlist_record: dict[str, Any] = {
        "id": wl_id,
        "name": payload.name,
        "description": payload.description,
        "is_default": False,
        "columns": payload.columns,
        "items": items_data,
    }
    _WATCHLISTS_STORE[wl_id] = watchlist_record
    return watchlist_record


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(watchlist_id: str) -> dict[str, Any]:
    """Get a specific watchlist by ID."""
    wl = _WATCHLISTS_STORE.get(watchlist_id)
    if not wl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found",
        )
    return wl


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(watchlist_id: str, payload: WatchlistUpdateModel) -> dict[str, Any]:
    """Update watchlist name, description, or configured columns."""
    wl = _WATCHLISTS_STORE.get(watchlist_id)
    if not wl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found",
        )

    if payload.name is not None:
        wl["name"] = payload.name
    if payload.description is not None:
        wl["description"] = payload.description
    if payload.columns is not None:
        wl["columns"] = payload.columns

    return wl


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(watchlist_id: str) -> None:
    """Delete a user watchlist. Default watchlists cannot be deleted."""
    wl = _WATCHLISTS_STORE.get(watchlist_id)
    if not wl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found",
        )
    if wl.get("is_default"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Default built-in watchlists cannot be deleted",
        )

    _WATCHLISTS_STORE.pop(watchlist_id, None)


@router.post("/{watchlist_id}/symbols", response_model=WatchlistResponse)
def add_symbol_to_watchlist(watchlist_id: str, item: WatchlistItemModel) -> dict[str, Any]:
    """Add a symbol to a watchlist with stable ordering."""
    wl = _WATCHLISTS_STORE.get(watchlist_id)
    if not wl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found",
        )

    existing_symbols = {i["symbol"] for i in wl["items"]}
    if item.symbol in existing_symbols:
        return wl

    new_item = item.model_dump()
    new_item["order"] = len(wl["items"])
    wl["items"].append(new_item)
    return wl


@router.delete("/{watchlist_id}/symbols/{symbol}", response_model=WatchlistResponse)
def remove_symbol_from_watchlist(watchlist_id: str, symbol: str) -> dict[str, Any]:
    """Remove a symbol from a watchlist and re-index orders."""
    wl = _WATCHLISTS_STORE.get(watchlist_id)
    if not wl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found",
        )

    wl["items"] = [i for i in wl["items"] if i["symbol"] != symbol]
    for idx, i in enumerate(wl["items"]):
        i["order"] = idx

    return wl


@router.post("/{watchlist_id}/reorder", response_model=WatchlistResponse)
def reorder_watchlist_symbols(watchlist_id: str, payload: WatchlistReorderModel) -> dict[str, Any]:
    """Stably reorder items in a watchlist based on an explicit symbol sequence."""
    wl = _WATCHLISTS_STORE.get(watchlist_id)
    if not wl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist '{watchlist_id}' not found",
        )

    items_by_sym = {i["symbol"]: i for i in wl["items"]}
    reordered: list[dict[str, Any]] = []

    # First add symbols in the requested sequence
    for idx, sym in enumerate(payload.ordered_symbols):
        if sym in items_by_sym:
            item = items_by_sym.pop(sym)
            item["order"] = idx
            reordered.append(item)

    # Any remaining unmentioned symbols append at the end
    curr_idx = len(reordered)
    for item in items_by_sym.values():
        item["order"] = curr_idx
        reordered.append(item)
        curr_idx += 1

    wl["items"] = reordered
    return wl
