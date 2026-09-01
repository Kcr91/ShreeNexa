"""Dhan integration package for ShreeNexa."""

from app.dhan.client import DhanRestClient
from app.dhan.credentials import (
    DhanCredentials,
    clear_dhan_credentials_dpapi,
    resolve_dhan_credentials,
    store_dhan_credentials_dpapi,
)
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanClientError,
    DhanError,
    DhanMalformedResponseError,
    DhanRateLimitError,
    DhanServerError,
    DhanTimeoutError,
)
from app.dhan.health import DhanTokenHealth, check_token_health
from app.dhan.models import (
    DhanFundLimit,
    DhanHistoricalBar,
    DhanHistoricalData,
    DhanHolding,
    DhanPosition,
    DhanProfile,
    DhanQuote,
    DhanResponseEnvelope,
)
from app.dhan.transport import (
    CassetteTransport,
    DhanTransport,
    HTTPTransport,
    MockTransport,
)

__all__ = [
    "CassetteTransport",
    "DhanAuthenticationError",
    "DhanClientError",
    "DhanCredentials",
    "DhanError",
    "DhanFundLimit",
    "DhanHistoricalBar",
    "DhanHistoricalData",
    "DhanHolding",
    "DhanMalformedResponseError",
    "DhanPosition",
    "DhanProfile",
    "DhanQuote",
    "DhanRateLimitError",
    "DhanResponseEnvelope",
    "DhanRestClient",
    "DhanServerError",
    "DhanTimeoutError",
    "DhanTokenHealth",
    "DhanTransport",
    "HTTPTransport",
    "MockTransport",
    "check_token_health",
    "clear_dhan_credentials_dpapi",
    "resolve_dhan_credentials",
    "store_dhan_credentials_dpapi",
]
