"""Typed DhanHQ v2 REST API client implementation."""

from __future__ import annotations

import json
from typing import Any

from app.config import mask_client_id
from app.dhan.credentials import DhanCredentials, resolve_dhan_credentials
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanMalformedResponseError,
)
from app.dhan.limiter import TokenBucket, get_dhan_rate_limiter
from app.dhan.limits_config import get_category_for_endpoint
from app.dhan.models import (
    DhanFundLimit,
    DhanHistoricalData,
    DhanHolding,
    DhanPosition,
    DhanProfile,
    DhanQuote,
    DhanResponseEnvelope,
)
from app.dhan.transport import (
    DhanTransport,
    HTTPTransport,
    raise_for_status,
)


class DhanRestClient:
    """Fully typed REST client for DhanHQ v2 API with injectable transport and rate limiter."""

    def __init__(
        self,
        credentials: DhanCredentials | None = None,
        transport: DhanTransport | None = None,
        limiter: TokenBucket | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.credentials = credentials or resolve_dhan_credentials()
        self.transport: DhanTransport = transport or HTTPTransport()
        self.limiter: TokenBucket = limiter or get_dhan_rate_limiter()
        self.timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        """Generate authenticated headers without leaking tokens in memory."""
        if not self.credentials:
            raise DhanAuthenticationError("No Dhan credentials configured")
        return {
            "client-id": self.credentials.client_id,
            "access-token": self.credentials.get_token_value(),
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Execute request, validate status code, and parse response JSON."""
        category = get_category_for_endpoint(method, path)
        self.limiter.acquire(category, timeout=self.timeout)

        headers = self._get_headers()
        status_code, _resp_headers, raw_body = self.transport.request(
            method,
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=self.timeout,
        )

        raise_for_status(status_code, raw_body)

        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            raise DhanMalformedResponseError(
                f"Failed to parse JSON response from {path}: {err}",
                status_code=status_code,
            ) from err

        if isinstance(parsed, dict) and "status" in parsed:
            envelope = DhanResponseEnvelope.model_validate(parsed)
            if envelope.status.lower() == "failure":
                remarks = envelope.remarks or "Dhan API returned failure status"
                raise DhanMalformedResponseError(
                    remarks,
                    status_code=status_code,
                    error_code=envelope.error_code,
                    error_type=envelope.error_type,
                )
            return envelope.data if envelope.data is not None else parsed

        return parsed

    def get_fund_limits(self) -> DhanFundLimit:
        """Fetch account fund and margin limits."""
        data = self._request("GET", "fundlimit")
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for fundlimit")
        if not any(
            k in data
            for k in ("availabelBalance", "sodLimit", "dhanClientId", "withdrawableBalance")
        ):
            raise DhanMalformedResponseError("Missing expected fund limit fields in response")
        return DhanFundLimit.model_validate(data)

    def get_profile(self) -> DhanProfile:
        """Fetch account profile metadata and limits."""
        fund_limit = self.get_fund_limits()
        client_id = fund_limit.client_id or (self.credentials.client_id if self.credentials else "")
        return DhanProfile(
            client_id=client_id,
            active=True,
            fund_limit=fund_limit,
        )

    def get_historical_daily(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
    ) -> DhanHistoricalData:
        """Fetch historical daily OHLCV bars."""
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment.upper(),
            "instrument": instrument_type.upper(),
            "fromDate": from_date,
            "toDate": to_date,
        }
        data = self._request("POST", "charts/historical", json_data=payload)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for charts/historical")
        return DhanHistoricalData.model_validate(data)

    def get_historical_intraday(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
        interval: int = 1,
    ) -> DhanHistoricalData:
        """Fetch historical minute intraday OHLCV bars."""
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment.upper(),
            "instrument": instrument_type.upper(),
            "fromDate": from_date,
            "toDate": to_date,
            "interval": str(interval),
        }
        data = self._request("POST", "charts/intraday", json_data=payload)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for charts/intraday")
        return DhanHistoricalData.model_validate(data)

    def get_quote(self, security_id: str, exchange_segment: str) -> DhanQuote:
        """Fetch snapshot quote for a security."""
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment.upper(),
        }
        data = self._request("POST", "marketfeed/quote", json_data=payload)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for marketfeed/quote")
        return DhanQuote.model_validate(data)

    def get_holdings(self) -> list[DhanHolding]:
        """Fetch account equity holdings."""
        data = self._request("GET", "holdings")
        if isinstance(data, list):
            return [DhanHolding.model_validate(item) for item in data]
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            return [DhanHolding.model_validate(item) for item in data["data"]]
        return []

    def get_positions(self) -> list[DhanPosition]:
        """Fetch open and closed trading positions."""
        data = self._request("GET", "positions")
        if isinstance(data, list):
            return [DhanPosition.model_validate(item) for item in data]
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            return [DhanPosition.model_validate(item) for item in data["data"]]
        return []

    def __repr__(self) -> str:
        cid = mask_client_id(self.credentials.client_id) if self.credentials else "[NONE]"
        return (
            f"DhanRestClient(client_id={cid!r}, "
            f"transport={self.transport.__class__.__name__}, "
            f"timeout={self.timeout})"
        )

    def __str__(self) -> str:
        return self.__repr__()
