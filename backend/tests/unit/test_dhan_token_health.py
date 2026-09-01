"""Unit tests for Dhan token expiry health and API endpoint."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.config import get_settings
from app.dhan.credentials import DhanCredentials, parse_iso_datetime
from app.dhan.health import check_token_health
from app.main import app, get_dhan_token_health
from pydantic import SecretStr


def test_parse_iso_datetime_timezones() -> None:
    # IST string
    ist_str = "2026-09-02T15:30:00+05:30"
    dt = parse_iso_datetime(ist_str)
    assert dt is not None
    assert dt.tzinfo == UTC
    assert dt.hour == 10  # 15:30 IST is 10:00 UTC
    assert dt.minute == 0

    # UTC string
    utc_str = "2026-09-02T10:00:00Z"
    dt_utc = parse_iso_datetime(utc_str.replace("Z", "+00:00"))
    assert dt_utc == dt


def test_token_health_missing() -> None:
    health = check_token_health(None)
    assert health.status == "missing"
    assert health.is_valid is False
    assert health.client_id_masked == "[NONE]"
    assert health.expires_at is None
    assert health.expires_in_seconds is None


def test_token_health_unknown_expiry() -> None:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("token_xyz"),
        expires_at=None,
        source="environment",
    )
    health = check_token_health(creds)
    assert health.status == "unknown_expiry"
    assert health.is_valid is True
    assert health.client_id_masked == "0000***000"
    assert health.expires_at is None
    assert health.expires_in_seconds is None
    assert health.source == "environment"


def test_token_health_valid() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    # 24-hour Dhan Web token validity test (e.g. expires 10 hours from now)
    expires = now + timedelta(hours=10)
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("token_xyz"),
        expires_at=expires,
        source="dpapi",
    )
    health = check_token_health(creds, now=now)
    assert health.status == "valid"
    assert health.is_valid is True
    assert health.expires_in_seconds == 36000
    assert health.expires_at == expires.isoformat()
    assert health.source == "dpapi"


def test_token_health_expiring_soon() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    # Expiring in 90 minutes (<= 2 hours threshold)
    expires = now + timedelta(minutes=90)
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("token_xyz"),
        expires_at=expires,
        source="environment",
    )
    health = check_token_health(creds, now=now)
    assert health.status == "expiring_soon"
    assert health.is_valid is True
    assert health.expires_in_seconds == 5400
    assert health.expires_at == expires.isoformat()


def test_token_health_expired() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    # Expired 5 minutes ago
    expires = now - timedelta(minutes=5)
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("token_xyz"),
        expires_at=expires,
        source="environment",
    )
    health = check_token_health(creds, now=now)
    assert health.status == "expired"
    assert health.is_valid is False
    assert health.expires_in_seconds == 0
    assert health.expires_at == expires.isoformat()


def test_token_health_revoked() -> None:
    creds = DhanCredentials(
        client_id="0000000000",
        access_token=SecretStr("token_xyz"),
        expires_at=datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC),
        source="environment",
    )
    health = check_token_health(creds, is_revoked=True)
    assert health.status == "revoked"
    assert health.is_valid is False
    assert health.expires_in_seconds == 0


@pytest.mark.anyio
async def test_dhan_token_health_api_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHAN_CLIENT_ID", "1100223344")
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "SUPER_SECRET_TOKEN_DO_NOT_EXPOSE")
    monkeypatch.setenv("DHAN_TOKEN_EXPIRES_AT", "2026-09-02T12:00:00+00:00")
    get_settings.cache_clear()

    # Direct function test
    result = get_dhan_token_health()
    dumped = result.model_dump()
    assert dumped["status"] in {"valid", "expiring_soon", "expired"}
    assert dumped["client_id_masked"] == "1100***344"
    assert dumped["source"] == "environment"

    # ASGI invocation test through FastAPI routing
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/dhan/token-health",
        "raw_path": b"/api/v1/dhan/token-health",
        "headers": [],
        "query_string": b"",
    }
    response_body: list[bytes] = []
    status_code = 0

    async def receive() -> MutableMapping[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        nonlocal status_code
        if message.get("type") == "http.response.start":
            raw_status = message.get("status", 0)
            if isinstance(raw_status, int):
                status_code = raw_status
        elif message.get("type") == "http.response.body":
            body = message.get("body", b"")
            if isinstance(body, bytes):
                response_body.append(body)

    await app(scope, receive, send)

    assert status_code == 200
    raw_response_text = b"".join(response_body).decode("utf-8")
    data = json.loads(raw_response_text)

    assert "status" in data
    assert "is_valid" in data
    assert "expires_at" in data
    assert "expires_in_seconds" in data
    assert "client_id_masked" in data
    assert data["client_id_masked"] == "1100***344"
    assert data["source"] == "environment"

    # Strict assertion: NO secret token value in payload
    assert "SUPER_SECRET_TOKEN_DO_NOT_EXPOSE" not in raw_response_text
    assert "access_token" not in data
