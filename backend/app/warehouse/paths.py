"""Single source of truth for the ShreeNexa data root and write admission.

``SHREENEXA_DATA_ROOT`` is specified in ``docs/architecture/data-lifecycle.md`` but was
never implemented: ``DEFAULT_DATA_ROOT`` was redefined independently in five modules, so
the override had nowhere to take effect. Everything that touches the data root resolves
it through :func:`resolve_data_root` instead.

The capacity alarm from the same document lives here too. A multi-week backfill writes
tens of gigabytes, and a disk that fills mid-partition is exactly the failure the
warehouse's atomic-write design cannot protect against on its own.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"

DATA_ROOT_ENV_VAR = "SHREENEXA_DATA_ROOT"
OWNERSHIP_MARKER = ".shreenexa-data-root.json"

# Refuse new partitions below this much free space; warn below the second threshold.
MIN_FREE_BYTES = 2 * 1024**3
WARN_FREE_BYTES = 10 * 1024**3


class DataRootCapacityError(RuntimeError):
    """Raised when a write is refused because the data root is nearly full."""

    def __init__(self, data_root: Path, free_bytes: int, required_bytes: int) -> None:
        self.data_root = data_root
        self.free_bytes = free_bytes
        self.required_bytes = required_bytes
        super().__init__(
            f"Refusing to write to {data_root}: {free_bytes / 1024**3:.2f} GiB free, "
            f"{required_bytes / 1024**3:.2f} GiB required. "
            "Free space or point SHREENEXA_DATA_ROOT at a larger volume."
        )


@dataclass(frozen=True)
class DiskUsage:
    """Snapshot of free space for a data root."""

    data_root: Path
    total_bytes: int
    used_bytes: int
    free_bytes: int

    @property
    def free_gib(self) -> float:
        return self.free_bytes / 1024**3

    @property
    def percent_used(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return 100.0 * self.used_bytes / self.total_bytes


def resolve_data_root(explicit: Path | str | None = None) -> Path:
    """Resolve the data root: explicit argument, then env override, then repo default.

    The path is returned resolved but is not created; callers that write use
    ``ensure_data_root`` in the publisher for that.
    """
    if explicit is not None:
        return Path(explicit).resolve()

    override = os.environ.get(DATA_ROOT_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser().resolve()

    return DEFAULT_DATA_ROOT.resolve()


def get_disk_usage(data_root: Path | str | None = None) -> DiskUsage:
    """Return free-space statistics for the volume holding the data root.

    Falls back to the nearest existing parent, so this works before the root exists.
    """
    root = resolve_data_root(data_root)

    probe = root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent

    usage = shutil.disk_usage(probe)
    return DiskUsage(
        data_root=root,
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
    )


def check_write_admission(
    data_root: Path | str | None = None,
    required_bytes: int = MIN_FREE_BYTES,
) -> DiskUsage:
    """Raise DataRootCapacityError when free space is below the required amount.

    Called before staging a partition so a long backfill stops cleanly at a window
    boundary rather than failing partway through a Parquet write.
    """
    usage = get_disk_usage(data_root)

    if usage.free_bytes < required_bytes:
        raise DataRootCapacityError(usage.data_root, usage.free_bytes, required_bytes)

    if usage.free_bytes < WARN_FREE_BYTES:
        logger.warning(
            "Data root %s is low on space: %.2f GiB free (%.1f%% of volume used)",
            usage.data_root,
            usage.free_gib,
            usage.percent_used,
        )

    return usage
