"""Unit tests for Settings API endpoints (Dhan token management and password update)."""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from app.auth.crypto import hash_password
from app.auth.models import SessionInfo
from app.auth.service import auth_service
from app.dhan.credentials import DhanCredentials
from app.main import app
from fastapi.testclient import TestClient
from pydantic import SecretStr


def _make_dummy_jwt(exp_seconds_from_now: int, client_id: str = "1234567890") -> str:
    """Generate a un-signed dummy JWT payload with exp and dhanClientId."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    exp_ts = int(time.time()) + exp_seconds_from_now
    payload = json.dumps({"exp": exp_ts, "dhanClientId": client_id}).encode()
    payload_b64 = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(b"signature").decode().rstrip("=")
    return f"{header}.{payload_b64}.{signature}"


@pytest.fixture
def auth_client() -> tuple[TestClient, dict[str, str]]:
    """Test client with an active authenticated trader session and CSRF token."""
    session_id = "test_settings_session_123"
    csrf_token = "valid_settings_csrf_token_456"
    session = SessionInfo(
        session_id=session_id,
        username="trader",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=2),
        csrf_token=csrf_token,
    )
    auth_service._sessions[session_id] = session

    client = TestClient(app)
    client.cookies.set("shreenexa_session", session_id)
    headers = {"x-csrf-token": csrf_token}
    return client, headers


@pytest.mark.no_auth_override
def test_settings_routes_require_authentication() -> None:
    """All settings endpoints reject unauthenticated callers with 401."""
    client = TestClient(app)
    # GET dhan-token
    res_get = client.get("/api/v1/settings/dhan-token")
    assert res_get.status_code == 401

    # POST dhan-token
    res_post_token = client.post("/api/v1/settings/dhan-token", json={"access_token": "abc"})
    assert res_post_token.status_code == 401

    # POST change-password
    res_post_pw = client.post(
        "/api/v1/settings/change-password",
        json={
            "current_password": "old",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )
    assert res_post_pw.status_code == 401


@pytest.mark.no_auth_override
def test_settings_mutating_routes_require_csrf() -> None:
    """Mutating POST endpoints reject callers without valid CSRF tokens with 403."""
    session_id = "csrf_test_settings_session"
    session = SessionInfo(
        session_id=session_id,
        username="trader",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=2),
        csrf_token="expected_csrf_123",
    )
    auth_service._sessions[session_id] = session

    client = TestClient(app)
    client.cookies.set("shreenexa_session", session_id)

    # POST without CSRF header
    res_token_no_csrf = client.post(
        "/api/v1/settings/dhan-token",
        json={"access_token": "valid_token_xyz"},
    )
    assert res_token_no_csrf.status_code == 403

    res_pw_no_csrf = client.post(
        "/api/v1/settings/change-password",
        json={
            "current_password": "old",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )
    assert res_pw_no_csrf.status_code == 403


def test_get_dhan_token_health(auth_client: tuple[TestClient, dict[str, str]]) -> None:
    """GET /api/v1/settings/dhan-token returns valid health metadata."""
    client, _ = auth_client
    res = client.get("/api/v1/settings/dhan-token")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "is_valid" in data
    assert "client_id_masked" in data


def test_update_dhan_token_expired_fails(
    auth_client: tuple[TestClient, dict[str, str]],
) -> None:
    """POST /api/v1/settings/dhan-token rejects expired tokens with 400."""
    client, headers = auth_client
    expired_jwt = _make_dummy_jwt(exp_seconds_from_now=-3600)
    res = client.post(
        "/api/v1/settings/dhan-token",
        headers=headers,
        json={"access_token": expired_jwt},
    )
    assert res.status_code == 400
    assert "already expired" in res.json()["detail"]


def test_update_dhan_token_success(
    auth_client: tuple[TestClient, dict[str, str]],
) -> None:
    """POST /api/v1/settings/dhan-token stores credentials and returns valid status."""
    client, headers = auth_client
    valid_jwt = _make_dummy_jwt(exp_seconds_from_now=43200, client_id="9998887776")

    mock_resolved_creds = DhanCredentials(
        client_id="9998887776",
        access_token=SecretStr(valid_jwt),
        expires_at=datetime.now(UTC) + timedelta(hours=12),
        source="dpapi",
    )

    with (
        patch("app.api.settings.store_dhan_credentials_dpapi") as mock_dpapi,
        patch("app.api.settings._update_env_file") as mock_env,
        patch("app.api.settings.resolve_dhan_credentials", return_value=mock_resolved_creds),
    ):
        res = client.post(
            "/api/v1/settings/dhan-token",
            headers=headers,
            json={"access_token": valid_jwt, "client_id": "9998887776"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "valid"
        assert data["is_valid"] is True
        assert "999" in data["client_id_masked"]
        mock_dpapi.assert_called_once()
        mock_env.assert_called_once()


def test_change_password_mismatch(
    auth_client: tuple[TestClient, dict[str, str]],
) -> None:
    """POST /api/v1/settings/change-password fails if passwords do not match."""
    client, headers = auth_client
    res = client.post(
        "/api/v1/settings/change-password",
        headers=headers,
        json={
            "current_password": "any",
            "new_password": "NewSecurePassword2026!",
            "confirm_password": "DifferentPassword2026!",
        },
    )
    assert res.status_code == 400
    assert "do not match" in res.json()["detail"]


def test_change_password_wrong_current(
    auth_client: tuple[TestClient, dict[str, str]],
) -> None:
    """POST /api/v1/settings/change-password fails if current password is incorrect."""
    client, headers = auth_client
    res = client.post(
        "/api/v1/settings/change-password",
        headers=headers,
        json={
            "current_password": "DefinitelyIncorrectPassword!",
            "new_password": "NewSecurePassword2026!",
            "confirm_password": "NewSecurePassword2026!",
        },
    )
    assert res.status_code == 400
    assert "Incorrect current password" in res.json()["detail"]


def test_change_password_success_cycle(
    auth_client: tuple[TestClient, dict[str, str]],
) -> None:
    """POST /api/v1/settings/change-password updates password and verifies new auth."""
    client, headers = auth_client
    original_hash = auth_service.password_hash
    test_current = "ShreeNexa2026!SecureTerminal"
    test_new = "NewUpdatedMasterPassword2026!"

    # Set known hash for test
    auth_service.password_hash = hash_password(test_current)

    with patch("app.api.settings._update_env_file") as mock_env:
        res = client.post(
            "/api/v1/settings/change-password",
            headers=headers,
            json={
                "current_password": test_current,
                "new_password": test_new,
                "confirm_password": test_new,
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        mock_env.assert_called_once()

    # Restore original hash
    auth_service.password_hash = original_hash
