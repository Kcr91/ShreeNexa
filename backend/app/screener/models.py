"""Data models for Point-in-Time Screener definitions and execution results."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.strategy.ir import (
    IndicatorDef,
    SignalNode,
    UniverseSelector,
)


class RankingRule(BaseModel):
    """Rule specifying how matched universe instruments should be sorted."""

    model_config = ConfigDict(extra="forbid")

    by: str = Field(description="Indicator or field name to sort by, e.g. 'rsi' or 'volume'")
    direction: Literal["asc", "desc"] = Field(default="desc", description="Sort direction")


class ScreenerDefinition(BaseModel):
    """Point-in-time screener definition containing universe, indicators, and signal AST."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Human-readable screener name")
    universe: UniverseSelector = Field(
        description="Target universe (e.g. IndexUniverse, StaticUniverse, WatchlistUniverse)"
    )
    timeframe: str = Field(default="1d", description="Resolution timeframe (e.g. '1d', '5m')")
    as_of: datetime | date | None = Field(
        default=None, description="Historical as-of evaluation timestamp/date"
    )
    lookback_bars: int = Field(
        default=200, ge=1, description="Number of historical warmup bars to load up to as-of date"
    )
    indicators: dict[str, IndicatorDef] = Field(
        default_factory=dict, description="Declared technical indicators"
    )
    filter: SignalNode = Field(description="Signal AST filter tree")
    ranking: RankingRule | None = Field(default=None, description="Optional ranking rule")
    limit: int | None = Field(default=None, ge=1, description="Max number of matches to return")


class ScreenerMatch(BaseModel):
    """A single matched instrument from the point-in-time screener run."""

    model_config = ConfigDict(extra="forbid")

    security_id: str
    symbol: str
    exchange_segment: str
    as_of: datetime
    indicator_values: dict[str, Any]
    rank_value: float | None = None


class ScreenerResult(BaseModel):
    """Aggregated output from point-in-time screener execution."""

    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    matches: list[ScreenerMatch]
    total_universe_size: int
    evaluated_count: int
    matched_count: int
    warnings: list[str] = Field(default_factory=list)
