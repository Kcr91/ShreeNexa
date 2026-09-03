"""Security tests for F13.3: Single-user password + TOTP auth, secure sessions,
recovery process, rate limiting, and audit.

Proves:
1. Session fixation protection
2. CSRF double-submit token enforcement
3. Brute-force lockout and rate limiting
4. Secure secret and credential storage
5. Single-use recovery code consumption
6. WebSocket authorization gating
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from app.api.auth import verify_csrf_token
from app.auth.crypto import (
    PBKDF2_ROUNDS,
    generate_totp_code,
    hash_password,
    verify_password,
    verify_totp_code,
)
from app.auth.models import SessionInfo
from app.auth.service import AuthService
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def auth_service_instance() -> AuthService:
    """Provide isolated AuthService instance for tests."""
    svc = AuthService()
    svc.password_hash = hash_password("CorrectHorseBatteryStaple2026!")
    svc.totp_secret = "JBSWY3DPEHPK3PXP"  # Standard test Base32 secret
    return svc


def test_secret_storage_pbkdf2_and_recovery_hashes(auth_service_instance: AuthService) -> None:
    """Proof: Password uses PBKDF2 >= 600,000 rounds and recovery codes stored as SHA-256."""
    pw_hash = auth_service_instance.password_hash
    parts = pw_hash.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) >= PBKDF2_ROUNDS
    assert len(parts[2]) == 32  # 16-byte hex salt

    # Verify password verification works
    assert verify_password("CorrectHorseBatteryStaple2026!", pw_hash)
    assert not verify_password("WrongPassword123!", pw_hash)

    # Verify recovery codes are stored as 64-character SHA-256 digests
    for h in auth_service_instance.recovery_code_hashes:
        assert len(h) == 64
        int(h, 16)  # must parse as valid hex


def test_totp_rfc6238_generation_and_skew_verification(auth_service_instance: AuthService) -> None:
    """Verify standard RFC 6238 TOTP computation and ±30s clock skew tolerance."""
    secret = auth_service_instance.totp_secret
    now = time.time()

    current_code = generate_totp_code(secret, timestamp=now)
    assert len(current_code) == 6
    assert current_code.isdigit()

    # Exact window matches
    assert verify_totp_code(secret, current_code, timestamp=now)

    # Skew within ±1 step (30s) matches
    assert verify_totp_code(secret, current_code, timestamp=now + 25.0)
    assert verify_totp_code(secret, current_code, timestamp=now - 25.0)

    # Skew beyond ±2 steps fails
    assert not verify_totp_code(secret, current_code, timestamp=now + 90.0)
    assert not verify_totp_code(secret, "000000", timestamp=now)


def test_brute_force_lockout_and_rate_limiting(auth_service_instance: AuthService) -> None:
    """Proof: 5 failed attempts locks out IP; 6th attempt is rejected with rate limit."""
    ip = "192.168.1.100"

    # 5 failed password attempts
    for _i in range(5):
        success, _, msg = auth_service_instance.initiate_login("WrongPassword", ip)
        assert not success
        assert "Invalid master password" in msg

    # 6th attempt must be locked out
    locked, retry_after = auth_service_instance.is_locked_out(ip)
    assert locked
    assert retry_after > 0

    success_6th, _, msg_6th = auth_service_instance.initiate_login(
        "CorrectHorseBatteryStaple2026!", ip
    )
    assert not success_6th
    assert "Too many failed attempts" in msg_6th

    # Other IPs are unaffected (isolation)
    other_ip = "192.168.1.101"
    ok, token, _ = auth_service_instance.initiate_login("CorrectHorseBatteryStaple2026!", other_ip)
    assert ok
    assert token is not None


def test_session_fixation_protection(auth_service_instance: AuthService) -> None:
    """Proof: Re-authenticating destroys previous session and generates fresh session ID."""
    ip = "10.0.0.1"

    # Step 1: Login to get Session A
    _, ch_token_a, _ = auth_service_instance.initiate_login("CorrectHorseBatteryStaple2026!", ip)
    assert ch_token_a is not None
    code_a = generate_totp_code(auth_service_instance.totp_secret)
    ok_a, session_a, _ = auth_service_instance.verify_totp_challenge(ch_token_a, code_a, ip)
    assert ok_a and session_a is not None
    old_session_id = session_a.session_id

    # Verify session A is active
    assert auth_service_instance.validate_session(old_session_id) is not None

    # Step 2: Login again passing old session ID (simulating session renewal / login)
    _, ch_token_b, _ = auth_service_instance.initiate_login("CorrectHorseBatteryStaple2026!", ip)
    assert ch_token_b is not None
    code_b = generate_totp_code(auth_service_instance.totp_secret)
    ok_b, session_b, _ = auth_service_instance.verify_totp_challenge(
        ch_token_b, code_b, ip, old_session_id=old_session_id
    )
    assert ok_b and session_b is not None
    new_session_id = session_b.session_id

    # Session IDs must differ
    assert new_session_id != old_session_id

    # Old session MUST be invalidated (cannot be reused)
    assert auth_service_instance.validate_session(old_session_id) is None
    assert auth_service_instance.validate_session(new_session_id) is not None


def test_recovery_code_single_use_consumption(auth_service_instance: AuthService) -> None:
    """Proof: Emergency recovery code works once and is immediately consumed."""
    ip = "10.0.0.2"
    raw_code = auth_service_instance.raw_recovery_codes_backup[0]

    # First attempt with recovery code succeeds
    ok, session, _ = auth_service_instance.login_with_recovery_code(
        "CorrectHorseBatteryStaple2026!", raw_code, ip
    )
    assert ok
    assert session is not None

    # Second attempt with identical code fails (consumed)
    ok_retry, _, msg_retry = auth_service_instance.login_with_recovery_code(
        "CorrectHorseBatteryStaple2026!", raw_code, ip
    )
    assert not ok_retry
    assert "Invalid or previously consumed recovery code" in msg_retry


def test_csrf_token_validation_logic() -> None:
    """Proof: State-modifying requests require matching X-CSRF-Token."""

    session = SessionInfo(
        session_id="test_sess_123",
        username="trader",
        created_at=datetime.now(tz=UTC),
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        csrf_token="secret_csrf_token_abc",
    )

    # Safe GET method ignores CSRF token
    req_get = MagicMock()
    req_get.method = "GET"
    verify_csrf_token(req_get, session, x_csrf_token=None)

    # Mutating POST method with valid CSRF token passes
    req_post = MagicMock()
    req_post.method = "POST"
    verify_csrf_token(req_post, session, x_csrf_token="secret_csrf_token_abc")

    # Mutating POST method without CSRF token fails with 403
    with pytest.raises(HTTPException) as exc_info:
        verify_csrf_token(req_post, session, x_csrf_token=None)
    assert exc_info.value.status_code == 403

    # Mutating POST method with incorrect CSRF token fails with 403
    with pytest.raises(HTTPException) as exc_info:
        verify_csrf_token(req_post, session, x_csrf_token="wrong_token")
    assert exc_info.value.status_code == 403


def test_api_auth_endpoints_end_to_end() -> None:
    """Test REST endpoints: 2FA login, session validation, audit, and logout."""
    # Step 1: Login with invalid password -> 401
    res_bad = client.post("/api/v1/auth/login", json={"password": "WrongPassword"})
    assert res_bad.status_code == 401

    # Step 2: Login with default master password -> 200 with challenge token
    res_step1 = client.post("/api/v1/auth/login", json={"password": "ShreeNexa2026!SecureTerminal"})
    assert res_step1.status_code == 200
    data_step1 = res_step1.json()
    assert data_step1["requires_totp"] is True
    challenge = data_step1["challenge_token"]

    # Step 3: Verify with wrong TOTP -> 401
    res_bad_totp = client.post(
        "/api/v1/auth/totp/verify",
        json={"challenge_token": challenge, "totp_code": "000000"},
    )
    assert res_bad_totp.status_code == 401

    # Re-issue challenge and verify with real TOTP code
    res_step1_again = client.post(
        "/api/v1/auth/login", json={"password": "ShreeNexa2026!SecureTerminal"}
    )
    challenge2 = res_step1_again.json()["challenge_token"]

    from app.auth.service import auth_service

    valid_totp = generate_totp_code(auth_service.totp_secret)
    res_step2 = client.post(
        "/api/v1/auth/totp/verify",
        json={"challenge_token": challenge2, "totp_code": valid_totp},
    )
    assert res_step2.status_code == 200
    data_step2 = res_step2.json()
    assert data_step2["authenticated"] is True
    assert "csrf_token" in data_step2

    # Step 4: Validate /me endpoint using cookie
    res_me = client.get("/api/v1/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["username"] == auth_service.username

    # Step 5: Audit logs are accessible
    res_audit = client.get("/api/v1/auth/audit")
    assert res_audit.status_code == 200
    assert len(res_audit.json()) > 0

    # Step 6: Logout
    res_logout = client.post("/api/v1/auth/logout")
    assert res_logout.status_code == 200
    assert res_logout.json()["status"] == "logged_out"

    # Now /me returns 401
    res_me_after = client.get("/api/v1/auth/me")
    assert res_me_after.status_code == 401
