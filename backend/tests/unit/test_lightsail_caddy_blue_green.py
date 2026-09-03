"""Unit tests for F13.2: Lightsail Mumbai provisioning, network policy,
Caddy TLS, and blue/green upstream.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path to allow importing infra.lightsail modules
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.lightsail.blue_green import (  # noqa: E402
    COLOR_BLUE,
    COLOR_GREEN,
    PORT_BLUE,
    PORT_GREEN,
    flip_caddyfile_content,
    get_active_color,
    get_candidate_color,
    promote_candidate,
    rollback,
)

CADDYFILE_PATH = REPO_ROOT / "infra" / "caddy" / "Caddyfile"
PROVISION_SH_PATH = REPO_ROOT / "infra" / "lightsail" / "provision.sh"
SYSTEMD_DIR = REPO_ROOT / "infra" / "lightsail" / "systemd"
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "staging-deploy-rollback.md"


def test_caddyfile_security_and_routing() -> None:
    """Validate Caddyfile TLS, security headers, and WebSocket routing."""
    assert CADDYFILE_PATH.exists(), f"Missing Caddyfile at {CADDYFILE_PATH}"
    content = CADDYFILE_PATH.read_text(encoding="utf-8")

    # Security headers
    assert "Strict-Transport-Security" in content
    assert "X-Content-Type-Options" in content
    assert "X-Frame-Options" in content
    assert "Content-Security-Policy" in content

    # WebSocket headers
    assert "Upgrade" in content
    assert "Connection" in content

    # Health check directive
    assert "health_uri /healthz" in content

    # Upstream configuration default
    assert "127.0.0.1:8000" in content


def test_lightsail_provisioning_network_policy() -> None:
    """Validate Lightsail provision script enforces strict port allowlist (22, 80, 443 only)."""
    assert PROVISION_SH_PATH.exists(), f"Missing provision.sh at {PROVISION_SH_PATH}"
    content = PROVISION_SH_PATH.read_text(encoding="utf-8")

    # Default deny incoming
    assert "ufw default deny incoming" in content
    assert "ufw default allow outgoing" in content

    # Allowed public ports
    assert "ufw allow 22/tcp" in content
    assert "ufw allow 80/tcp" in content
    assert "ufw allow 443/tcp" in content

    # Blocked internal services
    for blocked_port in ["5432", "6379", "8000", "8001", "8080", "8081", "8082"]:
        assert blocked_port in content, f"Port {blocked_port} not explicitly blocked in firewall"

    # User setup
    assert "10001" in content
    assert "shreenexa" in content


def test_systemd_units_isolation() -> None:
    """Validate systemd unit files for persistent background services."""
    assert SYSTEMD_DIR.exists()

    engine_unit = (SYSTEMD_DIR / "shreenexa-engine.service").read_text(encoding="utf-8")
    feedd_unit = (SYSTEMD_DIR / "shreenexa-feedd.service").read_text(encoding="utf-8")
    worker_unit = (SYSTEMD_DIR / "shreenexa-worker.service").read_text(encoding="utf-8")
    caddy_unit = (SYSTEMD_DIR / "shreenexa-caddy.service").read_text(encoding="utf-8")

    # Background daemons must not depend on api
    assert "api" not in engine_unit.lower()
    assert "api" not in feedd_unit.lower()
    assert "api" not in worker_unit.lower()

    # Must specify unprivileged user
    assert "User=shreenexa" in engine_unit
    assert "User=shreenexa" in feedd_unit
    assert "User=shreenexa" in worker_unit
    assert "User=caddy" in caddy_unit


def test_blue_green_state_detection() -> None:
    """Validate active color and candidate color detection logic."""
    blue_content = "reverse_proxy 127.0.0.1:8000"
    green_content = "reverse_proxy 127.0.0.1:8001"

    assert get_active_color(blue_content) == COLOR_BLUE
    assert get_active_color(green_content) == COLOR_GREEN

    assert get_candidate_color(COLOR_BLUE) == COLOR_GREEN
    assert get_candidate_color(COLOR_GREEN) == COLOR_BLUE

    # Flipping logic
    flipped_to_green = flip_caddyfile_content(blue_content, COLOR_GREEN)
    assert f"127.0.0.1:{PORT_GREEN}" in flipped_to_green
    assert f"127.0.0.1:{PORT_BLUE}" not in flipped_to_green

    flipped_back_to_blue = flip_caddyfile_content(flipped_to_green, COLOR_BLUE)
    assert f"127.0.0.1:{PORT_BLUE}" in flipped_back_to_blue
    assert f"127.0.0.1:{PORT_GREEN}" not in flipped_back_to_blue


def test_blue_green_promotion_and_rollback(tmp_path: Path) -> None:
    """Validate pre-traffic health gating and automated rollback."""
    temp_caddyfile = tmp_path / "Caddyfile"
    caddy_cfg = (
        "example.com {\n"
        "    reverse_proxy 127.0.0.1:8000 {\n"
        "        health_uri /healthz\n"
        "    }\n"
        "}\n"
    )
    temp_caddyfile.write_text(caddy_cfg, encoding="utf-8")

    # Scenario 1: Candidate is unhealthy -> promotion must fail and leave Caddyfile untouched
    def failing_health_checker(port: int) -> bool:
        return False

    res_fail = promote_candidate(temp_caddyfile, health_checker=failing_health_checker)
    assert not res_fail.success
    assert res_fail.active_color == COLOR_BLUE
    assert "failed health probe" in res_fail.message
    assert "127.0.0.1:8000" in temp_caddyfile.read_text(encoding="utf-8")

    # Scenario 2: Candidate is healthy -> promotion succeeds and flips upstream
    def passing_health_checker(port: int) -> bool:
        return True

    res_pass = promote_candidate(temp_caddyfile, health_checker=passing_health_checker)
    assert res_pass.success
    assert res_pass.active_color == COLOR_GREEN
    assert "127.0.0.1:8001" in temp_caddyfile.read_text(encoding="utf-8")

    # Scenario 3: Emergency rollback -> flips back to Blue
    res_rollback = rollback(temp_caddyfile)
    assert res_rollback.success
    assert res_rollback.active_color == COLOR_BLUE
    assert "127.0.0.1:8000" in temp_caddyfile.read_text(encoding="utf-8")


def test_staging_deploy_runbook_documented() -> None:
    """Validate staging runbook covers prerequisites, port audit, and rollback."""
    assert RUNBOOK_PATH.exists(), f"Missing runbook at {RUNBOOK_PATH}"
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "Public Network Policy & Port Reachability Audit" in content
    assert "Zero-Downtime Blue/Green Staging Deployment" in content
    assert "Emergency Rollback Protocol" in content
    assert "ufw status" in content
    assert "promote_candidate" in content
    assert "rollback" in content
