"""Typed exception hierarchy and retryability classifications for Dhan REST API."""

from __future__ import annotations

from typing import Any

from app.config import redact_text


class DhanError(Exception):
    """Base class for all DhanHQ API client exceptions."""

    is_retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        error_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.raw_message = message
        self.message = redact_text(message)
        self.status_code = status_code
        self.error_code = error_code
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, "
            f"status_code={self.status_code}, error_code={self.error_code!r}, "
            f"is_retryable={self.is_retryable})"
        )

    def __str__(self) -> str:
        code_str = f" [{self.error_code}]" if self.error_code else ""
        status_str = f" (HTTP {self.status_code})" if self.status_code else ""
        return f"{self.message}{code_str}{status_str}"


class DhanAuthenticationError(DhanError):
    """Raised when authentication fails (HTTP 401, invalid token, or expired token).

    Non-retryable: Requires credential update.
    """

    is_retryable: bool = False


class DhanRateLimitError(DhanError):
    """Raised when Dhan rate limits are exceeded (HTTP 429).

    Retryable: Backoff and retry via rate-limit bucket.
    """

    is_retryable: bool = True


class DhanServerError(DhanError):
    """Raised when Dhan returns a 5xx server error (500, 502, 503, 504).

    Retryable: Temporary upstream or gateway error.
    """

    is_retryable: bool = True


class DhanTimeoutError(DhanError):
    """Raised when a Dhan HTTP request times out.

    Retryable: Transient network latency.
    """

    is_retryable: bool = True


class DhanClientError(DhanError):
    """Raised for client-side request errors (HTTP 400, 404, 422).

    Non-retryable: Bad request parameters.
    """

    is_retryable: bool = False


class DhanMalformedResponseError(DhanError):
    """Raised when Dhan response is unparseable JSON or violates expected schema.

    Non-retryable: Unexpected response shape.
    """

    is_retryable: bool = False
