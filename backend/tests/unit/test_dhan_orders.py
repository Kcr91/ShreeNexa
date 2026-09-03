"""Unit tests for typed Dhan order models, validation, and slicing logic."""

from __future__ import annotations

import pytest
from app.dhan.orders import (
    DhanOrderModifyRequest,
    DhanOrderRequest,
    DhanOrderResponse,
    DhanSliceOrderRequest,
    ExchangeSegment,
    OrderStatus,
    OrderType,
    OrderValidity,
    ProductType,
    TransactionType,
    calculate_order_slices,
    generate_correlation_id,
)
from pydantic import ValidationError


def test_generate_correlation_id() -> None:
    cid1 = generate_correlation_id()
    cid2 = generate_correlation_id()
    assert cid1 != cid2
    assert len(cid1) <= 30
    assert cid1.startswith("NX-")


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
    with pytest.raises(ValidationError, match="correlationId must not exceed 30 characters"):
        DhanOrderRequest(
            transactionType=TransactionType.BUY,
            exchangeSegment=ExchangeSegment.NSE_EQ,
            securityId="1333",
            quantity=10,
            correlationId="VERY_LONG_CORRELATION_ID_EXCEEDING_THIRTY_CHARACTERS_LIMIT",
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
