"""Unit tests for Dhan WebSocket connection budget configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

from app.feedd.budget import (
    ConnectionBudgetConfig,
    PoolMode,
    load_budget_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "feed_budget.yaml"


def test_load_budget_config_from_yaml() -> None:
    """Verify loading default budget configuration from YAML file."""
    assert CONFIG_PATH.is_file()
    cfg = load_budget_config(CONFIG_PATH)

    assert cfg.pool_mode == PoolMode.SHARED
    assert cfg.total_capacity == 5
    assert cfg.feed_capacity == 3
    assert cfg.depth_capacity == 2
    assert cfg.acquire_timeout_seconds == 5.0


def test_load_budget_config_missing_file() -> None:
    """Verify default fallback values when configuration file is missing."""
    cfg = load_budget_config("non_existent_config.yaml")
    assert cfg.pool_mode == PoolMode.SHARED
    assert cfg.total_capacity == 5
    assert cfg.feed_capacity == 3
    assert cfg.depth_capacity == 2


def test_independent_pool_config_model() -> None:
    """Verify configuring independent 5/5 pools."""
    cfg = ConnectionBudgetConfig(
        pool_mode=PoolMode.INDEPENDENT,
        total_capacity=10,
        feed_capacity=5,
        depth_capacity=5,
        acquire_timeout_seconds=2.0,
    )
    assert cfg.pool_mode == PoolMode.INDEPENDENT
    assert cfg.feed_capacity == 5
    assert cfg.depth_capacity == 5
