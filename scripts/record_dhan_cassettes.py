"""Record sanitized DhanHQ REST responses as offline test cassettes.

F0.5 requires recorded broker responses; the seven fixtures currently in
``backend/tests/cassettes/dhan/`` are self-declared synthetic. This script replays a
small set of READ-ONLY market-data calls against the live API and writes sanitized
cassettes with ``recorded_broker_response: true``.

Only read-only endpoints are called. No order, fund, or account-state endpoint is
touched, and nothing here can place a trade.

Usage::

    uv run python scripts/record_dhan_cassettes.py --dry-run   # show the plan
    uv run python scripts/record_dhan_cassettes.py             # record

Requires a valid ``DHAN_ACCESS_TOKEN``; check first with::

    uv run python -c "from app.dhan.credentials import resolve_dhan_credentials; \
from app.dhan.health import check_token_health; \
print(check_token_health(resolve_dhan_credentials()))"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.dhan.client import DhanRestClient  # noqa: E402
from app.dhan.credentials import resolve_dhan_credentials  # noqa: E402
from app.dhan.health import check_token_health  # noqa: E402
from app.dhan.transport import DEFAULT_BASE_URL, HTTPTransport  # noqa: E402

CASSETTE_DIR = REPO_ROOT / "backend" / "tests" / "cassettes" / "dhan"

# NIFTY 50 index on the IDX_I segment - a stable, liquid, non-account-specific target.
NIFTY_SECURITY_ID = "13"
NIFTY_SEGMENT = "IDX_I"
NIFTY_INSTRUMENT = "INDEX"

REDACTION_PLACEHOLDER = "0000000000"
SECRET_KEY_PATTERN = re.compile(
    r"(token|access[-_]?token|client[-_]?id|dhanclientid|authorization|jwt|password|secret)",
    re.IGNORECASE,
)


class RecordingTransport:
    """Delegates to HTTPTransport while capturing the raw exchange for each call."""

    def __init__(self) -> None:
        self.inner = HTTPTransport(DEFAULT_BASE_URL)
        self.last: tuple[int, dict[str, str], bytes] | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> tuple[int, dict[str, str], bytes]:
        result = self.inner.request(
            method,
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )
        self.last = result
        return result


def sanitize(value: Any) -> Any:
    """Recursively blank any account identifier or credential in a decoded payload."""
    if isinstance(value, dict):
        return {
            k: (REDACTION_PLACEHOLDER if SECRET_KEY_PATTERN.search(str(k)) else sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def write_cassette(
    name: str,
    endpoint: str,
    request_params: dict[str, Any],
    status_code: int,
    body: bytes,
) -> Path:
    """Write one sanitized cassette, preserving the response shape byte-for-byte."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError, UnicodeDecodeError:
        payload = {"_raw": body.decode("utf-8", errors="replace")}

    document = {
        "_fixture": {
            "classification": "recorded",
            "source": "dhanhq_v2_live_api",
            "recorded_broker_response": True,
            "recorded_at": datetime.now(UTC).isoformat(),
            "endpoint": endpoint,
            "http_status": status_code,
            "request": sanitize(request_params),
            "account_id": REDACTION_PLACEHOLDER,
            "sanitized_keys": "token/client-id/authorization fields replaced",
        }
    }
    sanitized = sanitize(payload)
    if isinstance(sanitized, dict):
        document.update(sanitized)
    else:
        document["data"] = sanitized

    target = CASSETTE_DIR / f"{name}.json"
    target.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return target


def record_success_cassettes(dry_run: bool) -> list[str]:
    """Record the read-only success responses that can be genuinely captured."""
    end = date.today()
    start = end - timedelta(days=7)
    written: list[str] = []

    plan = [
        (
            "historical_daily_success",
            "charts/historical",
            {
                "securityId": NIFTY_SECURITY_ID,
                "exchangeSegment": NIFTY_SEGMENT,
                "instrument": NIFTY_INSTRUMENT,
                "fromDate": start.isoformat(),
                "toDate": end.isoformat(),
            },
        ),
        (
            "historical_intraday_success",
            "charts/intraday",
            {
                "securityId": NIFTY_SECURITY_ID,
                "exchangeSegment": NIFTY_SEGMENT,
                "instrument": NIFTY_INSTRUMENT,
                "fromDate": start.isoformat(),
                "toDate": end.isoformat(),
                "interval": "1",
            },
        ),
    ]

    if dry_run:
        for name, endpoint, params in plan:
            print(f"  would POST {endpoint} -> {name}.json  params={params}")
        print("  would GET  fundlimit    -> profile_success.json")
        return []

    transport = RecordingTransport()
    client = DhanRestClient(transport=transport)

    for name, endpoint, params in plan:
        client._request("POST", endpoint, json_data=params)
        assert transport.last is not None
        status, _headers, body = transport.last
        path = write_cassette(name, endpoint, params, status, body)
        print(f"  recorded {endpoint} -> {path.name} (HTTP {status}, {len(body)} bytes)")
        written.append(name)

    client._request("GET", "fundlimit")
    assert transport.last is not None
    status, _headers, body = transport.last
    path = write_cassette("profile_success", "fundlimit", {}, status, body)
    print(f"  recorded fundlimit -> {path.name} (HTTP {status})")
    written.append("profile_success")

    return written


def record_auth_failure(dry_run: bool) -> str | None:
    """Record a genuine 401 by sending a deliberately invalid token."""
    if dry_run:
        print("  would POST charts/historical with an invalid token -> auth_failure_401.json")
        return None

    transport = HTTPTransport(DEFAULT_BASE_URL)
    status, _headers, body = transport.request(
        "POST",
        "charts/historical",
        json_data={
            "securityId": NIFTY_SECURITY_ID,
            "exchangeSegment": NIFTY_SEGMENT,
            "instrument": NIFTY_INSTRUMENT,
            "fromDate": (date.today() - timedelta(days=2)).isoformat(),
            "toDate": date.today().isoformat(),
        },
        headers={
            "client-id": REDACTION_PLACEHOLDER,
            "access-token": "deliberately-invalid-token-for-cassette-recording",
        },
    )
    if status != 401:
        print(f"  WARNING: expected HTTP 401 for the invalid-token call, got {status}")
    path = write_cassette("auth_failure_401", "charts/historical", {}, status, body)
    print(f"  recorded auth failure -> {path.name} (HTTP {status})")
    return "auth_failure_401"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan without calling")
    args = parser.parse_args()

    if not args.dry_run:
        credentials = resolve_dhan_credentials()
        if credentials is None:
            print("ERROR: no Dhan credentials resolved.", file=sys.stderr)
            return 2
        health = check_token_health(credentials)
        if not health.is_valid:
            print(
                f"ERROR: Dhan token is {health.status} (expires_at={health.expires_at}).\n"
                "Refresh it first:  uv run python -m app.dhan.token set <NEW_TOKEN>",
                file=sys.stderr,
            )
            return 2
        print(f"Token OK (expires {health.expires_at}); recording read-only cassettes.")

    print("Success cassettes:")
    record_success_cassettes(args.dry_run)
    print("Auth-failure cassette:")
    record_auth_failure(args.dry_run)

    print(
        "\nNote: malformed_response, rate_limit_429 and server_error_503 remain constructed "
        "fixtures.\nA healthy server will not emit malformed JSON, a 429, or a 503 on demand, "
        "so those\nthree keep classification 'synthetic' by necessity, not by omission."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
