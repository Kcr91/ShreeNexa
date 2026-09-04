"""Unit tests for DhanBroker safety feature gates, static IP preflight, and timeout handling."""

from __future__ import annotations

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.exceptions import DhanTimeoutError
from app.dhan.orders import (
    DhanOrderModifyRequest,
    DhanOrderRequest,
    DhanSliceOrderRequest,
    ExchangeSegment,
    OrderStatus,
    OrderType,
    OrderValidity,
    ProductType,
    TransactionType,
)
from app.dhan.transport import MockTransport
from app.engine.broker import (
    DhanBroker,
    LiveTradingDisabledError,
    StaticIPMismatchError,
)
from pydantic import SecretStr


@pytest.fixture
def test_credentials() -> DhanCredentials:
    return DhanCredentials(
        client_id="1100000000",
        access_token=SecretStr("test_token_secret"),
        source="environment",
    )


@pytest.fixture
def sample_order_request() -> DhanOrderRequest:
    return DhanOrderRequest(
        transactionType=TransactionType.BUY,
        exchangeSegment=ExchangeSegment.NSE_EQ,
        productType=ProductType.CNC,
        orderType=OrderType.LIMIT,
        validity=OrderValidity.DAY,
        securityId="1333",
        quantity=10,
        price=1250.0,
        correlationId="NX-TEST-001",
    )


def test_dhan_broker_disabled_by_default(
    test_credentials: DhanCredentials, sample_order_request: DhanOrderRequest
) -> None:
    mock_transport = MockTransport()
    client = DhanRestClient(credentials=test_credentials, transport=mock_transport)
    broker = DhanBroker(client=client)

    # Invariant: Disabled by default
    assert broker.is_live_enabled is False

    # Placing order blocked
    with pytest.raises(LiveTradingDisabledError, match="Live trading is disabled by default"):
        broker.place_order(sample_order_request)

    # Sliced order blocked
    slice_req = DhanSliceOrderRequest(
        transactionType=TransactionType.BUY,
        exchangeSegment=ExchangeSegment.NSE_FNO,
        securityId="45231",
        quantity=3600,
        price=100.0,
    )
    with pytest.raises(LiveTradingDisabledError):
        broker.place_sliced_order(slice_req)

    # Modify blocked
    mod_req = DhanOrderModifyRequest(
        orderId="ORD123",
        orderType=OrderType.LIMIT,
        price=1200.0,
    )
    with pytest.raises(LiveTradingDisabledError):
        broker.modify_order(mod_req)

    # Cancel blocked
    with pytest.raises(LiveTradingDisabledError):
        broker.cancel_order("ORD123")


def test_dhan_broker_readonly_allowed_when_disabled(test_credentials: DhanCredentials) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "orders/ORD123",
        status_code=200,
        body={
            "orderId": "ORD123",
            "orderStatus": "TRADED",
            "transactionType": "BUY",
            "exchangeSegment": "NSE_EQ",
            "productType": "CNC",
            "orderType": "LIMIT",
            "securityId": "1333",
            "quantity": 10,
            "tradedQuantity": 10,
            "averageTradedPrice": 1250.0,
        },
    )
    client = DhanRestClient(credentials=test_credentials, transport=mock_transport)
    broker = DhanBroker(client=client, enable_live_trading=False)

    # Read-only query is permitted
    detail = broker.get_order_by_id("ORD123")
    assert detail.order_id == "ORD123"
    assert detail.order_status == OrderStatus.TRADED


def test_dhan_broker_static_ip_mismatch_blocks(
    test_credentials: DhanCredentials, sample_order_request: DhanOrderRequest
) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "ip/getIP",
        status_code=200,
        body={
            "primaryIP": "13.234.56.78",
            "secondaryIP": "103.21.244.10",
        },
    )
    client = DhanRestClient(credentials=test_credentials, transport=mock_transport)

    # Enabled live trading but outbound IP mismatches
    broker = DhanBroker(
        client=client,
        enable_live_trading=True,
        override_public_ip="192.168.1.100",  # Unwhitelisted
    )

    with pytest.raises(StaticIPMismatchError, match="does not match any whitelisted Dhan IP"):
        broker.place_order(sample_order_request)


def test_dhan_broker_live_order_success(
    test_credentials: DhanCredentials, sample_order_request: DhanOrderRequest
) -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "ip/getIP",
        status_code=200,
        body={
            "primaryIP": "13.234.56.78",
            "secondaryIP": "103.21.244.10",
        },
    )
    mock_transport.register(
        "orders",
        status_code=200,
        body={
            "orderId": "ORD_LIVE_001",
            "orderStatus": "PENDING",
        },
    )
    client = DhanRestClient(credentials=test_credentials, transport=mock_transport)

    # Matches primary IP (Lightsail)
    broker = DhanBroker(
        client=client,
        enable_live_trading=True,
        override_public_ip="13.234.56.78",
    )

    resp = broker.place_order(sample_order_request)
    assert resp.order_id == "ORD_LIVE_001"
    assert resp.order_status == OrderStatus.PENDING


def test_dhan_broker_timeout_triggers_pending_confirmation(
    test_credentials: DhanCredentials,
    sample_order_request: DhanOrderRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_transport = MockTransport()
    client = DhanRestClient(credentials=test_credentials, transport=mock_transport)

    def _raise_timeout(*args: object, **kwargs: object) -> None:
        raise DhanTimeoutError("Gateway timed out waiting for exchange ack")

    monkeypatch.setattr(client, "place_order", _raise_timeout)

    broker = DhanBroker(
        client=client,
        enable_live_trading=True,
        enforce_static_ip=False,
    )

    # Must NOT raise or retry blindly; must return PENDING_BROKER_CONFIRMATION
    resp = broker.place_order(sample_order_request)
    assert resp.order_id is None
    assert resp.order_status == OrderStatus.PENDING_BROKER_CONFIRMATION


def test_dhan_broker_read_only_methods_are_sole_unguarded_endpoints() -> None:
    """QA-13 Invariant: Assert that get_order_by_id, get_order_by_correlation_id,

    and reconcile_pending_order are the ONLY public methods on DhanBroker that access
    self.client without calling _verify_preflight_safety.
    Mutating methods (place_order, modify_order, cancel_order, place_sliced_order)
    strictly call _verify_preflight_safety.
    """
    import ast
    import inspect

    source = inspect.getsource(DhanBroker)
    tree = ast.parse(source)
    broker_class = tree.body[0]
    assert isinstance(broker_class, ast.ClassDef)

    methods_with_client: dict[str, bool] = {}

    for node in broker_class.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            calls_preflight = False
            calls_client = False
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    func = subnode.func
                    if isinstance(func, ast.Attribute) and func.attr == "_verify_preflight_safety":
                        calls_preflight = True
                    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
                        if func.value.attr == "client":
                            calls_client = True

            if calls_client:
                methods_with_client[node.name] = calls_preflight

    # Mutating methods MUST invoke _verify_preflight_safety
    mutating_methods = {"place_order", "modify_order", "cancel_order", "place_sliced_order"}
    for method in mutating_methods:
        assert method in methods_with_client, f"Expected {method} to access client"
        assert methods_with_client[method] is True, f"{method} must call _verify_preflight_safety"

    # Only read-only query/reconciliation methods are exempt from preflight gate
    unguarded = [m for m, preflight in methods_with_client.items() if not preflight]
    assert sorted(unguarded) == [
        "get_order_by_correlation_id",
        "get_order_by_id",
        "reconcile_pending_order",
    ], f"Unexpected unguarded broker methods: {unguarded}"
