"""Smoke test proving the backend test layer works end to end (F0.1 baseline)."""

from __future__ import annotations

import re

from app import __version__


def test_app_package_is_importable_and_versioned() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)
