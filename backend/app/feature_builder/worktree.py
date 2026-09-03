"""Git worktree isolation, branch ownership, path validation, and recovery (F11.2).

Proof requirement: Property/acceptance tests prove the runner cannot write outside
its worktree.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PathEscapeViolationError(PermissionError):
    """Raised when an operation attempts to access or write outside the designated worktree."""


class WorktreeAllocation(BaseModel):
    """Tracked worktree environment assigned to a feature building task."""

    model_config = ConfigDict(frozen=True)

    worktree_id: str
    feature_id: str
    branch_name: str
    worktree_path: str
    base_commit: str
    created_at: datetime
    status: str = "ACTIVE"  # ACTIVE, CLEANED, ORPHANED


class WorktreeCreateRequest(BaseModel):
    """Payload to request creation of an isolated worktree."""

    model_config = ConfigDict(extra="ignore")

    feature_id: str
    branch_name: str
    base_commit: str = "HEAD"


def validate_worktree_path(target: str | Path, worktree_root: str | Path) -> Path:
    """Strictly validate that a target path resolves within the designated worktree root.

    Raises:
        PathEscapeViolationError: if path escapes worktree root or touches legacy project.
    """
    resolved_root = Path(worktree_root).resolve()
    target_p = Path(target)

    if target_p.is_absolute():
        resolved_target = target_p.resolve()
    else:
        resolved_target = (resolved_root / target_p).resolve()

    # Invariant: Must not point into legacy project boundary F:\Algotrading
    target_str = str(resolved_target).lower()
    if "algotrading" in target_str:
        raise PathEscapeViolationError(
            f"Access to legacy project path prohibited: '{resolved_target}'"
        )

    # Invariant: Must strictly be within worktree_root (Proof requirement)
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise PathEscapeViolationError(
            f"Path escape violation: '{target}' resolves to '{resolved_target}', "
            f"which is outside the worktree root '{resolved_root}'"
        ) from exc

    return resolved_target


def safe_write_worktree_file(
    target: str | Path,
    content: str | bytes,
    worktree_root: str | Path,
) -> Path:
    """Safely write data to a file inside the worktree after strict boundary validation."""
    valid_path = validate_worktree_path(target, worktree_root)
    valid_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, str):
        valid_path.write_text(content, encoding="utf-8")
    else:
        valid_path.write_bytes(content)

    return valid_path


class WorktreeManager:
    """Manages Git worktree lifecycle, branch ownership, cleanup, and recovery."""

    def __init__(
        self,
        repo_root: Path | None = None,
        worktree_base_dir: Path | None = None,
    ) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.worktree_base_dir = (
            worktree_base_dir or (self.repo_root / "build" / "worktrees")
        ).resolve()
        self._allocations: dict[str, WorktreeAllocation] = {}

    def create_worktree(
        self,
        feature_id: str,
        branch_name: str,
        base_commit: str = "HEAD",
    ) -> WorktreeAllocation:
        """Create a dedicated Git worktree and check out an owned feature branch."""
        # Sanitize branch name
        sanitized_slug = re.sub(r"[^a-zA-Z0-9_\.-]", "-", branch_name).strip("-")
        worktree_id = f"wt-{uuid.uuid4().hex[:8]}"
        worktree_path = (self.worktree_base_dir / f"{feature_id}_{worktree_id}").resolve()

        self.worktree_base_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git",
            "worktree",
            "add",
            "-b",
            sanitized_slug,
            str(worktree_path),
            base_commit,
        ]

        try:
            subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as err:
            raise RuntimeError(
                f"Failed to create git worktree: {err.stderr.strip() or err.stdout.strip()}"
            ) from err

        allocation = WorktreeAllocation(
            worktree_id=worktree_id,
            feature_id=feature_id,
            branch_name=sanitized_slug,
            worktree_path=str(worktree_path),
            base_commit=base_commit,
            created_at=datetime.now(),
            status="ACTIVE",
        )

        self._allocations[worktree_id] = allocation
        return allocation

    def cleanup_worktree(self, worktree_id: str) -> bool:
        """Prune and remove an allocated Git worktree cleanly."""
        allocation = self._allocations.get(worktree_id)
        if not allocation:
            return False

        wt_path = Path(allocation.worktree_path)

        # Remove git worktree entry
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Prune worktree metadata
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=15,
        )

        # Fallback directory removal if git worktree remove left artifacts
        if wt_path.exists():
            shutil.rmtree(wt_path, ignore_errors=True)

        self._allocations[worktree_id] = allocation.model_copy(update={"status": "CLEANED"})
        return True

    def get_worktree(self, worktree_id: str) -> WorktreeAllocation | None:
        """Lookup an allocation by worktree_id."""
        return self._allocations.get(worktree_id)

    def list_worktrees(self) -> list[WorktreeAllocation]:
        """List all tracked worktree allocations."""
        return list(self._allocations.values())

    def reconcile_and_recover(self) -> list[str]:
        """Audit filesystem and Git state to cleanly recover and prune orphaned worktrees."""
        recovered: list[str] = []

        # Run git worktree prune first
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=15,
        )

        if not self.worktree_base_dir.exists():
            return recovered

        # Check directory children against active allocations
        active_paths = {
            Path(alloc.worktree_path).resolve()
            for alloc in self._allocations.values()
            if alloc.status == "ACTIVE"
        }

        for item in self.worktree_base_dir.iterdir():
            if item.is_dir() and item.resolve() not in active_paths:
                # Orphaned directory: safely remove
                shutil.rmtree(item, ignore_errors=True)
                recovered.append(str(item))

        return recovered


# Global singleton manager
worktree_manager = WorktreeManager()
