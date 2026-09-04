"""Configuration models and loader for dated Dhan API rate limits."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dhan_limits.yaml"


class RateLimitSpec(BaseModel):
    """Rate limit specification for an endpoint or endpoint category."""

    rate: float = Field(..., gt=0, description="Replenishment rate in tokens per second")
    burst: int = Field(..., ge=1, description="Maximum bucket capacity")
    description: str = Field(default="", description="Description of the endpoint or category")
    per_minute: int | None = Field(default=None, ge=1, description="Maximum requests per minute")
    per_hour: int | None = Field(default=None, ge=1, description="Maximum requests per hour")
    per_day: int | None = Field(default=None, ge=1, description="Maximum requests per day")


class BackoffSpec(BaseModel):
    """Configuration for jittered backoff during token wait."""

    base_delay_seconds: float = Field(default=0.05, gt=0)
    max_delay_seconds: float = Field(default=2.0, gt=0)
    jitter_ratio: float = Field(default=0.25, ge=0.0, le=1.0)


class DhanLimitsConfig(BaseModel):
    """Complete dated rate limits configuration for DhanHQ REST endpoints."""

    schema_version: int = Field(default=1)
    as_of: str = Field(default="2026-09-01")
    source: str = Field(default="https://dhanhq.co/docs/v2/")
    notes: str = Field(default="")
    default_limit: RateLimitSpec = Field(
        default_factory=lambda: RateLimitSpec(rate=10.0, burst=20, description="Default limit")
    )
    backoff: BackoffSpec = Field(default_factory=BackoffSpec)
    categories: dict[str, RateLimitSpec] = Field(default_factory=dict)

    def get_rate_limit(self, category: str) -> RateLimitSpec:
        """Retrieve rate limit for category, falling back to base category or default limit."""
        if category in self.categories:
            return self.categories[category]
        if category.startswith("option_chain:"):
            return self.categories.get("option_chain", self.default_limit)
        return self.default_limit


def get_default_dhan_limits() -> DhanLimitsConfig:
    """Return hardcoded safe fallback configuration if YAML file is unavailable."""
    return DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-03",
        source="https://dhanhq.co/docs/v2/",
        notes="Safe built-in fallback rate limits (DhanHQ v2.5 verified)",
        default_limit=RateLimitSpec(rate=10.0, burst=10, description="Default fallback"),
        backoff=BackoffSpec(base_delay_seconds=0.05, max_delay_seconds=2.0, jitter_ratio=0.25),
        categories={
            "default": RateLimitSpec(rate=10.0, burst=10, description="Default REST"),
            "option_chain": RateLimitSpec(
                rate=0.3333333333333333,
                burst=1,
                description="Option chain (1 req/3s per underlying)",
            ),
            "historical_daily": RateLimitSpec(
                rate=5.0, burst=5, per_day=7000, description="Daily historical"
            ),
            "historical_intraday": RateLimitSpec(
                rate=5.0, burst=5, per_day=7000, description="Intraday historical"
            ),
            "quotes": RateLimitSpec(rate=1.0, burst=1, description="Quotes (1 req/s)"),
            "orders": RateLimitSpec(
                rate=10.0,
                burst=10,
                per_minute=250,
                per_hour=1000,
                per_day=7000,
                description="Orders (10 req/s, 250/min, 1000/hr, 7000/day)",
            ),
            "account_funds_holdings": RateLimitSpec(
                rate=10.0, burst=10, description="Account & Holdings"
            ),
        },
    )


@lru_cache(maxsize=4)
def load_dhan_limits(config_path: Path | str | None = None) -> DhanLimitsConfig:
    """Load Dhan rate limits from YAML file with fallback to safe defaults."""
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not target_path.is_file():
        return get_default_dhan_limits()

    try:
        content = target_path.read_text(encoding="utf-8")
        parsed: Any = yaml.safe_load(content)
        if not isinstance(parsed, dict):
            return get_default_dhan_limits()
        return DhanLimitsConfig.model_validate(parsed)
    except Exception:
        return get_default_dhan_limits()


def get_category_for_endpoint(method: str, path: str) -> str:
    """Map an HTTP method and Dhan REST endpoint path to its rate limit category."""
    norm_path = path.strip().lstrip("/")
    if norm_path.startswith("v2/"):
        norm_path = norm_path[3:].lstrip("/")

    lower_path = norm_path.lower()
    method_upper = method.upper()

    if lower_path.startswith("optionchain"):
        return "option_chain"
    if lower_path.startswith("charts/historical"):
        return "historical_daily"
    if lower_path.startswith("charts/intraday") or lower_path.startswith("charts/rollingoption"):
        return "historical_intraday"
    if (
        lower_path.startswith("marketfeed/quote")
        or lower_path.startswith("quotes")
        or "quote" in lower_path
    ):
        return "quotes"

    # Orders and emergency order actions
    if (
        lower_path.startswith("orders")
        or lower_path.startswith("forever/orders")
        or lower_path.startswith("superorders")
        or lower_path.startswith("killswitch")
        or lower_path.startswith("pnlexit")
        or (lower_path.startswith("positions") and method_upper == "DELETE")
    ):
        return "orders"

    if any(
        lower_path.startswith(prefix)
        for prefix in (
            "fundlimit",
            "profile",
            "holdings",
            "positions",
            "edis",
            "margin",
            "margincalculator",
            "traderscontrol",
            "renewtoken",
            "ip",
        )
    ):
        return "account_funds_holdings"

    return "default"
