"""Dhan credential resolution and local DPAPI persistence management."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.config import Settings, get_settings, mask_client_id
from app.dhan.dpapi import (
    DPAPIAdapter,
    DPAPIError,
    get_dpapi_adapter,
    read_encrypted_file,
    save_encrypted_file,
)

CREDENTIALS_FILENAME = "dhan.enc"


def parse_iso_datetime(value: str | datetime | None) -> datetime | None:
    """Parse an ISO 8601 string or datetime into UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    clean = value.strip()
    if not clean:
        return None
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def decode_token_claims(token: str) -> dict[str, Any] | None:
    """Decode the unverified payload of a Dhan JWT access token.

    The signature is NOT verified: Dhan signs tokens with a server-side secret we
    do not hold. This reads self-reported metadata (``exp``, ``dhanClientId``)
    purely to drive local expiry banners, never to authorise anything.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload)
        claims = json.loads(raw.decode("utf-8"))
    except binascii.Error, ValueError, UnicodeDecodeError:
        return None
    if not isinstance(claims, dict):
        return None
    return claims


def token_expiry_from_claims(token: str) -> datetime | None:
    """Return the UTC expiry encoded in a Dhan token's own ``exp`` claim."""
    claims = decode_token_claims(token)
    if claims is None:
        return None
    exp = claims.get("exp")
    if not isinstance(exp, int | float) or isinstance(exp, bool):
        return None
    try:
        return datetime.fromtimestamp(float(exp), tz=UTC)
    except OverflowError, OSError, ValueError:
        return None


def token_client_id_from_claims(token: str) -> str | None:
    """Return the Dhan client ID encoded in a token's own claims, if present."""
    claims = decode_token_claims(token)
    if claims is None:
        return None
    client_id = claims.get("dhanClientId")
    if isinstance(client_id, str) and client_id.strip():
        return client_id.strip()
    return None


class DhanCredentials(BaseModel):
    """Resolved Dhan credential set."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client_id: str
    access_token: SecretStr
    expires_at: datetime | None = None
    source: str = Field(default="environment")  # "environment", "dpapi", "manual"

    def get_token_value(self) -> str:
        """Return the raw secret token value."""
        return self.access_token.get_secret_value()

    def __repr__(self) -> str:
        expires = self.expires_at.isoformat() if self.expires_at else None
        return (
            f"DhanCredentials(client_id={mask_client_id(self.client_id)!r}, "
            f"access_token=SecretStr('**********'), "
            f"expires_at={expires!r}, source={self.source!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


def get_credentials_path(runtime_root: Path | None = None) -> Path:
    """Return the canonical path to the encrypted credentials file."""
    root = runtime_root or Path(".runtime")
    return root / "credentials" / CREDENTIALS_FILENAME


def resolve_dhan_credentials(
    settings: Settings | None = None,
    runtime_root: Path | None = None,
    dpapi_adapter: DPAPIAdapter | None = None,
) -> DhanCredentials | None:
    """Resolve Dhan credentials with precedence: Environment > DPAPI storage > None."""
    cfg = settings or get_settings()

    # 1. Environment / .env resolution (production standard)
    if cfg.dhan_access_token and cfg.dhan_client_id:
        token_str = cfg.dhan_access_token.get_secret_value().strip()
        client_id_str = cfg.dhan_client_id.strip()
        if token_str and client_id_str:
            expires_at = parse_iso_datetime(cfg.dhan_token_expires_at) or token_expiry_from_claims(
                token_str
            )
            return DhanCredentials(
                client_id=client_id_str,
                access_token=SecretStr(token_str),
                expires_at=expires_at,
                source="environment",
            )

    # 2. Local DPAPI encrypted storage resolution (local Windows development)
    root = runtime_root or cfg.runtime_root
    enc_path = get_credentials_path(root)
    if enc_path.is_file():
        try:
            adapter = dpapi_adapter or get_dpapi_adapter()
            encrypted_bytes = read_encrypted_file(enc_path)
            decrypted_bytes = adapter.unprotect(encrypted_bytes)
            data: dict[str, Any] = json.loads(decrypted_bytes.decode("utf-8"))
            client_id = data.get("client_id")
            access_token = data.get("access_token")
            if client_id and access_token:
                token_value = str(access_token).strip()
                expires_at = parse_iso_datetime(data.get("expires_at")) or token_expiry_from_claims(
                    token_value
                )
                return DhanCredentials(
                    client_id=str(client_id).strip(),
                    access_token=SecretStr(token_value),
                    expires_at=expires_at,
                    source="dpapi",
                )
        except DPAPIError, json.JSONDecodeError, UnicodeDecodeError, OSError:
            # Fail closed if encrypted file cannot be read/decrypted
            return None

    return None


def store_dhan_credentials_dpapi(
    client_id: str,
    access_token: str,
    expires_at: datetime | str | None = None,
    runtime_root: Path | None = None,
    dpapi_adapter: DPAPIAdapter | None = None,
) -> Path:
    """Store Dhan credentials securely using Windows DPAPI encryption."""
    client_id_clean = client_id.strip()
    token_clean = access_token.strip()
    if not client_id_clean or not token_clean:
        raise ValueError("client_id and access_token must not be empty")

    parsed_expires = parse_iso_datetime(expires_at) or token_expiry_from_claims(token_clean)
    payload: dict[str, Any] = {
        "client_id": client_id_clean,
        "access_token": token_clean,
        "expires_at": parsed_expires.isoformat() if parsed_expires else None,
    }
    raw_bytes = json.dumps(payload).encode("utf-8")

    adapter = dpapi_adapter or get_dpapi_adapter()
    encrypted_bytes = adapter.protect(raw_bytes, description="ShreeNexa Dhan Credentials")

    target_path = get_credentials_path(runtime_root)
    save_encrypted_file(target_path, encrypted_bytes)
    return target_path


def clear_dhan_credentials_dpapi(runtime_root: Path | None = None) -> bool:
    """Delete the encrypted credentials file if it exists."""
    path = get_credentials_path(runtime_root)
    if path.is_file():
        path.unlink()
        return True
    return False
