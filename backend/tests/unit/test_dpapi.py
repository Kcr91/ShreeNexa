"""Unit tests for Windows DPAPI credential persistence."""

from __future__ import annotations

import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.config import Settings
from app.dhan.credentials import (
    clear_dhan_credentials_dpapi,
    resolve_dhan_credentials,
    store_dhan_credentials_dpapi,
)
from app.dhan.dpapi import (
    DPAPIError,
    FakeDPAPI,
    WindowsDPAPI,
    read_encrypted_file,
    save_encrypted_file,
)


def test_fake_dpapi_round_trip() -> None:
    fake = FakeDPAPI()
    data = b"secret_dhan_token_payload_12345"
    protected = fake.protect(data)
    assert protected != data
    assert fake.unprotect(protected) == data


def test_fake_dpapi_empty_data_rejection() -> None:
    fake = FakeDPAPI()
    with pytest.raises(DPAPIError, match="Cannot protect empty data"):
        fake.protect(b"")
    with pytest.raises(DPAPIError, match="Cannot unprotect empty data"):
        fake.unprotect(b"")


def test_fake_dpapi_tamper_rejection() -> None:
    fake = FakeDPAPI()
    with pytest.raises(DPAPIError, match="Invalid fake DPAPI ciphertext"):
        fake.unprotect(b"tampered_ciphertext_without_prefix")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI requires win32 platform")
def test_windows_dpapi_round_trip() -> None:
    dpapi = WindowsDPAPI()
    data = b"real_windows_dpapi_credential_payload"
    protected = dpapi.protect(data, description="Test Credentials")
    assert protected != data
    assert dpapi.unprotect(protected) == data


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI requires win32 platform")
def test_windows_dpapi_tamper_rejection() -> None:
    dpapi = WindowsDPAPI()
    protected = dpapi.protect(b"valid_payload")
    # Corrupt ciphertext bytes
    tampered = bytearray(protected)
    tampered[-5] = (tampered[-5] + 1) % 256
    with pytest.raises(DPAPIError):
        dpapi.unprotect(bytes(tampered))


def test_save_and_read_encrypted_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "subdir" / "creds.enc"
        test_data = b"encrypted_binary_bytes_998877"
        save_encrypted_file(file_path, test_data)
        assert file_path.is_file()
        assert read_encrypted_file(file_path) == test_data


def test_store_and_resolve_credentials_dpapi() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        fake_adapter = FakeDPAPI()
        runtime_root = Path(temp_dir) / "runtime"
        expiry = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

        target = store_dhan_credentials_dpapi(
            client_id="1100998877",
            access_token="MY_SECRET_DPAPI_TOKEN",
            expires_at=expiry,
            runtime_root=runtime_root,
            dpapi_adapter=fake_adapter,
        )
        assert target.is_file()

        # Verify plaintext is NEVER written to the file
        raw_disk_bytes = target.read_bytes()
        assert b"MY_SECRET_DPAPI_TOKEN" not in raw_disk_bytes

        # Resolve without env vars
        empty_settings = Settings(dhan_client_id=None, dhan_access_token=None)
        resolved = resolve_dhan_credentials(
            settings=empty_settings,
            runtime_root=runtime_root,
            dpapi_adapter=fake_adapter,
        )
        assert resolved is not None
        assert resolved.client_id == "1100998877"
        assert resolved.get_token_value() == "MY_SECRET_DPAPI_TOKEN"
        assert resolved.expires_at == expiry
        assert resolved.source == "dpapi"


def test_env_credentials_override_dpapi() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        fake_adapter = FakeDPAPI()
        runtime_root = Path(temp_dir) / "runtime"
        store_dhan_credentials_dpapi(
            client_id="DPAPI_CLIENT_ID",
            access_token="DPAPI_TOKEN",
            runtime_root=runtime_root,
            dpapi_adapter=fake_adapter,
        )

        env_settings = Settings(
            dhan_client_id="ENV_CLIENT_ID",
            dhan_access_token="ENV_TOKEN",  # type: ignore[arg-type]
        )

        resolved = resolve_dhan_credentials(
            settings=env_settings,
            runtime_root=runtime_root,
            dpapi_adapter=fake_adapter,
        )
        assert resolved is not None
        assert resolved.client_id == "ENV_CLIENT_ID"
        assert resolved.get_token_value() == "ENV_TOKEN"
        assert resolved.source == "environment"


def test_clear_credentials_dpapi() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        fake_adapter = FakeDPAPI()
        runtime_root = Path(temp_dir) / "runtime"
        target = store_dhan_credentials_dpapi(
            client_id="1100",
            access_token="TOK",
            runtime_root=runtime_root,
            dpapi_adapter=fake_adapter,
        )
        assert target.is_file()
        assert clear_dhan_credentials_dpapi(runtime_root=runtime_root) is True
        assert not target.is_file()
        assert clear_dhan_credentials_dpapi(runtime_root=runtime_root) is False
