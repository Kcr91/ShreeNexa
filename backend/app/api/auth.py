"""FastAPI Router for Single-User Password + TOTP Authentication (F13.3)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response, status

from app.auth.models import (
    AuthAuditRecord,
    AuthSuccessResponse,
    LoginRequest,
    LoginResponse,
    RecoveryLoginRequest,
    SessionInfo,
    TOTPVerifyRequest,
)
from app.auth.service import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

COOKIE_NAME = "shreenexa_session"
IS_PRODUCTION = os.environ.get("APP_ENV") == "production"


def get_client_ip(request: Request) -> str:
    """Extract client IP, preferring X-Forwarded-For if behind reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request) -> LoginResponse:
    """Step 1 of 2FA: Verify master password and return TOTP challenge token."""
    ip = get_client_ip(request)
    success, challenge_token, message = auth_service.initiate_login(req.password, ip)
    if not success:
        locked, retry_after = auth_service.is_locked_out(ip)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    return LoginResponse(
        requires_totp=True,
        challenge_token=challenge_token,
        message=message,
    )


@router.post("/totp/verify", response_model=AuthSuccessResponse)
def verify_totp(
    req: TOTPVerifyRequest,
    request: Request,
    response: Response,
    shreenexa_session: str | None = Cookie(default=None),
) -> AuthSuccessResponse:
    """Step 2 of 2FA: Verify 6-digit TOTP code and issue secure session cookie."""
    ip = get_client_ip(request)
    success, session, message = auth_service.verify_totp_challenge(
        challenge_token=req.challenge_token,
        totp_code=req.totp_code,
        ip_address=ip,
        old_session_id=shreenexa_session,
    )
    if not success or session is None:
        locked, retry_after = auth_service.is_locked_out(ip)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    # Set hardened session cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=session.session_id,
        httponly=True,
        samesite="strict",
        secure=IS_PRODUCTION,
        path="/",
        max_age=86400,
    )

    return AuthSuccessResponse(
        username=session.username,
        authenticated=True,
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
        message=message,
    )


@router.post("/recovery", response_model=AuthSuccessResponse)
def recovery_login(
    req: RecoveryLoginRequest,
    request: Request,
    response: Response,
    shreenexa_session: str | None = Cookie(default=None),
) -> AuthSuccessResponse:
    """Emergency single-use recovery code login when TOTP device is unavailable."""
    ip = get_client_ip(request)
    success, session, message = auth_service.login_with_recovery_code(
        password=req.password,
        recovery_code=req.recovery_code,
        ip_address=ip,
        old_session_id=shreenexa_session,
    )
    if not success or session is None:
        locked, retry_after = auth_service.is_locked_out(ip)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    response.set_cookie(
        key=COOKIE_NAME,
        value=session.session_id,
        httponly=True,
        samesite="strict",
        secure=IS_PRODUCTION,
        path="/",
        max_age=86400,
    )

    return AuthSuccessResponse(
        username=session.username,
        authenticated=True,
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
        message=message,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    shreenexa_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    """Destroy active trader session and clear cookie."""
    ip = get_client_ip(request)
    if shreenexa_session:
        auth_service.revoke_session(shreenexa_session)
        auth_service.log_audit("LOGOUT", ip, success=True, details="Session revoked cleanly")

    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "logged_out", "message": "Session terminated cleanly"}


@router.get("/me")
def get_current_user(
    shreenexa_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Inspect active session status."""
    token = shreenexa_session
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")

    session = auth_service.validate_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return {
        "username": session.username,
        "authenticated": True,
        "csrf_token": session.csrf_token,
        "expires_at": session.expires_at.isoformat(),
    }


@router.get("/audit", response_model=list[AuthAuditRecord])
def get_audit_log(
    shreenexa_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> list[AuthAuditRecord]:
    """Retrieve security audit records (requires authenticated session)."""
    token = shreenexa_session
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token or auth_service.validate_session(token) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")

    return auth_service.get_audit_records(limit=50)


def verify_csrf_token(
    request: Request,
    session: SessionInfo,
    x_csrf_token: str | None = Header(default=None),
) -> None:
    """Enforce CSRF protection on mutating HTTP methods."""
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        if not x_csrf_token or x_csrf_token != session.csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed",
            )
