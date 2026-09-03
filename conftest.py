"""Root test configuration and hermetic test environment fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from app.config import get_settings


@pytest.fixture(autouse=True)
def hermetic_test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Ensure test runs do not read live credentials from developer's .env file."""
    # Unless a test explicitly requests a specific env file, disable loading the repo .env
    if "SHREENEXA_ENV_FILE" not in os.environ:
        monkeypatch.setenv("SHREENEXA_ENV_FILE", "")

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
