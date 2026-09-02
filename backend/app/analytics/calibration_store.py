"""In-memory and Redis persistence store for active option-chain calibrations."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.analytics.calibration import CalibrationReport

logger = logging.getLogger(__name__)

# Module-level memory store fallback
_CALIBRATION_STORE: dict[str, CalibrationReport] = {}


class CalibrationStore:
    """Store for managing calibrated option chain conventions across runtime sessions."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client

    def save(self, underlying: str, report: CalibrationReport) -> None:
        """Save calibrated report for an underlying index/stock."""
        key = underlying.upper()
        _CALIBRATION_STORE[key] = report

        if self._redis is not None:
            try:
                redis_key = f"options:calibration:{key}"
                self._redis.set(redis_key, report.model_dump_json(), ex=86400)
            except Exception as e:
                logger.warning(f"Failed to persist calibration report to Redis: {e}")

    def get(self, underlying: str) -> CalibrationReport | None:
        """Retrieve calibrated report for an underlying index/stock."""
        key = underlying.upper()

        # Check in-memory store first
        if key in _CALIBRATION_STORE:
            return _CALIBRATION_STORE[key]

        if self._redis is not None:
            try:
                redis_key = f"options:calibration:{key}"
                raw = self._redis.get(redis_key)
                if raw:
                    data = json.loads(raw)
                    report = CalibrationReport.model_validate(data)
                    _CALIBRATION_STORE[key] = report
                    return report
            except Exception as e:
                logger.warning(f"Failed to load calibration report from Redis: {e}")

        return None

    def list_all(self) -> dict[str, CalibrationReport]:
        """Return all active calibration reports."""
        return dict(_CALIBRATION_STORE)


_default_store = CalibrationStore()


def get_calibration_store() -> CalibrationStore:
    """Get the global default CalibrationStore instance."""
    return _default_store
