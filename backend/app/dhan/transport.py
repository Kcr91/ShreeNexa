"""Injectable HTTP and offline cassette transports for Dhan REST API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from app.config import redact_text
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanClientError,
    DhanError,
    DhanRateLimitError,
    DhanServerError,
    DhanTimeoutError,
)

DEFAULT_BASE_URL = "https://api.dhan.co/v2"


class DhanTransport(Protocol):
    """Protocol for sending HTTP requests to DhanHQ REST API."""

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> tuple[int, dict[str, str], bytes]: ...


class HTTPTransport:
    """Standard network transport using urllib with timeouts and error translation."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

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
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"

        body_bytes: bytes | None = None
        req_headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)

        if json_data is not None:
            body_bytes = json.dumps(json_data).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=body_bytes,
            headers=req_headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = int(response.status)
                resp_headers = {k: v for k, v in response.headers.items()}
                content = response.read()
                return status_code, resp_headers, content
        except urllib.error.HTTPError as err:
            err_content = err.read()
            err_headers = {k: v for k, v in err.headers.items()} if err.headers else {}
            return int(err.code), err_headers, err_content
        except TimeoutError as err:
            raise DhanTimeoutError(f"Request to {path} timed out after {timeout}s") from err
        except urllib.error.URLError as err:
            if isinstance(err.reason, TimeoutError):
                raise DhanTimeoutError(f"Request to {path} timed out: {err.reason}") from err
            raise DhanServerError(f"Connection error reaching {path}: {err.reason}") from err


class CassetteTransport:
    """Deterministic offline transport replaying Dhan-shaped JSON fixtures."""

    def __init__(self, cassette_dir: Path | str) -> None:
        self.cassette_dir = Path(cassette_dir)
        self.routes: dict[str, Path] = {}
        self._load_routes()

    def _load_routes(self) -> None:
        if not self.cassette_dir.is_dir():
            return
        for file in self.cassette_dir.glob("*.json"):
            stem = file.stem
            self.routes[stem] = file

    def register_cassette(self, endpoint_key: str, file_path: Path) -> None:
        """Register a specific cassette file for an endpoint key."""
        self.routes[endpoint_key] = file_path

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
        clean_path = path.strip("/").replace("/", "_")
        key = clean_path

        # Match registered cassette keys
        matched_file: Path | None = None
        for candidate_key, file_path in self.routes.items():
            if candidate_key in key or key in candidate_key:
                matched_file = file_path
                break

        if not matched_file:
            # Check for fallback profile/charts
            if "profile" in key or "fund" in key:
                matched_file = self.routes.get("profile_success")
            elif "historical" in key:
                matched_file = self.routes.get("historical_daily_success")
            elif "intraday" in key:
                matched_file = self.routes.get("historical_intraday_success")

        if not matched_file or not matched_file.is_file():
            raise FileNotFoundError(f"No cassette fixture found for {method} {path} (key: {key})")

        content = matched_file.read_bytes()
        status_code = 200
        if "401" in matched_file.name or "auth_failure" in matched_file.name:
            status_code = 401
        elif "429" in matched_file.name or "rate_limit" in matched_file.name:
            status_code = 429
        elif "503" in matched_file.name or "server_error" in matched_file.name:
            status_code = 503

        return status_code, {"Content-Type": "application/json"}, content


class MockTransport:
    """Programmatic mock transport for simulating network conditions and edge cases."""

    def __init__(self) -> None:
        self.responses: dict[str, tuple[int, dict[str, str], bytes]] = {}
        self.exceptions: dict[str, Exception] = {}

    def register(
        self,
        path_substr: str,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes | str | dict[str, Any] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Register a mock response or exception for a path substring."""
        if exception:
            self.exceptions[path_substr] = exception
            return

        resp_headers = headers or {"Content-Type": "application/json"}
        if isinstance(body, dict | list):
            content = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            content = body.encode("utf-8")
        elif isinstance(body, bytes):
            content = body
        else:
            content = b"{}"

        self.responses[path_substr] = (status_code, resp_headers, content)

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
        for pattern, exc in self.exceptions.items():
            if pattern in path:
                raise exc

        for pattern, resp in self.responses.items():
            if pattern in path:
                return resp

        # Default fallback
        return 200, {"Content-Type": "application/json"}, b'{"status":"success","data":{}}'


def raise_for_status(status_code: int, raw_body: bytes) -> None:
    """Translate non-2xx HTTP status codes and error JSON into typed Dhan errors."""
    if 200 <= status_code < 300:
        return

    text = raw_body.decode("utf-8", errors="replace")
    error_code: str | None = None
    error_type: str | None = None
    message = f"HTTP {status_code} error from Dhan API"

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            remarks = data.get("remarks") or data.get("message")
            if remarks:
                message = str(remarks)
            error_code = data.get("errorCode")
            error_type = data.get("errorType")
    except json.JSONDecodeError:
        message = f"HTTP {status_code}: {redact_text(text)}"

    if status_code == 401:
        raise DhanAuthenticationError(
            message,
            status_code=status_code,
            error_code=error_code,
            error_type=error_type,
        )
    if status_code == 429:
        raise DhanRateLimitError(
            message,
            status_code=status_code,
            error_code=error_code,
            error_type=error_type,
        )
    if status_code in (500, 502, 503, 504):
        raise DhanServerError(
            message,
            status_code=status_code,
            error_code=error_code,
            error_type=error_type,
        )
    if status_code in (400, 404, 422):
        raise DhanClientError(
            message,
            status_code=status_code,
            error_code=error_code,
            error_type=error_type,
        )

    raise DhanError(
        message,
        status_code=status_code,
        error_code=error_code,
        error_type=error_type,
    )
