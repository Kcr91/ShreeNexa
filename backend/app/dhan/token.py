"""Local credential management CLI for the 24-hour Dhan Web access token.

Run as ``python -m app.dhan.token <command>``. The token is read from an
interactive prompt or stdin -- never from argv -- so it does not land in shell
history or the process table, and it is written only to the current-user
DPAPI-encrypted store described in ADR-0006.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from getpass import getpass
from pathlib import Path

from app.config import get_settings, mask_client_id
from app.dhan.credentials import (
    clear_dhan_credentials_dpapi,
    get_credentials_path,
    resolve_dhan_credentials,
    store_dhan_credentials_dpapi,
    token_client_id_from_claims,
    token_expiry_from_claims,
)
from app.dhan.dpapi import DPAPIError
from app.dhan.health import check_token_health


def _runtime_root() -> Path:
    return get_settings().runtime_root


def _format_remaining(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds <= 0:
        return "expired"
    hours, remainder = divmod(seconds, 3600)
    return f"{hours}h {remainder // 60}m"


def _read_token() -> str:
    """Read the token interactively, falling back to piped stdin."""
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return getpass("Paste Dhan access token (input hidden): ").strip()


def cmd_set(args: argparse.Namespace) -> int:
    """Store a freshly generated access token in the encrypted local store."""
    token = _read_token()
    if not token:
        print("No token provided; nothing was stored.", file=sys.stderr)
        return 2

    expiry = token_expiry_from_claims(token)
    client_id = args.client_id or token_client_id_from_claims(token)
    if not client_id:
        print(
            "Client ID could not be derived from the token; pass --client-id explicitly.",
            file=sys.stderr,
        )
        return 2

    if expiry is not None and expiry <= datetime.now(tz=UTC):
        print(
            f"Refusing to store: token already expired at {expiry.isoformat()}.",
            file=sys.stderr,
        )
        return 1

    try:
        path = store_dhan_credentials_dpapi(
            client_id=client_id,
            access_token=token,
            expires_at=expiry,
            runtime_root=_runtime_root(),
        )
    except (DPAPIError, ValueError) as exc:
        print(f"Failed to store credentials: {exc}", file=sys.stderr)
        return 1

    print(f"Stored encrypted credentials at {path}")
    print(f"  client id : {mask_client_id(client_id)}")
    print(f"  expires   : {expiry.isoformat() if expiry else 'unknown (no exp claim)'}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Report where credentials resolve from and how long they remain valid."""
    creds = resolve_dhan_credentials(runtime_root=_runtime_root())
    health = check_token_health(creds)
    print(f"status     : {health.status}")
    print(f"source     : {health.source}")
    print(f"client id  : {health.client_id_masked}")
    print(f"expires at : {health.expires_at or 'unknown'}")
    print(f"time left  : {_format_remaining(health.expires_in_seconds)}")
    print(f"store path : {get_credentials_path(_runtime_root())}")
    return 0 if health.is_valid else 1


def cmd_clear(args: argparse.Namespace) -> int:
    """Delete the encrypted credential file."""
    removed = clear_dhan_credentials_dpapi(runtime_root=_runtime_root())
    print("Encrypted credentials removed." if removed else "No stored credentials to remove.")
    return 0


def cmd_renew(args: argparse.Namespace) -> int:
    """Renew the active 24-hour access token via GET /v2/RenewToken."""
    from app.dhan.client import DhanRestClient
    from app.dhan.exceptions import DhanClientError

    creds = resolve_dhan_credentials(runtime_root=_runtime_root())
    if not creds:
        print("No Dhan credentials found to renew.", file=sys.stderr)
        return 1

    health = check_token_health(creds)
    if not health.is_valid:
        print(
            f"Cannot renew: current token is already {health.status}.",
            file=sys.stderr,
        )
        return 1

    client = DhanRestClient(credentials=creds)
    try:
        renewal = client.renew_token()
    except DhanClientError as exc:
        print(f"Token renewal failed: {exc}", file=sys.stderr)
        return 1

    new_token = renewal.access_token
    if not new_token:
        print("RenewToken API returned empty access token.", file=sys.stderr)
        return 1

    expiry = token_expiry_from_claims(new_token)
    client_id = renewal.client_id or creds.client_id

    try:
        path = store_dhan_credentials_dpapi(
            client_id=client_id,
            access_token=new_token,
            expires_at=expiry,
            runtime_root=_runtime_root(),
        )
    except (DPAPIError, ValueError) as exc:
        print(f"Failed to store renewed credentials: {exc}", file=sys.stderr)
        return 1

    print("Successfully renewed access token.")
    print(f"  stored at : {path}")
    print(f"  client id : {mask_client_id(client_id)}")
    print(f"  expires   : {expiry.isoformat() if expiry else 'unknown'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.dhan.token",
        description="Manage the local encrypted Dhan access token.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    set_parser = sub.add_parser("set", help="store a new access token (prompts, input hidden)")
    set_parser.add_argument(
        "--client-id",
        default=None,
        help="override the client ID instead of reading it from the token claims",
    )
    set_parser.set_defaults(func=cmd_set)

    sub.add_parser("status", help="show resolved credential source and expiry").set_defaults(
        func=cmd_status
    )
    sub.add_parser("renew", help="renew active access token for another 24 hours").set_defaults(
        func=cmd_renew
    )
    sub.add_parser("clear", help="delete the encrypted credential file").set_defaults(
        func=cmd_clear
    )
    return parser



def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
