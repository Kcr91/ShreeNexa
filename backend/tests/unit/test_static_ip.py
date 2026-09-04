"""Unit tests for SEBI Static IP egress resolution and fail-closed preflight (QA-09)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.ip import (
    get_current_outbound_ip,
    reset_outbound_ip_cache,
    validate_static_ip_preflight,
)
from app.dhan.transport import MockTransport
from pydantic import SecretStr


@pytest.fixture(autouse=True)
def clean_ip_cache(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    reset_outbound_ip_cache()
    monkeypatch.delenv("SHREENEXA_STATIC_IP_OVERRIDE", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    yield
    reset_outbound_ip_cache()


def test_test_override_honored_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHREENEXA_STATIC_IP_OVERRIDE", "103.21.244.10")
    monkeypatch.setenv("ENVIRONMENT", "development")

    resolved = get_current_outbound_ip()
    assert resolved == "103.21.244.10"


def test_test_override_ignored_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHREENEXA_STATIC_IP_OVERRIDE", "103.21.244.10")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"13.234.56.78\n"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        resolved = get_current_outbound_ip()
        assert resolved == "13.234.56.78"


def test_fail_closed_when_egress_discovery_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        resolved = get_current_outbound_ip()
        assert resolved is None


def test_preflight_blocks_when_ip_undetermined(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "ip/getIP",
        status_code=200,
        body={"primaryIP": "13.234.56.78", "secondaryIP": "103.21.244.10"},
    )
    creds = DhanCredentials(client_id="1000000001", access_token=SecretStr("mock-token"))
    client = DhanRestClient(credentials=creds, transport=mock_transport)

    with patch("urllib.request.urlopen", side_effect=OSError("Network down")):
        ok, msg = validate_static_ip_preflight(client)
        assert ok is False
        assert "Could not determine host outbound public IP address" in msg


def test_preflight_matches_and_mismatches() -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "ip/getIP",
        status_code=200,
        body={"primaryIP": "13.234.56.78", "secondaryIP": "103.21.244.10"},
    )
    creds = DhanCredentials(client_id="1000000001", access_token=SecretStr("mock-token"))
    client = DhanRestClient(credentials=creds, transport=mock_transport)

    # Primary match
    ok_prim, msg_prim = validate_static_ip_preflight(client, current_public_ip="13.234.56.78")
    assert ok_prim is True
    assert "Primary" in msg_prim

    # Secondary match
    ok_sec, msg_sec = validate_static_ip_preflight(client, current_public_ip="103.21.244.10")
    assert ok_sec is True
    assert "Secondary" in msg_sec

    # Mismatch rejects and blocks
    ok_bad, msg_bad = validate_static_ip_preflight(client, current_public_ip="198.51.100.42")
    assert ok_bad is False
    assert "does not match any whitelisted Dhan IP" in msg_bad
    assert "blocked" in msg_bad
