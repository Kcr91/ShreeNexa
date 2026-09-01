"""Warehouse partition metadata, canonical manifest hashing, and pointer contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PartitionMetadata(BaseModel):
    """Metadata describing a single immutable Parquet partition file."""

    model_config = ConfigDict(frozen=True)

    relative_path: str
    sha256: str
    bytes: int = Field(ge=0)
    rows: int = Field(ge=0)
    min_ts: str
    max_ts: str
    exchange_segment: str
    symbols: list[str] = Field(default_factory=list)


class CorrectionMetadata(BaseModel):
    """Metadata describing a published correction."""

    model_config = ConfigDict(frozen=True)

    reason: str
    replaces_partition_digest: str


class WarehouseManifest(BaseModel):
    """Immutable version manifest recording full partition lineage and checksums."""

    model_config = ConfigDict(frozen=True)

    format_version: int = 1
    warehouse_version: str
    parent_version: str | None = None
    created_at: str
    code_commit: str
    schema_versions: dict[str, int] = Field(default_factory=lambda: {"bars": 1, "options": 1})
    source_ingest_ids: list[str] = Field(default_factory=list)
    corrections: list[CorrectionMetadata] = Field(default_factory=list)
    partitions: list[PartitionMetadata] = Field(default_factory=list)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Convert manifest to deterministic dict with sorted partitions and keys."""
        sorted_partitions = sorted(
            [p.model_dump() for p in self.partitions],
            key=lambda item: str(item["relative_path"]),
        )
        for part in sorted_partitions:
            part["symbols"] = sorted(part["symbols"])

        return {
            "format_version": self.format_version,
            "warehouse_version": self.warehouse_version,
            "parent_version": self.parent_version,
            "created_at": self.created_at,
            "code_commit": self.code_commit,
            "schema_versions": dict(sorted(self.schema_versions.items())),
            "source_ingest_ids": sorted(self.source_ingest_ids),
            "corrections": [c.model_dump() for c in self.corrections],
            "partitions": sorted_partitions,
        }

    def to_canonical_json(self) -> str:
        """Serialize manifest to deterministic canonical JSON with sorted keys."""
        return json.dumps(self.to_canonical_dict(), indent=2, sort_keys=True)

    def compute_sha256(self) -> str:
        """Compute SHA-256 hex digest of the canonical manifest JSON."""
        canonical_bytes = self.to_canonical_json().encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()


class CurrentPointer(BaseModel):
    """Active warehouse version pointer written to `warehouse/current.json`."""

    model_config = ConfigDict(frozen=True)

    format_version: int = 1
    warehouse_version: str
    manifest_sha256: str
    pointer_generation: int = Field(default=1, ge=1)
    changed_at: str
    actor: str = "worker"
    reason: str = "initial_publish"

    def to_json(self) -> str:
        """Serialize pointer to JSON string."""
        return json.dumps(self.model_dump(), indent=2, sort_keys=True)
