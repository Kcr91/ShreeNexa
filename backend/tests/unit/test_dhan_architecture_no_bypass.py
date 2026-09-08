"""Architecture AST tests verifying no Dhan REST calls bypass rate limiting."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"


def _calls_attr(node: ast.AST, attr: str) -> bool:
    """Return True when the subtree contains a call to ``.<attr>(...)``."""
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr == attr
        for child in ast.walk(node)
    )


def _sends_http(node: ast.AST) -> bool:
    """Return True when the subtree invokes ``self.transport.request(...)``."""
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "request"
            and isinstance(child.func.value, ast.Attribute)
            and child.func.value.attr == "transport"
        ):
            return True
    return False


def test_every_transport_call_site_acquires_a_limiter_token() -> None:
    """AST check: any function sending HTTP must acquire a rate-limiter token.

    Pinned structurally rather than to a single method name, so a newly added
    method that calls the transport directly cannot silently bypass the limiter.
    Retries count too: each attempt must take its own token, otherwise retried
    calls overrun the documented per-day budgets in config/dhan_limits.yaml.
    """
    client_file = APP_DIR / "dhan" / "client.py"
    assert client_file.is_file()

    tree = ast.parse(client_file.read_text(encoding="utf-8"), filename=str(client_file))

    senders = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _sends_http(node)
    ]

    assert senders, (
        "No function in client.py calls self.transport.request; the limiter "
        "architecture guard would pass vacuously."
    )

    for func in senders:
        assert _calls_attr(func, "acquire"), (
            f"DhanRestClient.{func.name} sends an HTTP request without calling "
            "limiter.acquire; every attempt must consume a rate-limit token."
        )


def test_request_entrypoint_reaches_the_limiter() -> None:
    """AST check: _request must acquire a token itself or delegate to one that does."""
    client_file = APP_DIR / "dhan" / "client.py"
    tree = ast.parse(client_file.read_text(encoding="utf-8"), filename=str(client_file))

    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    request_fn = functions.get("_request")
    assert request_fn is not None, "DhanRestClient._request must exist"

    if _calls_attr(request_fn, "acquire"):
        return

    delegates = [
        child.func.attr
        for child in ast.walk(request_fn)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr in functions
    ]
    assert any(_calls_attr(functions[name], "acquire") for name in delegates), (
        "DhanRestClient._request MUST invoke limiter.acquire, directly or through "
        "a helper that does, before sending HTTP requests"
    )


def test_no_bypassing_http_calls_in_dhan_package() -> None:
    """AST check: only HTTPTransport in transport.py and DhanRestClient may call HTTP."""
    # transport.py executes Dhan REST calls; ip.py queries external IP discovery echo services
    allowed_http_modules = {"transport.py", "ip.py"}

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
