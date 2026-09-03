"""Static IP validation helper for DhanHQ SEBI-mandated Order APIs.

Supports dual-IP topology:
- Primary IP (production server on AWS Lightsail Mumbai)
- Secondary IP (local developer or operator workstation)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.dhan.client import DhanRestClient


def get_current_outbound_ip() -> str | None:
    """Retrieve host outbound public IP address from environment configuration."""
    for env_var in ("SHREENEXA_STATIC_IP", "OUTBOUND_STATIC_IP", "HOST_PUBLIC_IP"):
        val = os.environ.get(env_var)
        if val and val.strip():
            return val.strip()
    return None



def validate_static_ip_preflight(
    client: DhanRestClient,
    current_public_ip: str | None = None,
) -> tuple[bool, str]:
    """Verify that current outbound host IP is whitelisted as Primary or Secondary in Dhan.

    Returns:
        tuple of (is_whitelisted, message)
    """
    try:
        ip_config = client.get_ip_config()
    except Exception as exc:
        return False, f"Failed to fetch Dhan IP configuration: {exc}"

    primary = (ip_config.primary_ip or "").strip()
    secondary = (ip_config.secondary_ip or "").strip()

    allowed_ips = [ip for ip in (primary, secondary) if ip]
    if not allowed_ips:
        return False, "No static IP is configured or whitelisted in Dhan account."

    host_ip = current_public_ip or get_current_outbound_ip()
    if not host_ip:
        return False, "Could not determine host outbound public IP address."

    if host_ip == primary:
        return True, f"Outbound IP {host_ip} matches Dhan Primary Static IP (Lightsail/Server)."

    if host_ip == secondary:
        return True, f"Outbound IP {host_ip} matches Dhan Secondary Static IP (Local Workstation)."

    return False, (
        f"Outbound host IP {host_ip} does not match any whitelisted Dhan IP "
        f"(Primary: {primary or 'none'}, Secondary: {secondary or 'none'}). "
        "Order execution blocked."
    )
