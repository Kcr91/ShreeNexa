"""Persistence store for Screener definitions and immutable execution run snapshots."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.screener.models import ScreenerDefinition, ScreenerResult


class ScreenerRecord(BaseModel):
    """Persisted screener configuration entity."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    definition: ScreenerDefinition
    schedule: str | None = Field(default=None, description="Optional cron schedule expression")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class ScreenerRunSnapshot(BaseModel):
    """Immutable snapshot of a completed screener run with audit provenance."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    screener_id: str
    screener_name: str
    as_of: datetime
    executed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    result: ScreenerResult


class ScreenerStore:
    """Thread-safe in-memory store for screeners and run snapshots."""

    def __init__(self) -> None:
        self._screeners: dict[str, ScreenerRecord] = {}
        self._runs: dict[str, ScreenerRunSnapshot] = {}
        self._screener_runs_index: dict[str, list[str]] = {}

    def create_screener(
        self, definition: ScreenerDefinition, schedule: str | None = None
    ) -> ScreenerRecord:
        """Create and store a new screener definition."""
        record = ScreenerRecord(
            name=definition.name,
            definition=definition,
            schedule=schedule,
        )
        self._screeners[record.id] = record
        self._screener_runs_index[record.id] = []
        return record

    def get_screener(self, screener_id: str) -> ScreenerRecord | None:
        """Retrieve screener definition by ID."""
        return self._screeners.get(screener_id)

    def list_screeners(self) -> list[ScreenerRecord]:
        """List all saved screener definitions."""
        return list(self._screeners.values())

    def update_screener(
        self,
        screener_id: str,
        definition: ScreenerDefinition | None = None,
        schedule: str | None = None,
    ) -> ScreenerRecord | None:
        """Update existing screener definition."""
        rec = self._screeners.get(screener_id)
        if not rec:
            return None
        if definition:
            rec.name = definition.name
            rec.definition = definition
        if schedule is not None:
            rec.schedule = schedule
        rec.updated_at = datetime.now(tz=UTC)
        return rec

    def delete_screener(self, screener_id: str) -> bool:
        """Delete screener definition."""
        if screener_id in self._screeners:
            del self._screeners[screener_id]
            return True
        return False

    def save_run_snapshot(
        self, screener_id: str, screener_name: str, result: ScreenerResult
    ) -> ScreenerRunSnapshot:
        """Save an immutable execution run snapshot."""
        snapshot = ScreenerRunSnapshot(
            screener_id=screener_id,
            screener_name=screener_name,
            as_of=result.as_of,
            result=result,
        )
        self._runs[snapshot.run_id] = snapshot
        if screener_id not in self._screener_runs_index:
            self._screener_runs_index[screener_id] = []
        self._screener_runs_index[screener_id].append(snapshot.run_id)
        return snapshot

    def get_run_snapshot(self, run_id: str) -> ScreenerRunSnapshot | None:
        """Retrieve run snapshot by run ID."""
        return self._runs.get(run_id)

    def list_runs_for_screener(self, screener_id: str) -> list[ScreenerRunSnapshot]:
        """List all historical execution snapshots for a screener in reverse chronological order."""
        run_ids = self._screener_runs_index.get(screener_id, [])
        runs = [self._runs[rid] for rid in run_ids if rid in self._runs]
        runs.sort(key=lambda r: r.executed_at, reverse=True)
        return runs

    def clear(self) -> None:
        """Clear all stored screeners and run snapshots."""
        self._screeners.clear()
        self._runs.clear()
        self._screener_runs_index.clear()


# Global singleton store instance
screener_store = ScreenerStore()
