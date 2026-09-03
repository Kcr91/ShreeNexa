"""Unit tests for F13.1: Production containers for api, engine, feedd, worker.

Validates multi-stage Dockerfile, non-root users, resource limits, health checks,
and process independence (restarting API leaves engine/paper deployment intact).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from app.contracts import heartbeat as hb
from app.contracts.health_check import check_process_health

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCKERFILE_PATH = REPO_ROOT / "infra" / "Dockerfile"
COMPOSE_PROD_PATH = REPO_ROOT / "infra" / "docker-compose.prod.yml"


def test_production_dockerfile_structure_and_security() -> None:
    """Validate Dockerfile multi-stage build, non-root user, and minimal attack surface."""
    assert DOCKERFILE_PATH.exists(), f"Missing Dockerfile at {DOCKERFILE_PATH}"

    content = DOCKERFILE_PATH.read_text(encoding="utf-8")

    # Multi-stage validation
    assert "FROM python:3.14-slim AS builder" in content
    assert "FROM python:3.14-slim AS runtime" in content

    # Non-root unprivileged user creation and activation
    assert "groupadd -g 10001 shreenexa" in content
    assert "useradd -u 10001 -g shreenexa" in content
    assert "USER shreenexa:shreenexa" in content

    # Security: no development or secrets baked in
    assert "shreenexa_secret" not in content.lower()
    assert "dhan_client_id" not in content.lower()

    # Base requirements
    assert "curl" in content  # for HTTP health checks
    assert "uv sync --frozen --no-dev" in content  # production dependencies only


def test_production_compose_services_and_limits() -> None:
    """Validate docker-compose.prod.yml defines required 4 processes and resource caps."""
    assert COMPOSE_PROD_PATH.exists(), f"Missing compose file at {COMPOSE_PROD_PATH}"

    with open(COMPOSE_PROD_PATH, encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    required_services = ["postgres", "valkey", "api", "engine", "feedd", "worker"]
    for s in required_services:
        assert s in services, f"Service '{s}' missing from production compose"

    # Validate non-root users and resource limits for the four application processes
    app_processes = ["api", "engine", "feedd", "worker"]
    for proc in app_processes:
        cfg = services[proc]
        # Non-root user enforcement
        assert cfg.get("user") in ["10001:10001", "shreenexa:shreenexa"], (
            f"Service '{proc}' must specify non-root user 10001:10001"
        )
        # Explicit resource limits
        assert "mem_limit" in cfg, f"Service '{proc}' missing mem_limit"
        assert "cpus" in cfg, f"Service '{proc}' missing cpus limit"

        # Explicit health check configuration
        assert "healthcheck" in cfg, f"Service '{proc}' missing healthcheck"
        hc = cfg["healthcheck"]
        assert "test" in hc
        assert "interval" in hc
        assert "timeout" in hc
        assert "retries" in hc


def test_production_compose_independence_invariant() -> None:
    """Proof invariant: Restarting API leaves engine, feedd, and worker intact."""
    with open(COMPOSE_PROD_PATH, encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})

    # The 3 background daemons must NOT have api in their depends_on
    for daemon in ["engine", "feedd", "worker"]:
        deps = services[daemon].get("depends_on", {})
        if isinstance(deps, list):
            dep_names = deps
        elif isinstance(deps, dict):
            dep_names = list(deps.keys())
        else:
            dep_names = []

        assert "api" not in dep_names, (
            f"Violation: '{daemon}' depends on 'api'. "
            f"ADR-0002 requires that restarting API leaves {daemon} intact."
        )

        # They must depend on database infrastructure
        assert "postgres" in dep_names
        assert "valkey" in dep_names


def test_health_check_module_logic() -> None:
    """Test health_check module against invalid process names and mock heartbeats."""
    # Invalid process name returns False
    assert not check_process_health("invalid_daemon")

    # Mock database heartbeat inspection
    mock_row = MagicMock()
    mock_row.status = hb.STATUS_RUNNING
    mock_row.last_heartbeat_at = datetime.now(tz=UTC)

    with patch("app.contracts.heartbeat.make_engine") as mock_engine_factory:
        mock_engine = MagicMock()
        mock_engine_factory.return_value = mock_engine

        # Case 1: Fresh running heartbeat -> True
        with patch("app.contracts.heartbeat.read", return_value=mock_row):
            assert check_process_health("engine", max_age_seconds=15.0)

        # Case 2: Absent heartbeat -> False
        with patch("app.contracts.heartbeat.read", return_value=None):
            assert not check_process_health("engine", max_age_seconds=15.0)

        # Case 3: Stopped process status -> False
        stopped_row = MagicMock()
        stopped_row.status = hb.STATUS_STOPPED
        stopped_row.last_heartbeat_at = datetime.now(tz=UTC)
        with patch("app.contracts.heartbeat.read", return_value=stopped_row):
            assert not check_process_health("engine", max_age_seconds=15.0)
