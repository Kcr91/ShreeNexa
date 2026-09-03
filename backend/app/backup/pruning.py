"""Backup retention policy and safe pruning engine (F13.4)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PruningPolicy:
    """Retention configuration for backup snapshots."""

    max_daily: int = 30
    min_retained: int = 5


def prune_backups(
    backup_dir: Path,
    policy: PruningPolicy | None = None,
) -> list[Path]:
    """Prune expired backups according to retention policy, protecting recent snapshots."""
    pol = policy or PruningPolicy()
    if not backup_dir.exists():
        return []

    # Find all .tar.gz archives
    archives: list[Path] = [
        f for f in backup_dir.iterdir()
        if f.is_file() and f.name.endswith(".tar.gz")
    ]

    # Sort archives by modification/creation time descending (newest first)
    archives.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Never delete if count <= min_retained
    if len(archives) <= pol.min_retained:
        return []

    # Keep the newest max_daily snapshots
    to_delete = archives[pol.max_daily:]
    deleted: list[Path] = []

    for arch in to_delete:
        try:
            arch.unlink(missing_ok=True)
            # Also clean companion manifest if present
            manifest_file = arch.with_suffix("").with_suffix(".manifest.json")
            if manifest_file.exists():
                manifest_file.unlink(missing_ok=True)
            deleted.append(arch)
        except OSError:
            pass

    return deleted
