"""Unit tests for the bounded Dhan retry policy and limiter-counted retry attempts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanClientError,
    DhanRateLimitError,
    DhanServerError,
    DhanTimeoutError,
)
from app.dhan.retry import (
    MAX_RETRY_AFTER_SECONDS,
    RetryPolicy,
    parse_retry_after,
)
from pydantic import SecretStr

OK_RESPONSE: tuple[int, dict[str, str], bytes] = (
    200,
    {"Content-Type": "application/json"},
    b'{"status":"success","data":{"ok":1}}',
)


class CountingLimiter:
    """Token bucket stub recording every acquire call."""

    def __init__(self) -> None:
        self.acquisitions: list[str] = []

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        self.acquisitions.append(category)
        return 0.0

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        self.acquisitions.append(category)
        return True

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        return {"category": category, "used": len(self.acquisitions)}


class SequenceTransport:
    """Transport replaying a scripted sequence of responses or raising exceptions.

    The last scripted item repeats, so a single entry models a persistent failure.
    """

    def __init__(self, script: list[Any]) -> None:
        self.script = list(script)
        self.calls = 0

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
        item = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, tuple)
        return item


def build_client(
    transport: SequenceTransport,
    limiter: CountingLimiter,
    policy: RetryPolicy | None = None,
) -> tuple[DhanRestClient, list[float]]:
    """Return a client wired to stubs, plus the list capturing every sleep duration."""
    slept: list[float] = []
    client = DhanRestClient(
        credentials=DhanCredentials(
            client_id="1000000000",
            access_token=SecretStr("test-token"),
        ),
        transport=transport,
        limiter=limiter,
        retry_policy=policy or RetryPolicy(max_attempts=3, base_delay_seconds=0.01),
        sleep=slept.append,
    )
    return client, slept


class TestRetryPolicyValidation:
    def test_rejects_invalid_configuration(self) -> None:
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)
        with pytest.raises(ValueError, match="base_delay_seconds"):
            RetryPolicy(base_delay_seconds=0.0)
        with pytest.raises(ValueError, match="max_delay_seconds"):
            RetryPolicy(base_delay_seconds=5.0, max_delay_seconds=1.0)
        with pytest.raises(ValueError, match="jitter_ratio"):
            RetryPolicy(jitter_ratio=1.5)


class TestRetryClassification:
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_transient_statuses_retry(self, status: int) -> None:
        assert RetryPolicy(max_attempts=3).should_retry(1, status) is True

    @pytest.mark.parametrize("status", [200, 201, 400, 401, 404, 422])
    def test_terminal_statuses_do_not_retry(self, status: int) -> None:
        assert RetryPolicy(max_attempts=3).should_retry(1, status) is False

    def test_final_attempt_never_retries(self) -> None:
        assert RetryPolicy(max_attempts=3).should_retry(3, 503) is False


class TestBackoffTiming:
    def test_delay_grows_exponentially_and_caps(self) -> None:
        policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=8.0, jitter_ratio=0.0)
        assert policy.compute_delay(1) == pytest.approx(1.0)
        assert policy.compute_delay(2) == pytest.approx(2.0)
        assert policy.compute_delay(3) == pytest.approx(4.0)
        assert policy.compute_delay(4) == pytest.approx(8.0)
        assert policy.compute_delay(9) == pytest.approx(8.0)

    def test_jitter_stays_within_configured_ratio(self) -> None:
        policy = RetryPolicy(base_delay_seconds=4.0, max_delay_seconds=4.0, jitter_ratio=0.25)
        for _ in range(200):
            assert 3.0 <= policy.compute_delay(1) <= 5.0

    def test_retry_after_overrides_backoff(self) -> None:
        policy = RetryPolicy(base_delay_seconds=1.0, jitter_ratio=0.0)
        assert policy.compute_delay(1, retry_after=7.5) == pytest.approx(7.5)

    def test_retry_after_is_bounded_and_never_negative(self) -> None:
        policy = RetryPolicy(base_delay_seconds=1.0, jitter_ratio=0.0)
        assert policy.compute_delay(1, retry_after=9999.0) == pytest.approx(MAX_RETRY_AFTER_SECONDS)
        assert policy.compute_delay(1, retry_after=-3.0) == pytest.approx(0.0)


class TestParseRetryAfter:
    def test_absent_or_blank_returns_none(self) -> None:
        assert parse_retry_after(None) is None
        assert parse_retry_after({}) is None
        assert parse_retry_after({"Retry-After": "   "}) is None

    def test_delta_seconds_and_case_insensitive_lookup(self) -> None:
        assert parse_retry_after({"Retry-After": "12"}) == pytest.approx(12.0)
        assert parse_retry_after({"retry-after": "0.5"}) == pytest.approx(0.5)

    def test_http_date_form(self) -> None:
        now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
        header = (now + timedelta(seconds=30)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        assert parse_retry_after({"Retry-After": header}, now=now) == pytest.approx(30.0, abs=1.0)

    def test_past_http_date_clamps_to_zero(self) -> None:
        now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
        header = (now - timedelta(seconds=60)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        assert parse_retry_after({"Retry-After": header}, now=now) == pytest.approx(0.0)

    def test_unparseable_value_falls_back_to_none(self) -> None:
        assert parse_retry_after({"Retry-After": "soon-ish"}) is None


class TestClientRetryIntegration:
    def test_transient_503_then_success(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([(503, {}, b'{"remarks":"upstream down"}'), OK_RESPONSE])
        client, _ = build_client(transport, limiter)

        assert client._request("GET", "fundlimit") == {"ok": 1}
        assert transport.calls == 2

    def test_every_attempt_consumes_a_limiter_token(self) -> None:
        """Retries must be counted against the per-day budget, not slip past it."""
        limiter = CountingLimiter()
        transport = SequenceTransport([(503, {}, b"{}"), (503, {}, b"{}"), OK_RESPONSE])
        client, _ = build_client(transport, limiter)

        client._request("GET", "fundlimit")

        assert transport.calls == 3
        assert len(limiter.acquisitions) == 3, (
            "each HTTP attempt must acquire its own token; otherwise retried calls "
            "silently overrun the documented per-day budget"
        )

    def test_exhausted_attempts_raise_typed_rate_limit_error(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([(429, {}, b'{"remarks":"slow down"}')])
        client, _ = build_client(transport, limiter)

        with pytest.raises(DhanRateLimitError):
            client._request("GET", "fundlimit")

        assert transport.calls == 3
        assert len(limiter.acquisitions) == 3

    def test_auth_failure_is_terminal(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([(401, {}, b'{"remarks":"Invalid Token"}')])
        client, _ = build_client(transport, limiter)

        with pytest.raises(DhanAuthenticationError):
            client._request("GET", "fundlimit")

        assert transport.calls == 1, "401 is terminal; retrying only wastes budget"

    def test_client_error_is_terminal(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([(422, {}, b'{"remarks":"bad parameter"}')])
        client, _ = build_client(transport, limiter)

        with pytest.raises(DhanClientError):
            client._request("GET", "fundlimit")

        assert transport.calls == 1

    def test_timeout_exception_is_retried(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([DhanTimeoutError("timed out"), OK_RESPONSE])
        client, _ = build_client(transport, limiter)

        assert client._request("GET", "fundlimit") == {"ok": 1}
        assert transport.calls == 2

    def test_persistent_timeout_propagates_after_exhaustion(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([DhanTimeoutError("timed out")])
        client, _ = build_client(transport, limiter)

        with pytest.raises(DhanTimeoutError):
            client._request("GET", "fundlimit")

        assert transport.calls == 3
        assert len(limiter.acquisitions) == 3

    def test_connection_error_is_retried(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([DhanServerError("connection reset"), OK_RESPONSE])
        client, _ = build_client(transport, limiter)

        assert client._request("GET", "fundlimit") == {"ok": 1}
        assert transport.calls == 2

    def test_retry_after_header_drives_the_wait(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([(429, {"Retry-After": "3"}, b"{}"), OK_RESPONSE])
        client, slept = build_client(transport, limiter)

        client._request("GET", "fundlimit")

        assert slept == [pytest.approx(3.0)]

    def test_success_path_never_sleeps(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([OK_RESPONSE])
        client, slept = build_client(transport, limiter)

        client._request("GET", "fundlimit")

        assert slept == []
        assert len(limiter.acquisitions) == 1

    def test_single_attempt_policy_disables_retry(self) -> None:
        limiter = CountingLimiter()
        transport = SequenceTransport([(503, {}, b"{}")])
        client, slept = build_client(transport, limiter, policy=RetryPolicy(max_attempts=1))

        with pytest.raises(DhanServerError):
            client._request("GET", "fundlimit")

        assert transport.calls == 1
        assert slept == []
