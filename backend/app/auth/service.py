"""Authentication service managing single-user login, sessions, TOTP, and audit (F13.3)."""

from __future__ import annotations

import os
import secrets
import time
from collections import deque
from datetime import UTC, datetime, timedelta

from app.auth.crypto import (
    generate_recovery_codes,
    generate_totp_secret,
    hash_password,
    hash_recovery_code,
    verify_password,
    verify_totp_code,
)
from app.auth.models import AuthAuditRecord, SessionInfo

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900.0  # 15 minutes
CHALLENGE_EXPIRY_SECONDS = 300.0  # 5 minutes
SESSION_DURATION_HOURS = 24


class AuthService:
    """Manages single-user authentication state, sessions, rate limits, and audit logs."""

    def __init__(self) -> None:
        self.username: str = os.environ.get("SHREENEXA_AUTH_USERNAME", "trader")

        # Initial master credentials
        env_password = os.environ.get("SHREENEXA_AUTH_PASSWORD", "ShreeNexa2026!SecureTerminal")
        env_hash = os.environ.get("SHREENEXA_AUTH_PASSWORD_HASH")
        self.password_hash: str = env_hash if env_hash else hash_password(env_password)

        self.totp_secret: str = (
            os.environ.get("SHREENEXA_AUTH_TOTP_SECRET") or generate_totp_secret()
        )

        # Generate default recovery codes if not specified
        raw_recovery_codes = generate_recovery_codes(8)
        self.recovery_code_hashes: set[str] = {hash_recovery_code(c) for c in raw_recovery_codes}
        self.raw_recovery_codes_backup: list[str] = raw_recovery_codes

        # Brute force tracking: ip -> list of failed timestamp floats
        self._failed_attempts: dict[str, list[float]] = {}

        # Challenges for 2FA step: challenge_token -> (created_at_epoch, username)
        self._challenges: dict[str, tuple[float, str]] = {}

        # Active sessions: session_id -> SessionInfo
        self._sessions: dict[str, SessionInfo] = {}

        # In-memory audit log ring buffer (last 1000 events)
        self._audit_log: deque[AuthAuditRecord] = deque(maxlen=1000)

    # --------------------------------------------------------------------------
    # Rate Limiting & Brute Force Prevention
    # --------------------------------------------------------------------------
    def is_locked_out(self, ip_address: str) -> tuple[bool, int]:
        """Check if an IP address is currently locked out due to excessive failed attempts."""
        now = time.time()
        attempts = [
            t for t in self._failed_attempts.get(ip_address, [])
            if now - t < LOCKOUT_WINDOW_SECONDS
        ]
        self._failed_attempts[ip_address] = attempts

        if len(attempts) >= MAX_FAILED_ATTEMPTS:
            earliest = attempts[0]
            remaining = int(LOCKOUT_WINDOW_SECONDS - (now - earliest))
            return True, max(1, remaining)
        return False, 0

    def record_failed_attempt(self, ip_address: str, event_type: str, details: str = "") -> None:
        """Register a failed login or TOTP verification attempt."""
        now = time.time()
        attempts = self._failed_attempts.setdefault(ip_address, [])
        attempts.append(now)
        self.log_audit(event_type, ip_address, success=False, details=details)

    def reset_rate_limit(self, ip_address: str) -> None:
        """Reset rate limit counter upon successful authentication."""
        self._failed_attempts.pop(ip_address, None)

    # --------------------------------------------------------------------------
    # Audit Logging
    # --------------------------------------------------------------------------
    def log_audit(self, event: str, ip_address: str, success: bool, details: str = "") -> None:
        """Log an immutable audit record without leaking secrets."""
        record = AuthAuditRecord(
            timestamp=datetime.now(tz=UTC),
            event=event,
            ip_address=ip_address,
            success=success,
            details=details,
        )
        self._audit_log.append(record)

    def get_audit_records(self, limit: int = 50) -> list[AuthAuditRecord]:
        """Retrieve recent audit logs in reverse chronological order."""
        return list(reversed(self._audit_log))[:limit]

    # --------------------------------------------------------------------------
    # Login & TOTP Challenge Lifecycle
    # --------------------------------------------------------------------------
    def initiate_login(self, password: str, ip_address: str) -> tuple[bool, str | None, str]:
        """Step 1: Verify master password and issue TOTP challenge."""
        locked, retry_after = self.is_locked_out(ip_address)
        if locked:
            self.log_audit(
                "RATE_LIMITED",
                ip_address,
                success=False,
                details=f"Locked out ({retry_after}s remaining)",
            )
            return False, None, f"Too many failed attempts. Try again in {retry_after} seconds."

        if not verify_password(password, self.password_hash):
            self.record_failed_attempt(ip_address, "LOGIN_FAILED", "Invalid master password")
            return False, None, "Invalid master password"

        # Password verified! Issue short-lived challenge token for Step 2 (TOTP)
        challenge_token = secrets.token_urlsafe(32)
        self._challenges[challenge_token] = (time.time(), self.username)
        self.log_audit(
            "PASSWORD_VERIFIED", ip_address, success=True, details="TOTP challenge issued"
        )
        return True, challenge_token, "Password verified. Please submit 6-digit TOTP code."

    def verify_totp_challenge(
        self,
        challenge_token: str,
        totp_code: str,
        ip_address: str,
        old_session_id: str | None = None,
    ) -> tuple[bool, SessionInfo | None, str]:
        """Step 2: Verify TOTP code and issue secure session (with session fixation protection)."""
        locked, retry_after = self.is_locked_out(ip_address)
        if locked:
            self.log_audit(
                "RATE_LIMITED",
                ip_address,
                success=False,
                details=f"Locked out ({retry_after}s remaining)",
            )
            return False, None, f"Too many failed attempts. Try again in {retry_after} seconds."

        challenge = self._challenges.pop(challenge_token, None)
        if challenge is None:
            self.record_failed_attempt(
                ip_address, "TOTP_VERIFY_FAILED", "Expired or invalid challenge token"
            )
            return False, None, "Invalid or expired challenge token"

        created_at, username = challenge
        if time.time() - created_at > CHALLENGE_EXPIRY_SECONDS:
            self.record_failed_attempt(ip_address, "TOTP_VERIFY_FAILED", "Challenge expired")
            return False, None, "Challenge expired"

        if not verify_totp_code(self.totp_secret, totp_code):
            self.record_failed_attempt(ip_address, "TOTP_VERIFY_FAILED", "Invalid TOTP code")
            return False, None, "Invalid TOTP code"

        # Successful 2FA verification! Reset rate limit and generate new session
        self.reset_rate_limit(ip_address)
        session = self._create_session(username, old_session_id=old_session_id)
        self.log_audit(
            "LOGIN_SUCCESS",
            ip_address,
            success=True,
            details="Full 2FA authentication complete",
        )
        return True, session, "Authentication successful"

    def login_with_recovery_code(
        self,
        password: str,
        recovery_code: str,
        ip_address: str,
        old_session_id: str | None = None,
    ) -> tuple[bool, SessionInfo | None, str]:
        """Emergency login using master password and single-use recovery code."""
        locked, retry_after = self.is_locked_out(ip_address)
        if locked:
            return False, None, f"Too many failed attempts. Try again in {retry_after} seconds."

        if not verify_password(password, self.password_hash):
            self.record_failed_attempt(ip_address, "RECOVERY_FAILED", "Invalid password")
            return False, None, "Invalid master password"

        hashed_code = hash_recovery_code(recovery_code)
        if hashed_code not in self.recovery_code_hashes:
            self.record_failed_attempt(
                ip_address, "RECOVERY_FAILED", "Invalid or already consumed recovery code"
            )
            return False, None, "Invalid or previously consumed recovery code"

        # Consume the recovery code so it can NEVER be reused
        self.recovery_code_hashes.remove(hashed_code)
        self.reset_rate_limit(ip_address)

        session = self._create_session(self.username, old_session_id=old_session_id)
        self.log_audit(
            "RECOVERY_SUCCESS",
            ip_address,
            success=True,
            details="Emergency recovery code consumed",
        )
        msg = "Recovery authentication successful. Please reconfigure your TOTP device."
        return True, session, msg

    # --------------------------------------------------------------------------
    # Session Management & Fixation Protection
    # --------------------------------------------------------------------------
    def _create_session(self, username: str, old_session_id: str | None = None) -> SessionInfo:
        """Create a new session, destroying old session if present (session fixation protection)."""
        if old_session_id:
            self.revoke_session(old_session_id)

        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = datetime.now(tz=UTC)
        expires_at = now + timedelta(hours=SESSION_DURATION_HOURS)

        session = SessionInfo(
            session_id=session_id,
            username=username,
            created_at=now,
            expires_at=expires_at,
            csrf_token=csrf_token,
        )
        self._sessions[session_id] = session
        return session

    def validate_session(self, session_id: str) -> SessionInfo | None:
        """Validate active session and check expiration."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if datetime.now(tz=UTC) > session.expires_at:
            self.revoke_session(session_id)
            return None
        return session

    def revoke_session(self, session_id: str) -> bool:
        """Destroy an active session (logout)."""
        return bool(self._sessions.pop(session_id, None))


# Global singleton instance
auth_service = AuthService()
