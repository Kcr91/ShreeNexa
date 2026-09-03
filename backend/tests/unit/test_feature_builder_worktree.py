"""Unit and property/acceptance tests for worktree isolation and path validation (F11.2).

Proof requirement: Property/acceptance tests prove the runner cannot write outside
its worktree.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from app.feature_builder.worktree import (
    PathEscapeViolationError,
    WorktreeManager,
    safe_write_worktree_file,
    validate_worktree_path,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def local_tmp_path() -> Iterator[Path]:
    """Isolated local temporary path fixture within repo build root."""
    base = Path("build/test_tmp").resolve()
    base.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="wt_test_", dir=base)
    p = Path(temp_dir).resolve()
    try:
        yield p
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_safe_write_inside_worktree(local_tmp_path: Path) -> None:
    """Proof: Operations strictly within the worktree succeed and write correct content."""
    worktree_root = local_tmp_path / "sandbox_wt"
    worktree_root.mkdir()

    rel_path = "backend/app/feature/calc.py"
    content = "def calculate(): return 42\n"

    written = safe_write_worktree_file(rel_path, content, worktree_root)

    assert written.exists()
    assert written.read_text(encoding="utf-8") == content
    assert written.is_relative_to(worktree_root)


@pytest.mark.parametrize(
    "escaping_path",
    [
        "../outside.txt",
        "../../root.py",
        "nested/../../escape.json",
        "a/b/../../../danger.sh",
    ],
)
def test_denial_of_parent_directory_traversal(local_tmp_path: Path, escaping_path: str) -> None:
    """Proof: Any path traversal attempting to escape the worktree root is blocked."""
    worktree_root = local_tmp_path / "sandbox_wt"
    worktree_root.mkdir()

    with pytest.raises(PathEscapeViolationError) as exc_info:
        validate_worktree_path(escaping_path, worktree_root)

    assert "Path escape violation" in str(exc_info.value)

    with pytest.raises(PathEscapeViolationError):
        safe_write_worktree_file(escaping_path, "malicious", worktree_root)


def test_denial_of_absolute_paths_outside_worktree(local_tmp_path: Path) -> None:
    """Proof: Absolute paths resolving outside the worktree are strictly denied."""
    worktree_root = local_tmp_path / "sandbox_wt"
    worktree_root.mkdir()

    external_dir = local_tmp_path / "external_system"
    external_dir.mkdir()
    target_abs = external_dir / "target.py"

    with pytest.raises(PathEscapeViolationError) as exc_info:
        validate_worktree_path(target_abs, worktree_root)

    assert "Path escape violation" in str(exc_info.value)

    with pytest.raises(PathEscapeViolationError):
        safe_write_worktree_file(target_abs, "content", worktree_root)


def test_denial_of_legacy_project_path(local_tmp_path: Path) -> None:
    """Proof: Hard boundary enforcement blocking any reference to legacy project."""
    worktree_root = local_tmp_path / "sandbox_wt"
    worktree_root.mkdir()

    legacy_subpath = "F:/Algotrading/legacy_strategy.py"
    with pytest.raises(PathEscapeViolationError) as exc_info:
        validate_worktree_path(legacy_subpath, worktree_root)

    assert "legacy project path prohibited" in str(exc_info.value).lower()


def test_worktree_manager_allocation_and_cleanup(local_tmp_path: Path) -> None:
    """Proof: WorktreeManager provisions isolated worktrees and cleans them up cleanly."""
    repo_root = local_tmp_path / "repo"
    repo_root.mkdir()
    wt_dir = local_tmp_path / "worktrees"
    manager = WorktreeManager(repo_root=repo_root, worktree_base_dir=wt_dir)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        alloc = manager.create_worktree(
            feature_id="F12.1",
            branch_name="feature/F12.1-custom-analytics",
            base_commit="HEAD",
        )

        assert alloc.feature_id == "F12.1"
        assert alloc.status == "ACTIVE"
        assert alloc.worktree_id.startswith("wt-")
        assert Path(alloc.worktree_path).parent == wt_dir.resolve()

        # Retrieve worktree
        fetched = manager.get_worktree(alloc.worktree_id)
        assert fetched is not None
        assert fetched.worktree_id == alloc.worktree_id

        # Cleanup worktree
        success = manager.cleanup_worktree(alloc.worktree_id)
        assert success is True
        assert manager.get_worktree(alloc.worktree_id).status == "CLEANED"  # type: ignore[union-attr]


def test_reconcile_and_recover_orphaned_worktrees(local_tmp_path: Path) -> None:
    """Proof: Recovers and prunes orphaned worktree directories on disk."""
    repo_root = local_tmp_path / "repo"
    repo_root.mkdir()
    wt_dir = local_tmp_path / "worktrees"
    wt_dir.mkdir(parents=True)

    # Simulate an orphaned directory left behind by a crash
    orphaned_dir = wt_dir / "F9.9_orphaned_task"
    orphaned_dir.mkdir()
    (orphaned_dir / "dirty_file.txt").write_text("crash artifact", encoding="utf-8")

    manager = WorktreeManager(repo_root=repo_root, worktree_base_dir=wt_dir)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        recovered = manager.reconcile_and_recover()

        assert len(recovered) == 1
        assert str(orphaned_dir) in recovered
        assert not orphaned_dir.exists()


def test_worktree_rest_api_endpoints() -> None:
    """Proof: REST API endpoints for worktree provisioning, listing, and recovery."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        # 1. Create worktree
        resp = client.post(
            "/api/v1/feature-builder/worktrees",
            json={
                "feature_id": "F13.1",
                "branch_name": "feature/F13.1-production-containers",
                "base_commit": "HEAD",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        wt_id = data["worktree_id"]
        assert data["feature_id"] == "F13.1"
        assert data["status"] == "ACTIVE"

        # 2. Get worktree
        get_resp = client.get(f"/api/v1/feature-builder/worktrees/{wt_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["worktree_id"] == wt_id

        # 3. List worktrees
        list_resp = client.get("/api/v1/feature-builder/worktrees")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 4. Reconcile worktrees
        rec_resp = client.post("/api/v1/feature-builder/worktrees/reconcile")
        assert rec_resp.status_code == 200
        assert rec_resp.json()["status"] == "RECONCILED"

        # 5. Delete worktree
        del_resp = client.delete(f"/api/v1/feature-builder/worktrees/{wt_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "CLEANED"
