"""Tests for the validated build/state.json helper (state_schema + update_state)."""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state_schema import StateError, validate_state
from update_state import read_state, update_state


@pytest.fixture()
def tmp_path() -> Path:
    """Repo-local temp dir (covered by .gitignore's `tmp/` rule).

    Overrides pytest's built-in `tmp_path`, which resolves under the OS temp
    root; that root is not writable in this sandboxed environment.
    """
    directory = Path(__file__).parent / "tmp" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_valid_document_passes() -> None:
    validate_state(
        {
            "feature": "M0.5",
            "status": "in_progress",
            "branch": "feature/M0.5-feature-manifest",
            "commit": None,
            "tests": {},
            "started_at": "2026-08-31",
            "finished_at": None,
            "blockers": [],
        }
    )


def test_invalid_status_is_rejected() -> None:
    with pytest.raises(StateError, match="status"):
        validate_state(
            {
                "feature": "M0.5",
                "status": "almost_done",
                "branch": None,
                "commit": None,
                "tests": {},
                "started_at": None,
                "finished_at": None,
                "blockers": [],
            }
        )


def test_merged_unverified_is_distinct_from_verified_done() -> None:
    validate_state(
        {
            "feature": "F0.4",
            "status": "merged_unverified",
            "branch": "feature/F0.4-central-settings",
            "commit": "a" * 40,
            "tests": {},
            "started_at": None,
            "finished_at": None,
            "blockers": [],
            "features": {
                "F0.4": {
                    "status": "merged_unverified",
                    "branch": "feature/F0.4-central-settings",
                    "commit": "a" * 40,
                    "tests": {},
                    "evidence": [],
                    "verified_at": None,
                    "blockers": [],
                }
            },
        }
    )


def test_verified_done_requires_exact_evidence_and_no_blocker(tmp_path: Path) -> None:
    with pytest.raises(StateError, match="cannot be done"):
        update_state(
            tmp_path / "state.json",
            feature="F0.4",
            status="done",
            commit="a" * 40,
        )


def test_missing_field_is_rejected() -> None:
    with pytest.raises(StateError, match="missing required field"):
        validate_state({"feature": "M0.5", "status": "pending"})


def test_unexpected_field_is_rejected() -> None:
    with pytest.raises(StateError, match="unexpected field"):
        validate_state(
            {
                "feature": "M0.5",
                "status": "pending",
                "branch": None,
                "commit": None,
                "tests": {},
                "started_at": None,
                "finished_at": None,
                "blockers": [],
                "notes": "not allowed here",
            }
        )


def test_update_state_writes_atomically_and_round_trips(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    doc = update_state(
        state_path,
        feature="M0.5",
        status="in_progress",
        branch="feature/M0.5-feature-manifest",
    )
    assert doc["feature"] == "M0.5"
    assert not (tmp_path / "state.json.tmp").exists()

    on_disk = json.loads(state_path.read_text(encoding="utf-8"))
    assert on_disk == doc
    assert read_state(state_path) == doc


def test_update_state_preserves_unset_fields_across_calls(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    update_state(
        state_path, feature="M0.5", status="in_progress", branch="feature/M0.5-feature-manifest"
    )
    doc = update_state(state_path, feature="M0.5", status="review")

    assert doc["status"] == "review"
    assert doc["branch"] == "feature/M0.5-feature-manifest"


def test_update_state_rejects_invalid_status(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with pytest.raises(StateError):
        update_state(state_path, feature="M0.5", status="almost_done")
    assert not state_path.exists()


def test_update_state_does_not_leak_fields_across_features(tmp_path: Path) -> None:
    """Regression: switching features must not inherit the prior feature's
    finished_at/blockers/branch/commit/tests -- only continuing the *same*
    feature's lifecycle should carry those forward."""
    state_path = tmp_path / "state.json"
    update_state(
        state_path,
        feature="M0.5",
        status="blocked",
        branch="feature/M0.5-feature-manifest",
        commit="abc1234",
        finished_at="2026-08-31",
        blockers=["some prior blocker"],
    )

    doc = update_state(state_path, feature="M0.6", status="in_progress")

    assert doc["feature"] == "M0.6"
    assert doc["branch"] is None
    assert doc["commit"] is None
    assert doc["finished_at"] is None
    assert doc["blockers"] == []
