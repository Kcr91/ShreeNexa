"""Settings and credential management API (Dhan token updates, password change)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.auth import get_client_ip
from app.api.deps import require_session
from app.auth.crypto import hash_password, verify_password
from app.auth.models import SessionInfo
from app.auth.service import auth_service
from app.config import get_settings
from app.dhan.credentials import (
    resolve_dhan_credentials,
    store_dhan_credentials_dpapi,
    token_client_id_from_claims,
    token_expiry_from_claims,
)
from app.dhan.health import DhanTokenHealth, check_token_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class DhanTokenUpdateRequest(BaseModel):
    access_token: str = Field(..., min_length=10, description="Dhan Web 24h JWT access token")
    client_id: str | None = Field(default=None, description="Optional Dhan client ID")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current master password")
    new_password: str = Field(..., min_length=8, description="New master password (min 8 chars)")
    confirm_password: str = Field(..., min_length=8, description="Confirmation of new password")


class StatusResponse(BaseModel):
    status: str
    message: str


def _update_env_file(updates: dict[str, str], env_path: str = ".env") -> bool:
    """Update .env file key-value pairs while preserving comments and order."""
    path = Path(env_path)
    if not path.is_file():
        try:
            with open(path, "w", encoding="utf-8") as f:
                for k, v in updates.items():
                    f.write(f"{k}={v}\n")
            return True
        except Exception as exc:
            logger.warning("Failed to create .env file: %s", exc)
            return False

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        keys_remaining = set(updates.keys())
        new_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            matched_key = None
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in updates:
                    matched_key = k
                    new_lines.append(f"{k}={updates[k]}\n")
                    keys_remaining.discard(k)
            if matched_key is None:
                new_lines.append(line)

        for k in sorted(keys_remaining):
            new_lines.append(f"{k}={updates[k]}\n")

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception as exc:
        logger.warning("Failed to update .env file: %s", exc)
        return False


@router.get("/dhan-token", response_model=DhanTokenHealth)
def get_token_status() -> DhanTokenHealth:
    """Return non-secret Dhan token health and metadata."""
    creds = resolve_dhan_credentials()
    return check_token_health(creds)


@router.post("/dhan-token", response_model=DhanTokenHealth)
def update_dhan_token(
    req: DhanTokenUpdateRequest,
    session: Annotated[SessionInfo, Depends(require_session)],
) -> DhanTokenHealth:
    """Update Dhan 24h Web access token directly from terminal settings."""
    token = req.access_token.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token cannot be empty",
        )

    expiry = token_expiry_from_claims(token)
    if expiry is not None and expiry <= datetime.now(tz=UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refusing to save: token has already expired at {expiry.isoformat()}",
        )

    # Derive or lookup client_id
    client_id = (req.client_id or "").strip()
    if not client_id:
        derived = token_client_id_from_claims(token)
        if derived:
            client_id = derived
        else:
            existing = resolve_dhan_credentials()
            if existing and existing.client_id:
                client_id = existing.client_id
            else:
                settings = get_settings()
                client_id = settings.dhan_client_id or ""

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client ID could not be derived from token; provide client_id explicitly.",
        )

    # 1. Store securely in Windows DPAPI store
    try:
        store_dhan_credentials_dpapi(
            client_id=client_id,
            access_token=token,
            expires_at=expiry,
        )
    except Exception as exc:
        logger.error("Failed to store credentials via DPAPI: %s", exc)

    # 2. Synchronize with .env file
    _update_env_file({
        "DHAN_ACCESS_TOKEN": token,
        "DHAN_CLIENT_ID": client_id,
    })

    # Check updated token health
    creds = resolve_dhan_credentials()
    health = check_token_health(creds)
    return health


@router.post("/change-password", response_model=StatusResponse)
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    session: Annotated[SessionInfo, Depends(require_session)],
) -> StatusResponse:
    """Change existing master password."""
    ip = get_client_ip(request)
    current_pw = req.current_password
    new_pw = req.new_password
    confirm_pw = req.confirm_password

    # 1. Check confirmation & length
    if new_pw != confirm_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )

    if len(new_pw) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long",
        )

    # 2. Verify current password
    if not verify_password(current_pw, auth_service.password_hash):
        auth_service.record_failed_attempt(
            ip, "PASSWORD_CHANGE_FAILED", "Incorrect current password"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # 3. Hash and store new password
    new_hash = hash_password(new_pw)
    auth_service.password_hash = new_hash

    # 4. Persist to .env
    _update_env_file({
        "SHREENEXA_AUTH_PASSWORD": new_pw,
        "SHREENEXA_AUTH_PASSWORD_HASH": new_hash,
    })

    auth_service.log_audit(
        "PASSWORD_CHANGE_SUCCESS",
        ip,
        success=True,
        details="Password updated via terminal settings",
    )
    return StatusResponse(
        status="success",
        message="Master password updated successfully. Future logins must use the new password.",
    )
