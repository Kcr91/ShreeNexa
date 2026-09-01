"""Incremental indicator base class, factory, and state serialization."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


def extract_bar_field(bar: BarRecord | dict[str, Any], field: str) -> float:
    """Extract float value from BarRecord or dict."""
    if isinstance(bar, BarRecord):
        return float(getattr(bar, field))
    elif isinstance(bar, dict):
        val = bar.get(field)
        if val is None:
            raise KeyError(f"Missing required field '{field}' in bar dictionary")
        return float(val)
    else:
        raise TypeError(f"Unsupported bar type: {type(bar)}")


class IncrementalIndicator(ABC):
    """Abstract base class for streaming/incremental technical indicators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Indicator identifier matching its vector counterpart."""

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if warm-up period is completed and indicator produces valid outputs."""

    @abstractmethod
    def update(
        self,
        bar: BarRecord | dict[str, Any],
    ) -> float | dict[str, float | None] | None:
        """Update indicator state with a new bar and return current value."""

    @abstractmethod
    def reset(self) -> None:
        """Clear all buffers and reset indicator state."""

    @property
    @abstractmethod
    def state(self) -> dict[str, Any]:
        """Serializable state checkpoint dictionary."""

    @abstractmethod
    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore indicator state from checkpoint dictionary."""


_INCREMENTAL_REGISTRY: dict[str, type[IncrementalIndicator]] = {}


def register_incremental(name: str) -> Any:
    """Decorator to register an incremental indicator implementation class."""

    def decorator(cls: type[IncrementalIndicator]) -> type[IncrementalIndicator]:
        _INCREMENTAL_REGISTRY[name.lower()] = cls
        return cls

    return decorator


def create_incremental_indicator(
    name: str,
    params: dict[str, Any] | None = None,
) -> IncrementalIndicator:
    """Factory creating an incremental indicator instance by name with given parameters."""
    key = name.lower()
    if key not in _INCREMENTAL_REGISTRY:
        raise KeyError(f"No incremental implementation registered for '{name}'")
    cls = _INCREMENTAL_REGISTRY[key]
    return cls(**(params or {}))
