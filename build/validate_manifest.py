"""Validate build/manifest.yaml: schema, dependency references, cycles, and counts.

Run directly: python build/validate_manifest.py [path-to-manifest.yaml]
Exits 0 and prints generated counts on success; exits 1 and prints every
violation on failure. Counts are always computed from the manifest's own
`items` list — never hardcoded here or in the manifest file itself.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REQUIRED_FIELDS = ("id", "name", "depends_on", "proof", "model")
ID_PATTERN = re.compile(r"^(M0\.[1-6]|F\d{1,2}\.\d{1,2})$")
DEFAULT_MANIFEST = Path(__file__).parent / "manifest.yaml"


class ManifestError(Exception):
    """Raised for any manifest violation; message lists every finding found."""


@dataclass
class ManifestReport:
    total: int
    m0_count: int
    product_count: int
    topological_order: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"items: {self.total} (M0 tasks: {self.m0_count}, "
            f"product features: {self.product_count})"
        )


def load_manifest(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        raise ManifestError(f"{path}: top level must be a mapping with an 'items' list")
    items = data["items"]
    if not isinstance(items, list) or not items:
        raise ManifestError(f"{path}: 'items' must be a non-empty list")
    return items


def validate(items: list[dict]) -> ManifestReport:
    errors: list[str] = []
    ids_seen: dict[str, int] = {}

    for i, entry in enumerate(items):
        where = f"items[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: entry is not a mapping")
            continue

        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            errors.append(f"{where} ({entry.get('id', '?')}): missing field(s) {missing}")
            continue

        item_id = entry["id"]
        if not isinstance(item_id, str) or not ID_PATTERN.match(item_id):
            errors.append(f"{where}: id {item_id!r} does not match {ID_PATTERN.pattern}")
        if item_id in ids_seen:
            first = ids_seen[item_id]
            errors.append(f"{where}: duplicate id {item_id!r} (first at items[{first}])")
        else:
            ids_seen[item_id] = i

        if not isinstance(entry["depends_on"], list):
            errors.append(f"{where} ({item_id}): depends_on must be a list")
        if not isinstance(entry["name"], str) or not entry["name"].strip():
            errors.append(f"{where} ({item_id}): name must be a non-empty string")
        if not isinstance(entry["proof"], str) or not entry["proof"].strip():
            errors.append(f"{where} ({item_id}): proof must be a non-empty string")
        if not isinstance(entry["model"], str) or not entry["model"].strip():
            errors.append(f"{where} ({item_id}): model must be a non-empty string")

    if errors:
        bullets = "\n".join(f"  - {e}" for e in errors)
        raise ManifestError(f"manifest schema violations:\n{bullets}")

    known_ids = set(ids_seen)
    dep_errors: list[str] = []
    for entry in items:
        for dep in entry["depends_on"]:
            if dep not in known_ids:
                dep_errors.append(f"{entry['id']} depends on undeclared id {dep!r}")
    if dep_errors:
        bullets = "\n".join(f"  - {e}" for e in dep_errors)
        raise ManifestError(f"unresolved dependency reference(s):\n{bullets}")

    order = _topological_sort(items)

    total = len(items)
    m0_count = sum(1 for e in items if e["id"].startswith("M0."))
    product_count = total - m0_count

    return ManifestReport(
        total=total, m0_count=m0_count, product_count=product_count, topological_order=order
    )


def _topological_sort(items: list[dict]) -> list[str]:
    depends_on = {e["id"]: list(e["depends_on"]) for e in items}
    permanent: set[str] = set()
    temporary: set[str] = set()
    order: list[str] = []

    def visit(node: str, stack: list[str]) -> None:
        if node in permanent:
            return
        if node in temporary:
            cycle = " -> ".join([*stack[stack.index(node) :], node])
            raise ManifestError(f"dependency cycle detected: {cycle}")
        temporary.add(node)
        for dep in depends_on[node]:
            visit(dep, [*stack, node])
        temporary.discard(node)
        permanent.add(node)
        order.append(node)

    for item_id in depends_on:
        visit(item_id, [])

    return order


def main(argv: list[str]) -> int:
    manifest_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_MANIFEST
    try:
        items = load_manifest(manifest_path)
        report = validate(items)
    except ManifestError as exc:
        print(f"FAIL: {manifest_path}\n{exc}", file=sys.stderr)
        return 1

    print(f"OK: {manifest_path}")
    print(report.summary())
    print("topological sort succeeded (no cycles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
