"""Central application configuration and secret redaction for ShreeNexa Terminal."""

from __future__ import annotations

import functools
import os
import re
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr

SECRET_PATTERNS = [
    re.compile(r"(?i)bearer\s+['\"]?([^\s'\"]+)['\"]?"),
    re.compile(r"(?i)authorization[\s:=]+(?:bearer\s+)?['\"]?([^\s'\"]+)['\"]?"),
    re.compile(
        r"(?i)(?:access_token|refresh_token|api_secret|client_secret|password|passwd|pwd)[\s:=]+['\"]?([^\s'\"]+)['\"]?"
    ),
    re.compile(r"postgresql(?:\+psycopg)?://[^:]+:([^@]+)@"),
]


def redact_text(text: str) -> str:
    """Redact secret-shaped tokens and passwords from arbitrary text."""
    redacted = text
    for pattern in SECRET_PATTERNS:

        def _replace_match(m: re.Match[str]) -> str:
            full_match = m.group(0)
            if len(m.groups()) == 1 and m.group(1):
                secret_part = m.group(1)
                return full_match.replace(secret_part, "[REDACTED]")
            return "[REDACTED]"

        redacted = pattern.sub(_replace_match, redacted)
    return redacted


def mask_client_id(client_id: str | None) -> str:
    """Mask a client ID for safe UI display (e.g., '1100***123' or '[NONE]')."""
    if not client_id:
        return "[NONE]"
    if len(client_id) <= 4:
        return "****"
    prefix_len = min(4, len(client_id) // 2)
    suffix_len = min(3, (len(client_id) - prefix_len) // 2)
    if suffix_len <= 0:
        return client_id[:prefix_len] + "***"
    return f"{client_id[:prefix_len]}***{client_id[-suffix_len:]}"


class Settings(BaseModel):
    """Type-safe central application settings loaded from environment and .env file."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Authoritative and cache storage URLs
    database_url: SecretStr = Field(
        default=SecretStr(
            "postgresql+psycopg://shreenexa:shreenexa_dev@127.0.0.1:5432/shreenexa"
        )
    )
    redis_url: SecretStr = Field(default=SecretStr("redis://127.0.0.1:6379/0"))

    # Dhan API credentials
    dhan_client_id: str | None = Field(default=None)
    dhan_access_token: SecretStr | None = Field(default=None)
    dhan_token_expires_at: str | None = Field(default=None)

    # Runtime root directory for local operational state
    runtime_root: Path = Field(default=Path(".runtime"))

    @classmethod
    def load(cls, env_file: Path | str | None = ".env") -> Settings:
        """Load settings with precedence: OS environment > .env file > defaults."""
        file_values: dict[str, Any] = {}
        if env_file:
            path = Path(env_file)
            if path.is_file():
                file_values = {
                    k.lower(): v for k, v in dotenv_values(path).items() if v is not None
                }

        env_values: dict[str, Any] = {}
        for key, val in os.environ.items():
            env_values[key.lower()] = val

        merged: dict[str, Any] = {**file_values, **env_values}
        return cls(**merged)

    def get_database_dsn(self) -> str:
        """Return the raw database connection string."""
        return self.database_url.get_secret_value()

    def get_redis_dsn(self) -> str:
        """Return the raw redis connection string."""
        return self.redis_url.get_secret_value()

    def __repr__(self) -> str:
        fields = []
        for name in self.__class__.model_fields:
            val = getattr(self, name)
            if isinstance(val, SecretStr):
                fields.append(f"{name}=SecretStr('**********')")
            elif name == "dhan_client_id":
                fields.append(f"{name}={mask_client_id(val)!r}")
            else:
                fields.append(f"{name}={val!r}")
        return f"Settings({', '.join(fields)})"

    def __str__(self) -> str:
        return self.__repr__()


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings.load()
