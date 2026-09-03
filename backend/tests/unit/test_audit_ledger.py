"""Unit and proof tests for AuditLedger, tamper-evidence, redaction, and reconstruction (F12.6)."""

from __future__ import annotations

from app.engine.audit import AuditEvent, AuditEventType, AuditLedger


def test_tamper_evident_chain_verification_passes_on_valid_ledger() -> None:
    ledger = AuditLedger()
    correlation_id = "CORR-TEST-001"

    ledger.record_event(
        event_type=AuditEventType.SIGNAL_GENERATED,
        correlation_id=correlation_id,
        payload={"symbol": "RELIANCE", "side": "BUY", "quantity": 10},
    )
    ledger.record_event(
        event_type=AuditEventType.RISK_DECISION,
        correlation_id=correlation_id,
        payload={"status": "APPROVED", "risk_checks": "PASSED"},
    )
    ledger.record_event(
        event_type=AuditEventType.ORDER_SUBMITTED,
        correlation_id=correlation_id,
        payload={"order_id": "ORD-12345", "price": 2800.0},
        order_id="ORD-12345",
    )

    is_valid, corrupted_seq = ledger.verify_chain()
    assert is_valid is True
    assert corrupted_seq is None
    assert ledger.total_events == 3


def test_tamper_detection_on_payload_mutation() -> None:
    ledger = AuditLedger()
    correlation_id = "CORR-TAMPER-001"

    ledger.record_event(
        event_type=AuditEventType.SIGNAL_GENERATED,
        correlation_id=correlation_id,
        payload={"symbol": "TCS", "quantity": 25},
    )
    event1 = ledger.record_event(
        event_type=AuditEventType.ORDER_SUBMITTED,
        correlation_id=correlation_id,
        payload={"order_id": "ORD-9999", "quantity": 25, "price": 3500.0},
        order_id="ORD-9999",
    )
    ledger.record_event(
        event_type=AuditEventType.ORDER_UPDATE,
        correlation_id=correlation_id,
        payload={"order_id": "ORD-9999", "status": "TRADED"},
        order_id="ORD-9999",
    )

    # Valid before tampering
    assert ledger.verify_chain()[0] is True

    # Tamper with event 1: change price from 3500.0 to 1000.0
    tampered_payload = dict(event1.payload)
    tampered_payload["price"] = 1000.0

    tampered_event = AuditEvent(
        event_id=event1.event_id,
        event_seq=event1.event_seq,
        event_type=event1.event_type,
        timestamp=event1.timestamp,
        correlation_id=event1.correlation_id,
        order_id=event1.order_id,
        payload=tampered_payload,  # Tampered
        prev_hash=event1.prev_hash,
        hash=event1.hash,  # Old hash does not match modified payload
    )
    ledger._events[1] = tampered_event

    # Cryptographic verification MUST detect tampering at seq 1
    is_valid, corrupted_seq = ledger.verify_chain()
    assert is_valid is False
    assert corrupted_seq == 1


def test_tamper_detection_on_event_deletion_or_reordering() -> None:
    ledger = AuditLedger()
    for i in range(4):
        ledger.record_event(
            event_type=AuditEventType.RISK_FILTER_EVALUATED,
            correlation_id=f"CORR-{i}",
            payload={"step": i},
        )

    assert ledger.verify_chain()[0] is True

    # Delete event at index 1
    del ledger._events[1]

    # Verification MUST detect sequence mismatch / broken hash chain
    is_valid, corrupted_seq = ledger.verify_chain()
    assert is_valid is False
    assert corrupted_seq == 1


def test_sensitive_values_are_strictly_redacted() -> None:
    ledger = AuditLedger()
    correlation_id = "CORR-AUTH-001"

    raw_payload = {
        "access_token": "eyJhbGciOiJIUzUxMiIsIn...",
        "api_token": "super_secret_dhan_token",
        "authorization": "Bearer secret_jwt_here",
        "client_id": "1100000000",
        "nested": {
            "password": "my_secure_password",
            "dhan_client_id": "1234567890",
            "normal_field": "safe_value",
        },
    }

    event = ledger.record_event(
        event_type=AuditEventType.ORDER_SUBMITTED,
        correlation_id=correlation_id,
        payload=raw_payload,
    )

    # Redactions verified
    payload = event.payload
    assert payload["access_token"] == "[REDACTED]"
    assert payload["api_token"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["client_id"] == "1100***000"

    nested = payload["nested"]
    assert nested["password"] == "[REDACTED]"
    assert nested["dhan_client_id"] == "1234***890"
    assert nested["normal_field"] == "safe_value"


def test_end_to_end_trade_lifecycle_reconstruction() -> None:
    ledger = AuditLedger()
    target_corr_id = "TRADE-RECONSTRUCT-42"
    other_corr_id = "TRADE-OTHER-99"

    # Step 1: Signal
    ledger.record_event(
        event_type=AuditEventType.SIGNAL_GENERATED,
        correlation_id=target_corr_id,
        payload={"symbol": "INFY", "target_price": 1850.0},
    )
    # Interleaved other trade event
    ledger.record_event(
        event_type=AuditEventType.SIGNAL_GENERATED,
        correlation_id=other_corr_id,
        payload={"symbol": "WIPRO"},
    )
    # Step 2: Risk decision
    ledger.record_event(
        event_type=AuditEventType.RISK_DECISION,
        correlation_id=target_corr_id,
        payload={"decision": "APPROVED", "max_allowed_qty": 50},
    )
    # Step 3: Order Submitted
    ledger.record_event(
        event_type=AuditEventType.ORDER_SUBMITTED,
        correlation_id=target_corr_id,
        payload={"order_type": "LIMIT", "price": 1850.0, "qty": 50},
        order_id="ORD-INFY-1",
    )
    # Step 4: Broker response
    ledger.record_event(
        event_type=AuditEventType.ORDER_RESPONSE,
        correlation_id=target_corr_id,
        payload={"order_id": "ORD-INFY-1", "order_status": "PENDING"},
        order_id="ORD-INFY-1",
    )
    # Step 5: Order update (Fill)
    ledger.record_event(
        event_type=AuditEventType.ORDER_UPDATE,
        correlation_id=target_corr_id,
        payload={"order_id": "ORD-INFY-1", "status": "TRADED", "fill_qty": 50},
        order_id="ORD-INFY-1",
    )
    # Step 6: Reconciliation
    ledger.record_event(
        event_type=AuditEventType.RECONCILIATION_EVENT,
        correlation_id=target_corr_id,
        payload={"order_id": "ORD-INFY-1", "reconciled_with_broker": True},
        order_id="ORD-INFY-1",
    )

    # Reconstruct target trade lifecycle
    lifecycle = ledger.reconstruct_lifecycle(target_corr_id)
    assert len(lifecycle) == 6

    expected_types = [
        AuditEventType.SIGNAL_GENERATED,
        AuditEventType.RISK_DECISION,
        AuditEventType.ORDER_SUBMITTED,
        AuditEventType.ORDER_RESPONSE,
        AuditEventType.ORDER_UPDATE,
        AuditEventType.RECONCILIATION_EVENT,
    ]
    actual_types = [e.event_type for e in lifecycle]
    assert actual_types == expected_types

    # Ensure all events are valid cryptographically
    assert ledger.verify_chain()[0] is True
