"""Cryptographic primitives for ShreeNexa authentication (F13.3).

Implements:
- PBKDF2-HMAC-SHA256 password hashing with 600,000 rounds
- RFC 6238 / RFC 4226 compliant TOTP generator and verifier
- Single-use recovery code hashing
- Constant-time secret comparisons
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

PBKDF2_ROUNDS = 600_000
SALT_BYTES = 16
TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def hash_password(password: str, *, rounds: int = PBKDF2_ROUNDS) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with cryptographically random salt."""
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash in constant time."""
    try:
        parts = password_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        rounds = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_derived = bytes.fromhex(parts[3])

        candidate_derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
        return hmac.compare_digest(candidate_derived, expected_derived)
    except Exception:
        return False


def generate_totp_secret() -> str:
    """Generate a cryptographically random 20-byte Base32 TOTP secret."""
    raw_bytes = secrets.token_bytes(20)
    return base64.b32encode(raw_bytes).decode("ascii").rstrip("=")


def _clean_base32(secret: str) -> bytes:
    """Normalize and pad Base32 secret string to 8-character multiples."""
    normalized = secret.strip().upper().replace(" ", "")
    padding_needed = (8 - len(normalized) % 8) % 8
    normalized += "=" * padding_needed
    return base64.b32decode(normalized, casefold=True)


def generate_totp_code(secret: str, timestamp: float | None = None) -> str:
    """Generate RFC 6238 6-digit TOTP code for a given timestamp."""
    current_time = time.time() if timestamp is None else timestamp
    time_counter = int(current_time // TOTP_STEP_SECONDS)

    key = _clean_base32(secret)
    counter_bytes = struct.pack(">Q", time_counter)

    hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_digest[-1] & 0x0F
    binary = (
        (hmac_digest[offset] & 0x7F) << 24
        | (hmac_digest[offset + 1] & 0xFF) << 16
        | (hmac_digest[offset + 2] & 0xFF) << 8
        | (hmac_digest[offset + 3] & 0xFF)
    )
    code = binary % (10**TOTP_DIGITS)
    return f"{code:0{TOTP_DIGITS}d}"


def verify_totp_code(
    secret: str,
    code: str,
    *,
    timestamp: float | None = None,
    window: int = 1,
) -> bool:
    """Verify a TOTP code within a clock-skew window (default ±1 step / ±30s)."""
    clean_code = code.strip()
    if len(clean_code) != TOTP_DIGITS or not clean_code.isdigit():
        return False

    current_time = time.time() if timestamp is None else timestamp
    base_counter = int(current_time // TOTP_STEP_SECONDS)

    for offset in range(-window, window + 1):
        test_time = (base_counter + offset) * TOTP_STEP_SECONDS
        expected = generate_totp_code(secret, timestamp=test_time)
        if hmac.compare_digest(clean_code, expected):
            return True
    return False


def normalize_recovery_code(code: str) -> str:
    """Normalize recovery code by stripping whitespace and dashes."""
    return code.strip().replace("-", "").upper()


def hash_recovery_code(code: str) -> str:
    """Compute deterministic SHA-256 hash of a normalized recovery code."""
    normalized = normalize_recovery_code(code)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_recovery_codes(count: int = 8) -> list[str]:
    """Generate readable recovery codes formatted as XXXX-XXXX-XXXX."""
    codes: list[str] = []
    for _ in range(count):
        raw = secrets.token_hex(6).upper()
        formatted = f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}"
        codes.append(formatted)
    return codes
