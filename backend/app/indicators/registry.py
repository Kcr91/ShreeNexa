"""Vectorized technical indicator registry, metadata, and base classes."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

import pyarrow as pa
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class IndicatorFamily(StrEnum):
    """Categorized family namespaces for technical indicators."""

    TREND = "TREND"
    MOMENTUM = "MOMENTUM"
    VOLATILITY = "VOLATILITY"
    VOLUME = "VOLUME"
    STATISTICAL = "STATISTICAL"


class IndicatorMetadata(BaseModel):
    """Catalog metadata describing an indicator, its outputs, and default parameters."""

    model_config = ConfigDict(frozen=True)

    name: str
    family: IndicatorFamily
    description: str
    output_keys: list[str]
    default_params: dict[str, Any]


def extract_series(data: pa.Table | dict[str, Any], column_name: str) -> list[float]:
    """Extract a numeric series as a list of floats from Table or dict."""
    if isinstance(data, pa.Table):
        col = data.column(column_name)
        return [float(x) for x in col.to_pylist()]
    elif isinstance(data, dict):
        val = data.get(column_name)
        if val is None:
            raise KeyError(f"Missing required column '{column_name}' in data dictionary")
        return [float(x) for x in val]
    else:
        raise TypeError(f"Unsupported data container type: {type(data)}")


class VectorIndicator(ABC):
    """Abstract base class for vectorized technical indicator implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique lower-case identifier for indicator."""

    @property
    @abstractmethod
    def family(self) -> IndicatorFamily:
        """Indicator family classification."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable documentation description."""

    @property
    @abstractmethod
    def output_keys(self) -> list[str]:
        """List of dictionary keys for multi-output indicators (or ['value'])."""

    @property
    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """Default parameter dictionary."""

    @abstractmethod
    def warmup_period(self, params: dict[str, Any] | None = None) -> int:
        """Minimum number of bars required before first valid non-NaN output."""

    @abstractmethod
    def compute(
        self,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None] | dict[str, list[float | None]]:
        """Execute calculation over price/volume series."""


class IndicatorRegistry:
    """Central registry for discovering and executing technical indicators."""

    def __init__(self) -> None:
        self._indicators: dict[str, VectorIndicator] = {}

    def register(self, indicator: VectorIndicator) -> None:
        """Register a vector indicator instance."""
        key = indicator.name.lower()
        if key in self._indicators:
            logger.warning("Overwriting existing indicator registration for %s", key)
        self._indicators[key] = indicator

    def get(self, name: str) -> VectorIndicator:
        """Retrieve a registered indicator by name."""
        key = name.lower()
        if key not in self._indicators:
            raise KeyError(f"Indicator '{name}' not found in registry")
        return self._indicators[key]

    def list_indicators(self) -> list[IndicatorMetadata]:
        """List metadata for all registered indicators."""
        return [
            IndicatorMetadata(
                name=ind.name,
                family=ind.family,
                description=ind.description,
                output_keys=ind.output_keys,
                default_params=ind.default_params,
            )
            for ind in self._indicators.values()
        ]

    def compute(
        self,
        name: str,
        data: pa.Table | dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> list[float | None] | dict[str, list[float | None]]:
        """Execute indicator calculation by name."""
        indicator = self.get(name)
        return indicator.compute(data=data, params=params)


# Singleton global registry instance
registry = IndicatorRegistry()
