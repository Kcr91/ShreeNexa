"""Unit tests for central application settings and secret redaction."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from app.config import Settings, mask_client_id, redact_text
from pydantic import SecretStr


def test_default_settings() -> None:
    settings = Settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.get_database_dsn().startswith("postgresql+psycopg://")
    assert settings.get_redis_dsn().startswith("redis://")
    assert settings.dhan_client_id is None
    assert settings.dhan_access_token is None


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DHAN_CLIENT_ID", "0000000000")
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "SECRET_TOKEN_VALUE_XYZ")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://custom_user:custom_pass@localhost:5432/custom_db",
    )

    settings = Settings.load(env_file=None)
    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.dhan_client_id == "0000000000"
    assert settings.dhan_access_token is not None
    assert settings.dhan_access_token.get_secret_value() == "SECRET_TOKEN_VALUE_XYZ"
    assert (
        settings.get_database_dsn()
        == "postgresql+psycopg://custom_user:custom_pass@localhost:5432/custom_db"
    )


def test_settings_load_from_env_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env_file = Path(temp_dir) / ".env.test"
        env_file.write_text(
            "ENVIRONMENT=production\n"
            "LOG_LEVEL=WARNING\n"
            "DHAN_CLIENT_ID=2233445566\n"
            "DHAN_ACCESS_TOKEN=FILE_SECRET_TOKEN\n",
            encoding="utf-8",
        )
        # Ensure env vars don't override
        old_env = os.environ.copy()
        for key in ("ENVIRONMENT", "LOG_LEVEL", "DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN"):
            os.environ.pop(key, None)
        try:
            settings = Settings.load(env_file=env_file)
            assert settings.environment == "production"
            assert settings.log_level == "WARNING"
            assert settings.dhan_client_id == "2233445566"
            assert settings.dhan_access_token is not None
            assert settings.dhan_access_token.get_secret_value() == "FILE_SECRET_TOKEN"
        finally:
            os.environ.clear()
            os.environ.update(old_env)


def test_secrets_never_appear_in_repr_or_str() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+psycopg://u:super_secret_db_pw@host/db"),
        dhan_client_id="0000000000",
        dhan_access_token=SecretStr("super_secret_dhan_access_token_12345"),
    )
    repr_str = repr(settings)
    str_val = str(settings)

    assert "super_secret_db_pw" not in repr_str
    assert "super_secret_dhan_access_token_12345" not in repr_str
    assert "super_secret_db_pw" not in str_val
    assert "super_secret_dhan_access_token_12345" not in str_val

    assert "**********" in repr_str
    assert "0000***000" in repr_str


def test_redact_text() -> None:
    raw = (
        "Connection error: postgresql+psycopg://user:secret_pw_123@db.prod.internal:5432/main "
        "with header Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.supersecret "
        "and access_token='my_dhan_token_xyz' password=hunter2"
    )
    redacted = redact_text(raw)
    assert "secret_pw_123" not in redacted
    assert "eyJhbGciOiJIUzI1NiJ9.supersecret" not in redacted
    assert "my_dhan_token_xyz" not in redacted
    assert "hunter2" not in redacted
    assert "[REDACTED]" in redacted


def test_mask_client_id() -> None:
    assert mask_client_id(None) == "[NONE]"
    assert mask_client_id("") == "[NONE]"
    assert mask_client_id("123") == "****"
    assert mask_client_id("1100223344") == "1100***344"
    assert mask_client_id("ABCDEFGH") == "ABCD***GH"
