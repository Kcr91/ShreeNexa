"""Static proof of ADR-0002: no process entry module imports another's.

"The roles may share tested library modules, but one process entry point
must never import or invoke another process entry point." This parses each
entry module's own source (not a runtime import, which would only prove
today's call graph, not guard against a future accidental import) and
checks its import statements directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parents[2] / "app"

ENTRY_MODULES = {
    "api": BACKEND_APP / "main.py",
    "engine": BACKEND_APP / "engine" / "core.py",
    "feedd": BACKEND_APP / "feedd" / "core.py",
    "worker": BACKEND_APP / "worker" / "core.py",
}

OTHER_ENTRY_DOTTED_PREFIXES = {
    "api": ("app.main",),
    "engine": ("app.engine.core",),
    "feedd": ("app.feedd.core",),
    "worker": ("app.worker.core",),
}


def _imported_module_names(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_process_entry_module_imports_another() -> None:
    violations = []
    for role, path in ENTRY_MODULES.items():
        imported = _imported_module_names(path)
        for other_role, prefixes in OTHER_ENTRY_DOTTED_PREFIXES.items():
            if other_role == role:
                continue
            for prefix in prefixes:
                if any(name == prefix or name.startswith(prefix + ".") for name in imported):
                    violations.append(
                        f"{role} ({path.name}) imports {other_role}'s entry module {prefix!r}"
                    )

    assert not violations, "\n".join(violations)


def test_all_four_entry_modules_exist() -> None:
    missing = [role for role, path in ENTRY_MODULES.items() if not path.is_file()]
    assert not missing, f"missing entry module(s) for role(s): {missing}"
