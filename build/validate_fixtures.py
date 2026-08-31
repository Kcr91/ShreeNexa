"""Validate build/fixtures/ against build/fixtures/manifest.json.

Run directly: python build/validate_fixtures.py [fixtures-dir]
Exits 0 if every recorded fixture's SHA-256 matches its file on disk, no
recorded file is missing, and no extra fixture file is untracked by the
manifest. Exits 1 and prints every violation otherwise.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

DEFAULT_FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_NAME = "manifest.json"
IGNORED_NAMES = {MANIFEST_NAME, "README.md"}


class FixturesError(Exception):
    """Raised for any fixture-manifest mismatch; message lists every finding."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(fixtures_dir: Path) -> dict[str, str]:
    manifest_path = fixtures_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FixturesError(f"{manifest_path}: manifest file not found")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "files" not in data:
        raise FixturesError(f"{manifest_path}: must be a mapping with a 'files' list")
    recorded: dict[str, str] = {}
    for entry in data["files"]:
        if "path" not in entry or "sha256" not in entry:
            raise FixturesError(f"{manifest_path}: entry missing 'path' or 'sha256': {entry}")
        recorded[entry["path"]] = entry["sha256"]
    return recorded


def validate(fixtures_dir: Path) -> list[str]:
    recorded = load_manifest(fixtures_dir)

    on_disk = {
        p.name for p in fixtures_dir.iterdir() if p.is_file() and p.name not in IGNORED_NAMES
    }

    errors: list[str] = []

    missing = set(recorded) - on_disk
    for name in sorted(missing):
        errors.append(f"recorded fixture is missing from disk: {name}")

    untracked = on_disk - set(recorded)
    for name in sorted(untracked):
        errors.append(f"fixture file is not recorded in {MANIFEST_NAME}: {name}")

    for name in sorted(set(recorded) & on_disk):
        actual = sha256_of(fixtures_dir / name)
        expected = recorded[name]
        if actual != expected:
            errors.append(f"{name}: hash mismatch (expected {expected}, got {actual})")

    return errors


def main(argv: list[str]) -> int:
    fixtures_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_FIXTURES_DIR
    try:
        errors = validate(fixtures_dir)
    except FixturesError as exc:
        print(f"FAIL: {fixtures_dir}\n{exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"FAIL: {fixtures_dir}", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: {fixtures_dir}")
    print(f"{len(load_manifest(fixtures_dir))} fixture(s) verified against {MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
