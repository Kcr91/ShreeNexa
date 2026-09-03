"""Data models and schemas for ShreeNexa authentication (F13.3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Master trader password")


class LoginResponse(BaseModel):
    requires_totp: bool = Field(..., description="True if TOTP code is required to complete login")
    challenge_token: str | None = Field(
        default=None, description="Time-limited challenge token for TOTP step"
    )
    message: str = Field(default="", description="Instructional or status message")


class TOTPVerifyRequest(BaseModel):
    challenge_token: str = Field(
        ..., min_length=1, description="Challenge token issued by login step"
    )
    totp_code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class RecoveryLoginRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Master trader password")
    recovery_code: str = Field(..., min_length=8, description="Single-use emergency recovery code")


class AuthSuccessResponse(BaseModel):
    username: str
    authenticated: bool = True
    csrf_token: str
    expires_at: datetime
    message: str = "Authenticated successfully"


class SessionInfo(BaseModel):
    session_id: str
    username: str
    created_at: datetime
    expires_at: datetime
    csrf_token: str


class AuthAuditRecord(BaseModel):
    timestamp: datetime
    event: str
    ip_address: str
    success: bool
    details: str = ""
