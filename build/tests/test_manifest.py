"""Acceptance tests for build/validate_manifest.py against build/manifest.yaml.

See docs/qa/acceptance/M0.5.md for the acceptance scenarios these tests satisfy.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_manifest import ManifestError, load_manifest, validate

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "manifest.yaml"
BUILD_PLAN_PATH = Path(__file__).resolve().parents[2] / "SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md"


@pytest.fixture(scope="module")
def real_items() -> list[dict]:
    return load_manifest(MANIFEST_PATH)


def test_manifest_is_valid_yaml_mapping() -> None:
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0


def test_real_manifest_passes_validation(real_items: list[dict]) -> None:
    report = validate(real_items)
    assert report.total == len(real_items)


def test_generated_count_matches_approved_102_product_features(real_items: list[dict]) -> None:
    report = validate(real_items)
    assert report.m0_count == 6
    assert report.product_count == 102
    assert report.total == 108


def test_every_id_appears_in_topological_order_exactly_once(real_items: list[dict]) -> None:
    report = validate(real_items)
    ids = {e["id"] for e in real_items}
    assert set(report.topological_order) == ids
    assert len(report.topological_order) == len(set(report.topological_order))


def test_dependencies_precede_their_dependents(real_items: list[dict]) -> None:
    report = validate(real_items)
    position = {item_id: i for i, item_id in enumerate(report.topological_order)}
    by_id = {e["id"]: e for e in real_items}
    for item_id, entry in by_id.items():
        for dep in entry["depends_on"]:
            assert position[dep] < position[item_id], (
                f"{item_id} is ordered before its dependency {dep}"
            )


def test_build_plan_names_102_product_features() -> None:
    text = BUILD_PLAN_PATH.read_text(encoding="utf-8")
    assert "The manifest counts 102 product features" in text


def test_unresolved_dependency_reference_is_rejected(real_items: list[dict]) -> None:
    broken = copy.deepcopy(real_items)
    broken[0]["depends_on"] = broken[0]["depends_on"] + ["M0.99"]
    with pytest.raises(ManifestError, match="undeclared id"):
        validate(broken)


def test_introduced_cycle_is_rejected(real_items: list[dict]) -> None:
    broken = copy.deepcopy(real_items)
    by_id = {e["id"]: e for e in broken}
    # M0.1 has no dependencies in the real manifest; force a two-node cycle
    # between it and M0.2 to prove the topological sort actually detects one.
    by_id["M0.1"]["depends_on"] = ["M0.2"]
    with pytest.raises(ManifestError, match="cycle"):
        validate(broken)


def test_missing_required_field_is_rejected(real_items: list[dict]) -> None:
    broken = copy.deepcopy(real_items)
    del broken[0]["proof"]
    with pytest.raises(ManifestError, match="missing field"):
        validate(broken)


def test_duplicate_id_is_rejected(real_items: list[dict]) -> None:
    broken = copy.deepcopy(real_items)
    broken.append(copy.deepcopy(broken[0]))
    with pytest.raises(ManifestError, match="duplicate id"):
        validate(broken)


def test_malformed_id_is_rejected(real_items: list[dict]) -> None:
    broken = copy.deepcopy(real_items)
    broken[0]["id"] = "not-a-valid-id"
    with pytest.raises(ManifestError, match="does not match"):
        validate(broken)


def test_wave_3_features_do_not_depend_on_deferred_ui_features(real_items: list[dict]) -> None:
    """Regression for build plan correction C11.

    F2.6 (wave W3, before the frontend shell exists) previously transitively
    required F2.4 (an indicator-builder UI feature deferred to after
    F4.1-F4.3) through the literal dependency range "F2.2-F2.5". Any wave-W3
    feature depending, even transitively, on a deferred UI feature would
    reintroduce the same contradiction.
    """
    deferred_ui_features = {"F2.4", "F3.11", "F3.13", "F3.14"}
    wave_3_features = {
        "F2.1", "F2.2", "F2.3", "F2.5", "F2.6", "F2.7",
        "F3.1", "F3.2", "F3.3", "F3.4", "F3.7", "F3.10", "F3.12",
    }
    by_id = {e["id"]: e for e in real_items}

    def transitive_deps(item_id: str, seen: set[str]) -> set[str]:
        for dep in by_id[item_id]["depends_on"]:
            if dep not in seen:
                seen.add(dep)
                transitive_deps(dep, seen)
        return seen

    for feature_id in wave_3_features:
        deps = transitive_deps(feature_id, set())
        overlap = deps & deferred_ui_features
        assert not overlap, f"{feature_id} transitively depends on deferred UI feature(s) {overlap}"
