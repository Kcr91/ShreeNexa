"""Tests for API authentication and CSRF protection enforcement (QA-02 / F13.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.auth.models import SessionInfo
from app.auth.service import auth_service
from app.main import app
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

PUBLIC_ROUTE_ALLOWLIST = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/healthz",
    "/api/v1/auth/login",
    "/api/v1/auth/totp/verify",
    "/api/v1/auth/recovery",
    "/api/v1/auth/logout",
    "/api/v1/auth/me",
    "/api/v1/auth/audit",
    "/api/v1/feed/ws",
    "",  # Mount path for websocket router
}


def _extract_all_routes(application: object) -> list[tuple[str, set[str], list[str]]]:
    """Extract (path, methods, dependency_names) for all registered endpoints."""
    routes: list[tuple[str, set[str], list[str]]] = []
    for r in getattr(application, "routes", []):
        if hasattr(r, "effective_route_contexts"):
            for ctx in r.effective_route_contexts():
                dep_names = [
                    getattr(d.dependency, "__name__", str(d.dependency)) for d in ctx.dependencies
                ]
                routes.append((ctx.path, set(ctx.methods), dep_names))
        elif isinstance(r, APIRoute):
            dep_names = [
                getattr(d.dependency, "__name__", str(d.dependency)) for d in r.dependencies
            ]
            routes.append((r.path, set(r.methods or ()), dep_names))
        elif hasattr(r, "path"):
            dep_names = [
                getattr(d.dependency, "__name__", str(d.dependency))
                for d in getattr(r, "dependencies", [])
            ]
            raw_methods = getattr(r, "methods", ()) or ()
            routes.append((r.path, set(raw_methods), dep_names))
    return routes


def test_all_non_allowlisted_routes_require_session_dependency() -> None:
    """Architecture test: verify every non-public route enforces require_session."""
    all_routes = _extract_all_routes(app)
    assert len(all_routes) > 20, "Expected full complement of API routes"

    unprotected: list[tuple[str, set[str], list[str]]] = []
    for path, methods, deps in all_routes:
        if path in PUBLIC_ROUTE_ALLOWLIST:
            continue
        if "require_session" not in deps:
            unprotected.append((path, methods, deps))

    assert not unprotected, (
        f"Found {len(unprotected)} unprotected routes without require_session: {unprotected}"
    )


def test_mutating_trading_routes_require_csrf_dependency() -> None:
    """Architecture test: verify all mutating routes enforce require_csrf."""
    all_routes = _extract_all_routes(app)

    trading_and_state_prefixes = (
        "/api/v1/orders",
        "/api/v1/paper",
        "/api/v1/watchlists",
        "/api/v1/strategy",
        "/api/v1/options/strategy",
        "/api/v1/investing",
        "/api/v1/ai",
        "/api/v1/feature-builder",
    )

    missing_csrf: list[str] = []
    for path, _methods, deps in all_routes:
        if any(path.startswith(prefix) for prefix in trading_and_state_prefixes):
            if "require_csrf" not in deps:
                missing_csrf.append(path)

    assert not missing_csrf, f"Found mutating routes missing require_csrf: {missing_csrf}"


@pytest.mark.no_auth_override
def test_unauthenticated_request_rejected_with_401() -> None:
    """Unauthenticated client calls must return 401 with WWW-Authenticate header."""
    client = TestClient(app)

    # 1. Read-only protected endpoint
    res = client.get("/api/v1/dhan/token-health")
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers
    assert res.headers["WWW-Authenticate"] == "Bearer"

    # 2. Mutating protected endpoint
    res = client.post("/api/v1/orders/ticket/place", json={})
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers


@pytest.mark.no_auth_override
def test_public_routes_accessible_without_auth() -> None:
    """Liveness and auth negotiation routes must remain accessible without active session."""
    client = TestClient(app)

    # /healthz must return 200
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["process"] == "api"

    # /api/v1/auth/login with invalid password yields 401 from auth logic, not from dependency
    res = client.post("/api/v1/auth/login", json={"password": "InvalidPasswordTest"})
    assert res.status_code == 401
    assert "Invalid master password" in res.json()["detail"]


@pytest.mark.no_auth_override
def test_cookie_mutating_request_rejected_without_csrf_403() -> None:
    """Session cookie caller without valid X-CSRF-Token must be rejected with 403."""
    # Seed a valid session into auth_service
    session_id = "test_csrf_session_id_403_suite"
    csrf_token = "valid_csrf_token_secret_123"
    session = SessionInfo(
        session_id=session_id,
        username="trader",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        csrf_token=csrf_token,
    )
    auth_service._sessions[session_id] = session

    try:
        client = TestClient(app)
        client.cookies.set("shreenexa_session", session_id)

        # GET request succeeds without CSRF header
        res_get = client.get("/api/v1/dhan/token-health")
        assert res_get.status_code == 200

        # POST without X-CSRF-Token fails with 403
        res_post_no_csrf = client.post("/api/v1/orders/ticket/estimate", json={})
        assert res_post_no_csrf.status_code == 403
        assert "CSRF token validation failed" in res_post_no_csrf.json()["detail"]

        # POST with wrong X-CSRF-Token fails with 403
        res_post_wrong_csrf = client.post(
            "/api/v1/orders/ticket/estimate",
            json={},
            headers={"x-csrf-token": "wrong-token-value"},
        )
        assert res_post_wrong_csrf.status_code == 403

        # POST with correct X-CSRF-Token passes auth + CSRF (and reaches validation error 422)
        res_post_valid_csrf = client.post(
            "/api/v1/orders/ticket/estimate",
            json={},
            headers={"x-csrf-token": csrf_token},
        )
        assert res_post_valid_csrf.status_code == 422  # Unprocessable Entity (missing body fields)
    finally:
        auth_service._sessions.pop(session_id, None)


@pytest.mark.no_auth_override
def test_bearer_token_mutating_request_exempt_from_csrf() -> None:
    """API callers using Authorization: Bearer <session_id> are exempt from CSRF double-submit."""
    session_id = "test_bearer_session_id_exempt_suite"
    csrf_token = "csrf_token_not_needed_for_bearer"
    session = SessionInfo(
        session_id=session_id,
        username="trader",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        csrf_token=csrf_token,
    )
    auth_service._sessions[session_id] = session

    try:
        client = TestClient(app)

        # POST with Bearer token passes CSRF check even without x-csrf-token header
        res = client.post(
            "/api/v1/orders/ticket/estimate",
            json={},
            headers={"Authorization": f"Bearer {session_id}"},
        )
        assert res.status_code == 422  # Passed auth and CSRF, reaches FastAPI body validation
    finally:
        auth_service._sessions.pop(session_id, None)
