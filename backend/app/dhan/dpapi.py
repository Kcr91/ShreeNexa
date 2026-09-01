"""Windows Data Protection API (DPAPI) adapter for local credential encryption.

Implements current-user scoped credential encryption without plaintext fallback
per ADR-0006.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Protocol


class DPAPIError(RuntimeError):
    """Raised when DPAPI encryption or decryption fails."""


class DPAPIAdapter(Protocol):
    """Protocol for DPAPI operations."""

    def protect(self, data: bytes, description: str = "") -> bytes: ...

    def unprotect(self, encrypted: bytes) -> bytes: ...


class WindowsDPAPI:
    """Real Windows DPAPI implementation using CryptProtectData and CryptUnprotectData."""

    CRYPTPROTECT_UI_FORBIDDEN = 0x01

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise DPAPIError("Windows DPAPI is only available on win32 platforms")
        import ctypes.wintypes as wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char)),
            ]

        self._DATA_BLOB = DATA_BLOB
        self._crypt32 = ctypes.windll.crypt32
        self._kernel32 = ctypes.windll.kernel32

    def protect(self, data: bytes, description: str = "") -> bytes:
        """Encrypt bytes using current-user Windows DPAPI."""
        if not data:
            raise DPAPIError("Cannot protect empty data")

        buffer = ctypes.create_string_buffer(data, len(data))
        data_in = self._DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        data_out = self._DATA_BLOB()
        desc = ctypes.c_wchar_p(description) if description else None

        # Flags: CRYPTPROTECT_UI_FORBIDDEN (0x01).
        # We explicitly do NOT pass CRYPTPROTECT_LOCAL_MACHINE (0x04), ensuring
        # the encrypted data is bound exclusively to the current user's credentials.
        success = self._crypt32.CryptProtectData(
            ctypes.byref(data_in),
            desc,
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            self.CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out),
        )
        if not success:
            error_code = self._kernel32.GetLastError()
            raise DPAPIError(f"CryptProtectData failed with Windows error code {error_code}")

        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            self._kernel32.LocalFree(data_out.pbData)

    def unprotect(self, encrypted: bytes) -> bytes:
        """Decrypt bytes using current-user Windows DPAPI."""
        if not encrypted:
            raise DPAPIError("Cannot unprotect empty data")

        buffer = ctypes.create_string_buffer(encrypted, len(encrypted))
        data_in = self._DATA_BLOB(
            len(encrypted),
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)),
        )
        data_out = self._DATA_BLOB()

        success = self._crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,  # Description output
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            self.CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out),
        )
        if not success:
            error_code = self._kernel32.GetLastError()
            raise DPAPIError(f"CryptUnprotectData failed with Windows error code {error_code}")

        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            self._kernel32.LocalFree(data_out.pbData)


class FakeDPAPI:
    """Deterministic fake DPAPI adapter for isolated automated tests on any platform."""

    PREFIX = b"FAKEDPAPI::"

    def protect(self, data: bytes, description: str = "") -> bytes:
        if not data:
            raise DPAPIError("Cannot protect empty data")
        return self.PREFIX + data[::-1]

    def unprotect(self, encrypted: bytes) -> bytes:
        if not encrypted:
            raise DPAPIError("Cannot unprotect empty data")
        if not encrypted.startswith(self.PREFIX):
            raise DPAPIError("Invalid fake DPAPI ciphertext")
        raw = encrypted[len(self.PREFIX) :]
        return raw[::-1]


def get_dpapi_adapter(*, force_fake: bool = False) -> DPAPIAdapter:
    """Get the appropriate DPAPI adapter for the current environment."""
    if force_fake or sys.platform != "win32":
        return FakeDPAPI()
    return WindowsDPAPI()


def save_encrypted_file(path: Path, encrypted_data: bytes) -> None:
    """Write encrypted bytes atomically to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f".tmp.{os.getpid()}")
    temp_path.write_bytes(encrypted_data)
    temp_path.replace(path)


def read_encrypted_file(path: Path) -> bytes:
    """Read encrypted bytes from disk."""
    if not path.is_file():
        raise FileNotFoundError(f"Encrypted file not found: {path}")
    return path.read_bytes()
