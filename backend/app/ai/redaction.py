"""Prompt and payload secret scrubber ensuring no credentials reach AI providers."""

from __future__ import annotations

import re

# RegEx patterns for common credentials and Indian market broker secrets
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # JWT tokens
    (
        re.compile(
            r"ey[A-Za-z0-9_-]{10,}\.ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
            re.IGNORECASE,
        ),
        "[REDACTED_JWT]",
    ),
    # Bearer tokens
    (
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        "Bearer [REDACTED_TOKEN]",
    ),
    # Private Key blocks
    (
        re.compile(
            r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
            re.IGNORECASE,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # Dhan Client IDs or access tokens
    (
        re.compile(
            r"(client_id|dhan_client_id|access_token|dhan_token)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{6,}['\"]?",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
    # API keys and secret keys
    (
        re.compile(
            r"(api_key|apikey|secret_key|api_secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
    # Passwords
    (
        re.compile(
            r"(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"&]+['\"]?",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, client IDs, and passwords from text."""
    scrubbed = text
    for pattern, replacement in _PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def contains_secret(text: str) -> bool:
    """Check whether text matches any known sensitive credential patterns."""
    return any(pattern.search(text) is not None for pattern, _ in _PATTERNS)
