"""Typed DhanHQ v2 REST API client implementation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.config import mask_client_id
from app.dhan.credentials import DhanCredentials, resolve_dhan_credentials
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanMalformedResponseError,
    DhanRateLimitError,
)
from app.dhan.limiter import TokenBucket, get_dhan_rate_limiter
from app.dhan.limits_config import get_category_for_endpoint
from app.dhan.models import (
    DhanFundLimit,
    DhanHistoricalData,
    DhanHolding,
    DhanIPConfig,
    DhanKillSwitchStatus,
    DhanMultiMarginResponse,
    DhanMultiMarginScripItem,
    DhanPosition,
    DhanProfile,
    DhanQuote,
    DhanResponseEnvelope,
    DhanTokenRenewalResponse,
)
from app.dhan.orders import (
    DhanOrderCancelResponse,
    DhanOrderDetail,
    DhanOrderModifyRequest,
    DhanOrderRequest,
    DhanOrderResponse,
    DhanSliceOrderRequest,
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
        self._order_modification_counts: dict[str, int] = {}

    def _get_headers(self) -> dict[str, str]:
        """Generate authenticated headers without leaking tokens in memory."""
        if not self.credentials:
            raise DhanAuthenticationError("No Dhan credentials configured")
        return {
            "client-id": self.credentials.client_id,
            "access-token": self.credentials.get_token_value(),
            "dhanClientId": self.credentials.client_id,
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
        if category == "option_chain":
            underlying = None
            expiry = None
            if json_data:
                underlying = (
                    json_data.get("UnderlyingScrip")
                    or json_data.get("underlying")
                    or json_data.get("securityId")
                )
                expiry = (
                    json_data.get("Expiry")
                    or json_data.get("expiry")
                    or json_data.get("expiryDate")
                )
            elif params:
                underlying = (
                    params.get("UnderlyingScrip")
                    or params.get("underlying")
                    or params.get("securityId")
                )
                expiry = params.get("Expiry") or params.get("expiry") or params.get("expiryDate")
            if underlying:
                suffix = f"{underlying}:{expiry}" if expiry else str(underlying)
                category = f"option_chain:{suffix}"

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

        if not raw_body or not raw_body.strip():
            return {}

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

    def renew_token(self) -> DhanTokenRenewalResponse:
        """Renew an active 24-hour access token via GET /v2/RenewToken."""
        data = self._request("GET", "RenewToken")
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for RenewToken")
        return DhanTokenRenewalResponse.model_validate(data)

    def get_ip_config(self) -> DhanIPConfig:
        """Fetch currently configured primary and secondary static IPs via GET /v2/ip/getIP."""
        data = self._request("GET", "ip/getIP")
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for ip/getIP")
        return DhanIPConfig.model_validate(data)

    def calculate_multi_margin(
        self,
        scrip_list: Sequence[dict[str, Any] | DhanMultiMarginScripItem],
        include_position: bool = False,
        include_order: bool = False,
    ) -> DhanMultiMarginResponse:
        """Calculate combined margin with hedge benefits via POST /v2/margincalculator/multi."""
        cid = self.credentials.client_id if self.credentials else ""
        serialized_scrips = [
            item.model_dump(by_alias=True) if isinstance(item, DhanMultiMarginScripItem) else item
            for item in scrip_list
        ]
        payload = {
            "dhanClientId": cid,
            "includePosition": include_position,
            "includeOrder": include_order,
            "scripList": serialized_scrips,
        }
        data = self._request("POST", "margincalculator/multi", json_data=payload)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError(
                "Expected dictionary payload for margincalculator/multi"
            )
        return DhanMultiMarginResponse.model_validate(data)

    def exit_all_positions(self) -> bool:
        """Exit all active positions and cancel open orders via DELETE /v2/positions."""
        self._request("DELETE", "positions")
        return True

    def get_kill_switch_status(self) -> DhanKillSwitchStatus:
        """Query trading account kill switch status via GET /v2/killswitch."""
        data = self._request("GET", "killswitch")
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for killswitch")
        return DhanKillSwitchStatus.model_validate(data)

    def manage_kill_switch(self, activate: bool = True) -> DhanKillSwitchStatus:
        """Activate or deactivate account kill switch via POST /v2/killswitch."""
        status_val = "ACTIVATE" if activate else "DEACTIVATE"
        data = self._request("POST", "killswitch", params={"killSwitchStatus": status_val})
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for killswitch")
        return DhanKillSwitchStatus.model_validate(data)

    def place_order(self, order: DhanOrderRequest) -> DhanOrderResponse:
        """Place a new order via POST /v2/orders (requires Static IP whitelisting)."""
        cid = self.credentials.client_id if self.credentials else ""
        payload = order.to_api_payload(client_id=cid)
        data = self._request("POST", "orders", json_data=payload)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError("Expected dictionary payload for orders")
        return DhanOrderResponse.model_validate(data)

    def modify_order(self, modification: DhanOrderModifyRequest) -> DhanOrderResponse:
        """Modify a pending order via PUT /v2/orders/{orderId} (requires Static IP)."""
        current_mods = self._order_modification_counts.get(modification.order_id, 0)
        if current_mods >= 25:
            raise DhanRateLimitError(
                f"Order {modification.order_id} has exceeded maximum allowed "
                "modifications (25 cap)",
                details={"order_id": modification.order_id, "modification_count": current_mods},
            )

        cid = self.credentials.client_id if self.credentials else ""
        payload = modification.to_api_payload(client_id=cid)
        endpoint = f"orders/{modification.order_id}"
        data = self._request("PUT", endpoint, json_data=payload)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError(f"Expected dictionary payload for {endpoint}")
        self._order_modification_counts[modification.order_id] = current_mods + 1
        return DhanOrderResponse.model_validate(data)

    def cancel_order(self, order_id: str) -> DhanOrderCancelResponse:
        """Cancel a pending order via DELETE /v2/orders/{orderId} (requires Static IP)."""
        endpoint = f"orders/{order_id}"
        data = self._request("DELETE", endpoint)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError(f"Expected dictionary payload for {endpoint}")
        return DhanOrderCancelResponse.model_validate(data)

    def place_sliced_order(self, slice_order: DhanSliceOrderRequest) -> list[DhanOrderResponse]:
        """Place order with slicing for freeze limits via POST /v2/orders/slicing."""
        cid = self.credentials.client_id if self.credentials else ""
        payload = slice_order.to_api_payload(client_id=cid)
        data = self._request("POST", "orders/slicing", json_data=payload)
        if isinstance(data, list):
            return [
                DhanOrderResponse.model_validate(item) for item in data if isinstance(item, dict)
            ]
        if isinstance(data, dict):
            return [DhanOrderResponse.model_validate(data)]
        raise DhanMalformedResponseError("Expected list or dictionary payload for orders/slicing")

    def get_order_by_id(self, order_id: str) -> DhanOrderDetail:
        """Retrieve order details by order ID via GET /v2/orders/{order-id}."""
        endpoint = f"orders/{order_id}"
        data = self._request("GET", endpoint)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError(f"Expected dictionary payload for {endpoint}")
        return DhanOrderDetail.model_validate(data)

    def get_order_by_correlation_id(self, correlation_id: str) -> DhanOrderDetail:
        """Retrieve order details by correlation ID via GET /v2/orders/external/{correlation-id}."""
        endpoint = f"orders/external/{correlation_id}"
        data = self._request("GET", endpoint)
        if not isinstance(data, dict):
            raise DhanMalformedResponseError(f"Expected dictionary payload for {endpoint}")
        return DhanOrderDetail.model_validate(data)

    def get_order_list(self) -> list[DhanOrderDetail]:
        """Retrieve order book via GET /v2/orders."""
        data = self._request("GET", "orders")
        if not isinstance(data, list):
            raise DhanMalformedResponseError("Expected list payload for orders")
        return [DhanOrderDetail.model_validate(item) for item in data if isinstance(item, dict)]

    def __repr__(self) -> str:
        cid = mask_client_id(self.credentials.client_id) if self.credentials else "[NONE]"
        return (
            f"DhanRestClient(client_id={cid!r}, "
            f"transport={self.transport.__class__.__name__}, "
            f"timeout={self.timeout})"
        )

    def __str__(self) -> str:
        return self.__repr__()
