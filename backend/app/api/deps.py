"""FastAPI dependencies for session authentication and CSRF validation (QA-02 / F13.3)."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from app.auth.models import SessionInfo
from app.auth.service import auth_service

COOKIE_NAME = "shreenexa_session"


async def get_current_session(
    request: Request,
    shreenexa_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> SessionInfo:
    """Extract and validate active session from session cookie or Authorization header."""
    token = shreenexa_session
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing session cookie or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = auth_service.validate_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.session = session
    return session


async def require_session(
    session: Annotated[SessionInfo, Depends(get_current_session)],
) -> SessionInfo:
    """Dependency enforcing that an active, non-expired session is present."""
    return session


async def require_csrf(
    request: Request,
    session: Annotated[SessionInfo, Depends(get_current_session)],
    x_csrf_token: str | None = Header(default=None, alias="x-csrf-token"),
) -> None:
    """Dependency enforcing CSRF double-submit token on mutating HTTP methods."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Programmatic Bearer token callers outside browser cookies are immune to browser CSRF
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    if not x_csrf_token or not secrets.compare_digest(x_csrf_token, session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed.",
        )
