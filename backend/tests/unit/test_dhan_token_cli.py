"""Unit tests for Dhan token claim decoding and the local credential CLI."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from app.dhan import token as token_cli
from app.dhan.credentials import (
    decode_token_claims,
    resolve_dhan_credentials,
    store_dhan_credentials_dpapi,
    token_client_id_from_claims,
    token_expiry_from_claims,
)
from app.dhan.dpapi import FakeDPAPI


def make_token(claims: dict[str, Any]) -> str:
    def seg(obj: dict[str, Any]) -> str:
        raw = json.dumps(obj).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{seg({'typ': 'JWT', 'alg': 'HS512'})}.{seg(claims)}.c2lnbmF0dXJl"


def test_decode_token_claims_reads_payload() -> None:
    token = make_token({"exp": 1788445858, "dhanClientId": "1111713478"})
    claims = decode_token_claims(token)
    assert claims is not None
    assert claims["dhanClientId"] == "1111713478"


@pytest.mark.parametrize("bad", ["", "not-a-jwt", "a.b", "a.!!!.c", "a.b.c.d"])
def test_decode_token_claims_rejects_malformed(bad: str) -> None:
    assert decode_token_claims(bad) is None
    assert token_expiry_from_claims(bad) is None
    assert token_client_id_from_claims(bad) is None


def test_token_expiry_from_claims_returns_utc() -> None:
    expiry = datetime(2026, 9, 4, 14, 30, 58, tzinfo=UTC)
    token = make_token({"exp": int(expiry.timestamp()), "dhanClientId": "1111713478"})
    assert token_expiry_from_claims(token) == expiry
    assert token_client_id_from_claims(token) == "1111713478"


def test_token_expiry_ignores_non_numeric_and_bool_exp() -> None:
    assert token_expiry_from_claims(make_token({"exp": "soon"})) is None
    assert token_expiry_from_claims(make_token({"exp": True})) is None
    assert token_expiry_from_claims(make_token({})) is None


def test_env_expiry_falls_back_to_token_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    expiry = datetime.now(tz=UTC) + timedelta(hours=10)
    token = make_token({"exp": int(expiry.timestamp()), "dhanClientId": "1111713478"})
    monkeypatch.setenv("DHAN_CLIENT_ID", "1111713478")
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", token)
    monkeypatch.delenv("DHAN_TOKEN_EXPIRES_AT", raising=False)

    from app.config import Settings

    creds = resolve_dhan_credentials(settings=Settings.load(env_file=None))
    assert creds is not None
    assert creds.source == "environment"
    assert creds.expires_at is not None
    assert int(creds.expires_at.timestamp()) == int(expiry.timestamp())


def test_explicit_env_expiry_wins_over_token_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    token = make_token({"exp": 1788445858, "dhanClientId": "1111713478"})
    monkeypatch.setenv("DHAN_CLIENT_ID", "1111713478")
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", token)
    monkeypatch.setenv("DHAN_TOKEN_EXPIRES_AT", "2026-09-09T00:00:00+00:00")

    from app.config import Settings

    creds = resolve_dhan_credentials(settings=Settings.load(env_file=None))
    assert creds is not None
    assert creds.expires_at == datetime(2026, 9, 9, tzinfo=UTC)


def test_dpapi_store_derives_expiry_and_round_trips(tmp_path: Path) -> None:
    expiry = datetime.now(tz=UTC) + timedelta(hours=20)
    token = make_token({"exp": int(expiry.timestamp()), "dhanClientId": "1111713478"})
    fake = FakeDPAPI()

    store_dhan_credentials_dpapi(
        client_id="1111713478",
        access_token=token,
        expires_at=None,
        runtime_root=tmp_path,
        dpapi_adapter=fake,
    )

    from app.config import Settings

    creds = resolve_dhan_credentials(
        settings=Settings.load(env_file=None),
        runtime_root=tmp_path,
        dpapi_adapter=fake,
    )
    assert creds is not None
    assert creds.source == "dpapi"
    assert creds.expires_at is not None
    assert int(creds.expires_at.timestamp()) == int(expiry.timestamp())


def test_cli_set_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stale = datetime.now(tz=UTC) - timedelta(hours=1)
    token = make_token({"exp": int(stale.timestamp()), "dhanClientId": "1111713478"})
    monkeypatch.setattr(token_cli, "_read_token", lambda: token)
    monkeypatch.setattr(token_cli, "_runtime_root", lambda: tmp_path)

    assert token_cli.main(["set"]) == 1
    assert "already expired" in capsys.readouterr().err


def test_cli_set_requires_a_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(token_cli, "_read_token", lambda: "")
    monkeypatch.setattr(token_cli, "_runtime_root", lambda: tmp_path)

    assert token_cli.main(["set"]) == 2
    assert "No token provided" in capsys.readouterr().err


def test_cli_set_requires_derivable_client_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    future = datetime.now(tz=UTC) + timedelta(hours=5)
    token = make_token({"exp": int(future.timestamp())})
    monkeypatch.setattr(token_cli, "_read_token", lambda: token)
    monkeypatch.setattr(token_cli, "_runtime_root", lambda: tmp_path)

    assert token_cli.main(["set"]) == 2
    assert "--client-id" in capsys.readouterr().err


def test_cli_set_status_clear_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    future = datetime.now(tz=UTC) + timedelta(hours=20)
    token = make_token({"exp": int(future.timestamp()), "dhanClientId": "1111713478"})
    monkeypatch.setattr(token_cli, "_read_token", lambda: token)
    monkeypatch.setattr(token_cli, "_runtime_root", lambda: tmp_path)
    monkeypatch.setattr("app.dhan.credentials.get_dpapi_adapter", lambda: FakeDPAPI())
    monkeypatch.delenv("DHAN_CLIENT_ID", raising=False)
    monkeypatch.delenv("DHAN_ACCESS_TOKEN", raising=False)

    assert token_cli.main(["set"]) == 0
    set_out = capsys.readouterr().out
    assert token not in set_out
    assert "1111***478" in set_out

    assert token_cli.main(["status"]) == 0
    status_out = capsys.readouterr().out
    assert token not in status_out
    assert "source     : dpapi" in status_out

    assert token_cli.main(["clear"]) == 0
    assert "removed" in capsys.readouterr().out
