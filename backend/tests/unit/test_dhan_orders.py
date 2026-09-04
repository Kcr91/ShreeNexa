"""Unit tests for typed Dhan order models, validation, and slicing logic."""

from __future__ import annotations

import pytest
from app.dhan.orders import (
    DhanOrderModifyRequest,
    DhanOrderRequest,
    DhanOrderResponse,
    DhanSliceOrderRequest,
    DhanSliceOrderResponse,
    ExchangeSegment,
    OrderStatus,
    OrderType,
    OrderValidity,
    ProductType,
    TransactionType,
    calculate_order_slices,
    generate_correlation_id,
    get_freeze_limit,
)
from pydantic import ValidationError


def test_generate_correlation_id() -> None:
    import re

    cid1 = generate_correlation_id()
    cid2 = generate_correlation_id()
    assert cid1 != cid2
    assert len(cid1) <= 25  # ADR-0007 25-character cap
    assert cid1.startswith("NX-")
    assert re.match(r"^[a-zA-Z0-9_-]+$", cid1)

    # With strategy_id
    cid_strat = generate_correlation_id(prefix="NX", strategy_id="alpha_momentum")
    assert len(cid_strat) <= 25
    assert cid_strat.startswith("NX-alpha_") or "alpha" in cid_strat
    assert re.match(r"^[a-zA-Z0-9_-]+$", cid_strat)

    # With very long strategy_id
    cid_long = generate_correlation_id(
        prefix="NEXA", strategy_id="SUPER_LONG_COMPLEX_STRATEGY_99999"
    )
    assert len(cid_long) <= 25
    assert re.match(r"^[a-zA-Z0-9_-]+$", cid_long)


def test_calculate_order_slices_below_freeze_limit() -> None:
    slices = calculate_order_slices(total_quantity=500, freeze_limit=1800)
    assert slices == [500]


def test_calculate_order_slices_exceeding_freeze_limit() -> None:
    # 4000 total with freeze limit of 1800 -> 1800, 1800, 400
    slices = calculate_order_slices(total_quantity=4000, freeze_limit=1800)
    assert slices == [1800, 1800, 400]
    assert sum(slices) == 4000


def test_calculate_order_slices_with_lot_size() -> None:
    # Total 2500, freeze 1000, lot size 50 -> 1000, 1000, 500
    slices = calculate_order_slices(total_quantity=2500, freeze_limit=1000, lot_size=50)
    assert slices == [1000, 1000, 500]
    assert all(s % 50 == 0 for s in slices)


def test_calculate_order_slices_invalid_quantity() -> None:
    with pytest.raises(ValueError, match="Total quantity must be greater than zero"):
        calculate_order_slices(total_quantity=0)


def test_order_request_validation_success() -> None:
    req = DhanOrderRequest(
        transactionType=TransactionType.BUY,
        exchangeSegment=ExchangeSegment.NSE_EQ,
        productType=ProductType.CNC,
        orderType=OrderType.LIMIT,
        validity=OrderValidity.DAY,
        securityId="1333",
        quantity=25,
        price=1250.50,
        correlationId="NX-TEST-VALID-01",
    )
    assert req.quantity == 25
    assert req.price == 1250.50
    payload = req.to_api_payload(client_id="1100000000")
    assert payload["dhanClientId"] == "1100000000"
    assert payload["securityId"] == "1333"
    assert payload["transactionType"] == "BUY"


def test_order_request_validation_invalid_quantity() -> None:
    with pytest.raises(ValidationError):
        DhanOrderRequest(
            transactionType=TransactionType.BUY,
            exchangeSegment=ExchangeSegment.NSE_EQ,
            securityId="1333",
            quantity=-10,  # Invalid
        )


def test_order_request_validation_correlation_id_length() -> None:
    match_msg = "correlationId must not exceed 25 characters per ADR-0007"
    with pytest.raises(ValidationError, match=match_msg):
        DhanOrderRequest(
            transactionType=TransactionType.BUY,
            exchangeSegment=ExchangeSegment.NSE_EQ,
            securityId="1333",
            quantity=10,
            correlationId="VERY_LONG_CORRELATION_ID_EXCEEDING_TWENTY_FIVE_CHARS",
        )


def test_order_request_validation_correlation_id_chars() -> None:
    with pytest.raises(ValidationError, match="correlationId must contain only alphanumeric"):
        DhanOrderRequest(
            transactionType=TransactionType.BUY,
            exchangeSegment=ExchangeSegment.NSE_EQ,
            securityId="1333",
            quantity=10,
            correlationId="INVALID@CHAR$!#",
        )


def test_slice_order_request_payload() -> None:
    slice_req = DhanSliceOrderRequest(
        transactionType=TransactionType.BUY,
        exchangeSegment=ExchangeSegment.NSE_FNO,
        productType=ProductType.MARGIN,
        orderType=OrderType.LIMIT,
        validity=OrderValidity.DAY,
        securityId="45231",
        quantity=3600,
        price=185.0,
    )
    payload = slice_req.to_api_payload(client_id="1100000000")
    assert payload["dhanClientId"] == "1100000000"
    assert payload["quantity"] == 3600
    assert payload["correlationId"].startswith("SL-")


def test_order_modify_request_payload() -> None:
    mod = DhanOrderModifyRequest(
        orderId="ORD123456",
        orderType=OrderType.LIMIT,
        quantity=50,
        price=1300.0,
        validity=OrderValidity.DAY,
    )
    payload = mod.to_api_payload(client_id="1100000000")
    assert payload["dhanClientId"] == "1100000000"
    assert payload["orderId"] == "ORD123456"
    assert payload["price"] == 1300.0


def test_order_response_parsing() -> None:
    resp = DhanOrderResponse.model_validate({"orderId": "ORD987654", "orderStatus": "TRANSIT"})
    assert resp.order_id == "ORD987654"
    assert resp.order_status == OrderStatus.TRANSIT


def test_get_freeze_limit_equity_and_derivatives() -> None:
    # Equities are unconstrained (None)
    assert get_freeze_limit("RELIANCE", ExchangeSegment.NSE_EQ) is None
    assert get_freeze_limit("INFY", "NSE_EQ") is None
    assert get_freeze_limit("TCS", ExchangeSegment.BSE_EQ) is None

    # Derivatives match index caps
    assert get_freeze_limit("NIFTY26SEP24500CE", ExchangeSegment.NSE_FNO) == 1800
    assert get_freeze_limit("BANKNIFTY26SEP52000PE", ExchangeSegment.NSE_FNO) == 900
    assert get_freeze_limit("FINNIFTY", ExchangeSegment.NSE_FNO) == 1800
    assert get_freeze_limit("MIDCPNIFTY", ExchangeSegment.NSE_FNO) == 4200

    # Generic FNO default
    assert get_freeze_limit("UNKNOWN_STOCK_FUT", ExchangeSegment.NSE_FNO) == 1800


def test_calculate_order_slices_unconstrained_equity() -> None:
    # 5,000 equity shares should NOT be sliced when freeze_limit is None
    slices = calculate_order_slices(total_quantity=5000, freeze_limit=None)
    assert slices == [5000]


def test_dhan_slice_order_response_model() -> None:
    payload = [
        {"orderId": "ORD-SLICE-1", "orderStatus": "PENDING"},
        {"orderId": "ORD-SLICE-2", "orderStatus": "TRANSIT"},
    ]
    resp = DhanSliceOrderResponse.from_api_response(payload)
    assert len(resp) == 2
    assert resp[0].order_id == "ORD-SLICE-1"
    assert resp[1].order_id == "ORD-SLICE-2"
    assert resp[0].order_status == OrderStatus.PENDING
    assert resp[1].order_status == OrderStatus.TRANSIT

    # Test iteration
    order_ids = [order.order_id for order in resp]
    assert order_ids == ["ORD-SLICE-1", "ORD-SLICE-2"]
