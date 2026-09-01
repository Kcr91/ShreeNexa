"""Dhan token-expiry health assessment and non-secret UI banner models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.config import mask_client_id
from app.dhan.credentials import DhanCredentials

TokenStatus = Literal["valid", "expiring_soon", "expired", "unknown_expiry", "missing", "revoked"]

EXPIRING_SOON_THRESHOLD_SECONDS = 7200  # 2 hours


class DhanTokenHealth(BaseModel):
    """Non-secret token health metadata suitable for public API and UI display."""

    status: TokenStatus
    is_valid: bool
    expires_at: str | None = Field(
        default=None, description="Absolute expiry timestamp in UTC ISO format."
    )
    expires_in_seconds: int | None = Field(
        default=None, description="Seconds remaining before expiration."
    )
    client_id_masked: str = Field(description="Masked Dhan client ID.")
    source: str = Field(
        default="none", description="Credential source: environment, dpapi, or none."
    )


def check_token_health(
    credentials: DhanCredentials | None = None,
    now: datetime | None = None,
    *,
    is_revoked: bool = False,
) -> DhanTokenHealth:
    """Evaluate token health against current time and validity thresholds."""
    current_time = now or datetime.now(tz=UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    else:
        current_time = current_time.astimezone(UTC)

    if is_revoked:
        masked = mask_client_id(credentials.client_id) if credentials else "[NONE]"
        src = credentials.source if credentials else "none"
        exp = (
            credentials.expires_at.isoformat() if (credentials and credentials.expires_at) else None
        )
        return DhanTokenHealth(
            status="revoked",
            is_valid=False,
            expires_at=exp,
            expires_in_seconds=0,
            client_id_masked=masked,
            source=src,
        )

    if credentials is None or not credentials.client_id or not credentials.get_token_value():
        return DhanTokenHealth(
            status="missing",
            is_valid=False,
            expires_at=None,
            expires_in_seconds=None,
            client_id_masked="[NONE]",
            source="none",
        )

    masked_client_id = mask_client_id(credentials.client_id)
    source = credentials.source

    if credentials.expires_at is None:
        return DhanTokenHealth(
            status="unknown_expiry",
            is_valid=True,
            expires_at=None,
            expires_in_seconds=None,
            client_id_masked=masked_client_id,
            source=source,
        )

    target_expiry = credentials.expires_at
    if target_expiry.tzinfo is None:
        target_expiry = target_expiry.replace(tzinfo=UTC)
    else:
        target_expiry = target_expiry.astimezone(UTC)

    diff_seconds = (target_expiry - current_time).total_seconds()

    if diff_seconds <= 0:
        return DhanTokenHealth(
            status="expired",
            is_valid=False,
            expires_at=target_expiry.isoformat(),
            expires_in_seconds=0,
            client_id_masked=masked_client_id,
            source=source,
        )

    remaining = int(diff_seconds)
    if remaining <= EXPIRING_SOON_THRESHOLD_SECONDS:
        return DhanTokenHealth(
            status="expiring_soon",
            is_valid=True,
            expires_at=target_expiry.isoformat(),
            expires_in_seconds=remaining,
            client_id_masked=masked_client_id,
            source=source,
        )

    return DhanTokenHealth(
        status="valid",
        is_valid=True,
        expires_at=target_expiry.isoformat(),
        expires_in_seconds=remaining,
        client_id_masked=masked_client_id,
        source=source,
    )
