"""Static IP validation helper for DhanHQ SEBI-mandated Order APIs.

Supports dual-IP topology:
- Primary IP (production server on AWS Lightsail Mumbai)
- Secondary IP (local developer or operator workstation)

SEBI Security Mandate & Fail-Closed Invariant (QA-09 / F12.1):
Static IP verification resolves the host's actual public outbound egress IP
via hardened external IP discovery services rather than trusting arbitrary
unverified environment variables.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.dhan.client import DhanRestClient

logger = logging.getLogger("shreenexa.dhan.ip")

_cached_outbound_ip: str | None = None

# Hardened endpoints for outbound public IP discovery
IP_ECHO_SERVICES: tuple[str, ...] = (
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
    "https://checkip.amazonaws.com",
    "https://icanhazip.com",
)


def _is_valid_ipv4(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return ip.version == 4
    except ValueError:
        return False


def reset_outbound_ip_cache() -> None:
    """Clear cached egress IP (primarily for isolated test fixtures)."""
    global _cached_outbound_ip
    _cached_outbound_ip = None


def get_current_outbound_ip(force_refresh: bool = False) -> str | None:
    """Resolve the host's actual outbound public IP address with fail-closed security.

    Priority:
    1. In-process cache (persists for the process lifetime to avoid network spam).
    2. SHREENEXA_STATIC_IP_OVERRIDE (explicitly logged offline test override;
       STRICTLY ignored when APP_ENV=production or ENVIRONMENT=production).
    3. Live HTTP queries to hardened IP echo services with a 2.0-second timeout.
    4. If resolution fails or host is offline, returns None (fail-closed, orders are blocked).
    """
    global _cached_outbound_ip

    if _cached_outbound_ip is not None and not force_refresh:
        return _cached_outbound_ip

    # Check offline test override
    env_mode = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    override = os.environ.get("SHREENEXA_STATIC_IP_OVERRIDE")
    if override and override.strip():
        if env_mode == "production":
            logger.warning(
                "SHREENEXA_STATIC_IP_OVERRIDE is disallowed in production environment. "
                "Resolving actual egress IP."
            )
        else:
            cleaned = override.strip()
            if _is_valid_ipv4(cleaned):
                logger.info("Using explicit test static IP override: %s", cleaned)
                _cached_outbound_ip = cleaned
                return _cached_outbound_ip
            logger.warning("Invalid IP format in SHREENEXA_STATIC_IP_OVERRIDE: %s", cleaned)

    # Perform real egress IP discovery across hardened endpoints
    for endpoint in IP_ECHO_SERVICES:
        try:
            req = urllib.request.Request(
                endpoint,
                headers={"User-Agent": "ShreeNexa-StaticIP-Preflight/1.0"},
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8").strip()
                    if _is_valid_ipv4(raw):
                        _cached_outbound_ip = raw
                        logger.info("Resolved host outbound public IP: %s (via %s)", raw, endpoint)
                        return _cached_outbound_ip
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            logger.debug("IP echo lookup failed via %s: %s", endpoint, exc)
            continue

    logger.error("Failed to determine host outbound public IP address from any discovery service.")
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
