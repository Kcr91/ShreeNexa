"""Blue/Green deployment and rollback controller for ShreeNexa API (F13.2).

Manages zero-downtime deployment:
- Blue API instance: 127.0.0.1:8000
- Green API instance: 127.0.0.1:8001
- Inspects and flips Caddy upstream
- Pre-traffic candidate health gating
- Automatic rollback on health probe failure
- Invariant: Leaves engine, feedd, and worker completely untouched
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

PORT_BLUE = 8000
PORT_GREEN = 8001
COLOR_BLUE = "blue"
COLOR_GREEN = "green"

PORTS_BY_COLOR = {
    COLOR_BLUE: PORT_BLUE,
    COLOR_GREEN: PORT_GREEN,
}

COLORS_BY_PORT = {
    PORT_BLUE: COLOR_BLUE,
    PORT_GREEN: COLOR_GREEN,
}


@dataclass(frozen=True)
class DeploymentResult:
    success: bool
    previous_color: str
    active_color: str
    message: str


def get_active_color(caddyfile_content: str) -> str:
    """Determine the currently routed color from Caddyfile reverse_proxy upstream."""
    if f"127.0.0.1:{PORT_GREEN}" in caddyfile_content:
        return COLOR_GREEN
    return COLOR_BLUE


def get_candidate_color(active_color: str) -> str:
    """Get the opposite color for candidate deployment."""
    return COLOR_GREEN if active_color == COLOR_BLUE else COLOR_BLUE


def flip_caddyfile_content(content: str, target_color: str) -> str:
    """Replace upstream port in Caddyfile content with target color's port."""
    target_port = PORTS_BY_COLOR[target_color]
    # Match reverse_proxy directives targeting 127.0.0.1:8000 or 8001
    pattern = r"(reverse_proxy\s+(?:\{\$UPSTREAM_API:)?127\.0\.0\.1:)(8000|8001)(\}?)"
    replacement = rf"\g<1>{target_port}\g<3>"
    return re.sub(pattern, replacement, content)


def probe_health(port: int, host: str = "127.0.0.1", timeout: float = 3.0) -> bool:
    """Probe /healthz endpoint on candidate port."""
    url = f"http://{host}:{port}/healthz"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ShreeNexa-Deploy-Controller/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return bool(response.status == 200)
    except Exception:
        return False


def promote_candidate(
    caddyfile_path: Path,
    *,
    health_checker: Callable[[int], bool] = probe_health,
) -> DeploymentResult:
    """Promote candidate color if health check passes.

    Fails safely without touching Caddyfile if candidate is unhealthy.
    """
    if not caddyfile_path.exists():
        return DeploymentResult(
            success=False,
            previous_color=COLOR_BLUE,
            active_color=COLOR_BLUE,
            message=f"Caddyfile not found at {caddyfile_path}",
        )

    current_content = caddyfile_path.read_text(encoding="utf-8")
    active_color = get_active_color(current_content)
    candidate_color = get_candidate_color(active_color)
    candidate_port = PORTS_BY_COLOR[candidate_color]

    # Pre-flight candidate health check
    if not health_checker(candidate_port):
        return DeploymentResult(
            success=False,
            previous_color=active_color,
            active_color=active_color,
            message=(
                f"Candidate {candidate_color} on port {candidate_port} failed health probe. "
                f"Promotion aborted; {active_color} remains active."
            ),
        )

    # Flip upstream in Caddyfile
    updated_content = flip_caddyfile_content(current_content, candidate_color)
    caddyfile_path.write_text(updated_content, encoding="utf-8")

    return DeploymentResult(
        success=True,
        previous_color=active_color,
        active_color=candidate_color,
        message=(
            f"Successfully promoted {candidate_color} (port {candidate_port}) "
            "to active upstream."
        ),
    )


def rollback(caddyfile_path: Path) -> DeploymentResult:
    """Immediately rollback Caddy upstream to the opposite color."""
    if not caddyfile_path.exists():
        return DeploymentResult(
            success=False,
            previous_color=COLOR_BLUE,
            active_color=COLOR_BLUE,
            message=f"Caddyfile not found at {caddyfile_path}",
        )

    current_content = caddyfile_path.read_text(encoding="utf-8")
    active_color = get_active_color(current_content)
    rollback_color = get_candidate_color(active_color)
    rollback_port = PORTS_BY_COLOR[rollback_color]

    updated_content = flip_caddyfile_content(current_content, rollback_color)
    caddyfile_path.write_text(updated_content, encoding="utf-8")

    return DeploymentResult(
        success=True,
        previous_color=active_color,
        active_color=rollback_color,
        message=(
            f"Rolled back active upstream from {active_color} to {rollback_color} "
            f"(port {rollback_port})."
        ),
    )
