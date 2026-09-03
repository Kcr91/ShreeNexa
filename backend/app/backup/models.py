"""Data models and schemas for backup creation, integrity manifests, and restoration (F13.4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    """File metadata with cryptographic SHA-256 digest."""

    relative_path: str = Field(..., description="Path relative to backup root")
    size_bytes: int = Field(..., ge=0, description="Size in bytes")
    sha256: str = Field(..., min_length=64, max_length=64, description="Hex-encoded SHA-256 digest")


class DatabaseTableRecord(BaseModel):
    """Database table metadata with row count and deterministic content hash."""

    table_name: str = Field(..., description="Name of Postgres table")
    row_count: int = Field(..., ge=0, description="Total number of rows")
    content_sha256: str = Field(
        ..., min_length=64, max_length=64, description="Deterministic content digest"
    )


class BackupManifest(BaseModel):
    """Authoritative integrity manifest recorded at backup creation."""

    backup_id: str = Field(..., description="Unique backup identifier")
    created_at: datetime = Field(..., description="Timestamp of backup completion")
    git_commit: str = Field(..., description="Git commit SHA active at backup time")
    tables: list[DatabaseTableRecord] = Field(
        default_factory=list, description="Postgres database tables"
    )
    warehouse_files: list[FileRecord] = Field(
        default_factory=list, description="DuckDB Parquet partitions"
    )
    config_files: list[FileRecord] = Field(
        default_factory=list, description="Configuration and specification files"
    )
    total_size_bytes: int = Field(default=0, ge=0)
    archive_sha256: str | None = Field(default=None, description="SHA-256 digest of tarball bundle")
    encrypted: bool = Field(default=False, description="Whether the bundle is AES encrypted")


class ReconciliationItem(BaseModel):
    """Audit comparison of a single database table or file between manifest and restore."""

    name: str
    kind: str  # "table" or "warehouse_file" or "config_file"
    manifest_count: int | None = None
    restored_count: int | None = None
    manifest_hash: str
    restored_hash: str
    matches: bool


class RestoreVerificationReport(BaseModel):
    """Formal audit report proving reconciliation between backup manifest and restored box."""

    backup_id: str
    restored_at: datetime
    target_dir: str
    total_items_checked: int
    all_matched: bool
    discrepancies: list[str] = Field(default_factory=list)
    items: list[ReconciliationItem] = Field(default_factory=list)
