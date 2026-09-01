"""Architecture AST tests verifying no Dhan REST calls bypass rate limiting."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"


def test_dhan_rest_client_calls_limiter_acquire() -> None:
    """AST check: DhanRestClient._request must call limiter.acquire."""
    client_file = APP_DIR / "dhan" / "client.py"
    assert client_file.is_file()

    tree = ast.parse(client_file.read_text(encoding="utf-8"), filename=str(client_file))

    found_acquire_call = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_request":
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "acquire"
                ):
                    found_acquire_call = True
                    break

    assert found_acquire_call, (
        "DhanRestClient._request MUST invoke limiter.acquire before sending HTTP requests"
    )


def test_no_bypassing_http_calls_in_dhan_package() -> None:
    """AST check: only HTTPTransport in transport.py and DhanRestClient may call HTTP."""
    allowed_http_modules = {"transport.py"}

    dhan_dir = APP_DIR / "dhan"
    for py_file in dhan_dir.glob("*.py"):
        if py_file.name in allowed_http_modules:
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in (
                        "urllib.request",
                        "http.client",
                        "requests",
                        "httpx",
                    ), (
                        f"Direct HTTP client import '{alias.name}' forbidden in {py_file.name}; "
                        "all HTTP requests must route through DhanRestClient with rate limiting."
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module not in (
                    "urllib.request",
                    "http.client",
                    "requests",
                    "httpx",
                ), (
                    f"Direct HTTP client import from '{node.module}' forbidden in {py_file.name}; "
                    "all HTTP requests must route through DhanRestClient with rate limiting."
                )
