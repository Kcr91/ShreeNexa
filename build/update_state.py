"""The only validated writer for build/state.json.

Usage as a library:
    from update_state import update_state
    update_state(Path("build/state.json"), feature="M0.5", status="in_progress")

Usage from the command line:
    python build/update_state.py --feature M0.5 --status in_progress \
        --branch feature/M0.5-feature-manifest

Every call re-validates the full resulting document against state_schema
before writing, and writes atomically (temp file + replace) so a crash mid-write
cannot leave build/state.json truncated or corrupt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from state_schema import StateError, validate_state

DEFAULT_STATE_PATH = Path(__file__).parent / "state.json"


def read_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate_state(doc)
    return doc


def update_state(
    path: Path,
    *,
    feature: str,
    status: str,
    branch: str | None = None,
    commit: str | None = None,
    tests: dict | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    blockers: list[str] | None = None,
) -> dict:
    """Validate the proposed fields and atomically write build/state.json.

    Fields not supplied fall back to the existing document's value only when
    updating the *same* feature (the usual case: recording branch, then
    later commit, then status, for one feature's lifecycle). Switching to a
    different `feature` starts from a clean slate instead, so a new
    feature's record can never inherit a stale `finished_at`, `blockers`, or
    other leftover field from whatever was previously tracked.
    """
    on_disk = read_state(path)
    existing = on_disk if on_disk is not None and on_disk.get("feature") == feature else {}

    doc = {
        "feature": feature,
        "status": status,
        "branch": branch if branch is not None else existing.get("branch"),
        "commit": commit if commit is not None else existing.get("commit"),
        "tests": tests if tests is not None else existing.get("tests", {}),
        "started_at": started_at if started_at is not None else existing.get("started_at"),
        "finished_at": finished_at if finished_at is not None else existing.get("finished_at"),
        "blockers": blockers if blockers is not None else existing.get("blockers", []),
    }

    validate_state(doc)

    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)
    return doc


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--feature", required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=[
            "pending",
            "in_progress",
            "review",
            "done",
            "blocked",
            "parked",
        ],
    )
    parser.add_argument("--branch")
    parser.add_argument("--commit")
    parser.add_argument("--started-at")
    parser.add_argument("--finished-at")
    parser.add_argument("--blocker", action="append", dest="blockers", default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    try:
        doc = update_state(
            args.path,
            feature=args.feature,
            status=args.status,
            branch=args.branch,
            commit=args.commit,
            started_at=args.started_at,
            finished_at=args.finished_at,
            blockers=args.blockers,
        )
    except StateError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"OK: wrote {args.path}")
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
