"""Unit tests for warehouse partition metadata, manifest hashing, and pointer contracts."""

from __future__ import annotations

import json

from app.warehouse.manifest import (
    CurrentPointer,
    PartitionMetadata,
    WarehouseManifest,
)


def test_manifest_canonical_serialization_and_hashing() -> None:
    """Verify deterministic canonical manifest JSON and SHA-256 computation."""
    p1 = PartitionMetadata(
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/part-000.parquet",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        bytes=1024,
        rows=100,
        min_ts="2026-08-01T09:15:00+00:00",
        max_ts="2026-08-01T15:30:00+00:00",
        exchange_segment="NSE_EQ",
        symbols=["RELIANCE", "HDFCBANK"],
    )

    manifest = WarehouseManifest(
        warehouse_version="wv-20260901T210000Z-test1234",
        created_at="2026-09-01T21:00:00+00:00",
        code_commit="abcdef1234567890",
        partitions=[p1],
    )

    digest1 = manifest.compute_sha256()
    json_str = manifest.to_canonical_json()
    assert isinstance(digest1, str)
    assert len(digest1) == 64

    # Deserializing and re-serializing must produce exact same digest
    manifest2 = WarehouseManifest.model_validate(json.loads(json_str))
    assert manifest2.compute_sha256() == digest1


def test_current_pointer_generation_and_json() -> None:
    """Verify CurrentPointer serialization and fields."""
    pointer = CurrentPointer(
        warehouse_version="wv-20260901T210000Z-test1234",
        manifest_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        pointer_generation=1,
        changed_at="2026-09-01T21:00:00+00:00",
        actor="worker",
        reason="initial_publish",
    )
    p_json = pointer.to_json()
    parsed = json.loads(p_json)
    assert parsed["warehouse_version"] == "wv-20260901T210000Z-test1234"
    assert parsed["pointer_generation"] == 1
