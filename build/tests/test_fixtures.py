"""Tests for build/validate_fixtures.py and the frozen reference fixtures.

See docs/qa/acceptance/M0.6.md for the acceptance scenarios these satisfy.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_fixtures import sha256_of, validate

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture()
def scratch_fixtures_dir() -> Path:
    """A disposable copy of build/fixtures/ so tampering tests don't touch the real files."""
    directory = Path(__file__).parent / "tmp" / uuid.uuid4().hex
    shutil.copytree(FIXTURES_DIR, directory)
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_real_fixtures_pass_validation() -> None:
    errors = validate(FIXTURES_DIR)
    assert errors == []


def test_tampered_fixture_is_detected(scratch_fixtures_dir: Path) -> None:
    csv_path = scratch_fixtures_dir / "ohlc_synthetic_10bar.csv"
    original = csv_path.read_bytes()
    csv_path.write_bytes(original[:-2] + b"9\n")  # flip the final digit

    errors = validate(scratch_fixtures_dir)
    assert any("hash mismatch" in e for e in errors)


def test_untracked_extra_fixture_is_detected(scratch_fixtures_dir: Path) -> None:
    (scratch_fixtures_dir / "extra_untracked.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    errors = validate(scratch_fixtures_dir)
    assert any("not recorded" in e for e in errors)


def test_missing_recorded_fixture_is_detected(scratch_fixtures_dir: Path) -> None:
    (scratch_fixtures_dir / "ohlc_synthetic_10bar.csv").unlink()

    errors = validate(scratch_fixtures_dir)
    assert any("missing from disk" in e for e in errors)


def test_manifest_hashes_are_not_stale(scratch_fixtures_dir: Path) -> None:
    """The manifest's own recorded digests must equal the real file hashes."""
    manifest = json.loads((scratch_fixtures_dir / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        actual = sha256_of(scratch_fixtures_dir / entry["path"])
        assert actual == entry["sha256"], f"{entry['path']} manifest hash is stale"


def _load_closes() -> list[float]:
    with open(FIXTURES_DIR / "ohlc_synthetic_10bar.csv", newline="", encoding="utf-8") as f:
        return [float(row["close"]) for row in csv.DictReader(f)]


def test_sma3_reference_matches_independent_recomputation() -> None:
    closes = _load_closes()
    reference = json.loads((FIXTURES_DIR / "sma_ema_reference.json").read_text(encoding="utf-8"))
    window = reference["window"]

    for entry in reference["values"]:
        i = entry["index"]
        if i < window - 1:
            assert entry["sma3"] is None
            continue
        expected = sum(closes[i - window + 1 : i + 1]) / window
        assert entry["sma3"] == pytest.approx(expected)


def test_ema3_reference_matches_independent_recomputation() -> None:
    closes = _load_closes()
    reference = json.loads((FIXTURES_DIR / "sma_ema_reference.json").read_text(encoding="utf-8"))
    window = reference["window"]
    k = 2 / (window + 1)

    ema = None
    for entry in reference["values"]:
        i = entry["index"]
        if i < window - 1:
            assert entry["ema3"] is None
            continue
        if i == window - 1:
            ema = sum(closes[:window]) / window
        else:
            ema = closes[i] * k + ema * (1 - k)
        assert entry["ema3"] == pytest.approx(ema)


def test_warm_up_bars_are_null_not_partial_average() -> None:
    reference = json.loads((FIXTURES_DIR / "sma_ema_reference.json").read_text(encoding="utf-8"))
    window = reference["window"]
    warm_up = [e for e in reference["values"] if e["index"] < window - 1]

    assert len(warm_up) == window - 1
    for entry in warm_up:
        assert entry["sma3"] is None
        assert entry["ema3"] is None
