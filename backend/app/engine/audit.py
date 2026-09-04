"""Immutable audit trail for trading events with cryptographic tamper-evidence and redaction.

CRITICAL INVARIANTS:
1. Cryptographic Hash Chain: Every event links to its predecessor via SHA-256 (prev_hash).
   Any modification, insertion, deletion, or reordering causes verify_chain() to fail.
2. End-to-End Reconstruction: A single trade can be reconstructed across its complete
   lifecycle from signal to reconciliation using correlation_id.
3. Secret Redaction: Tokens, passwords, and sensitive credentials are automatically redacted
   before entering the audit ledger.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.config import mask_client_id

logger = logging.getLogger("shreenexa.engine.audit")

GENESIS_HASH = "0" * 64
SENSITIVE_KEYS = {
    "access_token",
    "token",
    "password",
    "secret",
    "authorization",
    "cookie",
    "api_token",
    "jwt",
}


class AuditEventType(StrEnum):
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    RISK_FILTER_EVALUATED = "RISK_FILTER_EVALUATED"
    RISK_DECISION = "RISK_DECISION"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_RESPONSE = "ORDER_RESPONSE"
    ORDER_UPDATE = "ORDER_UPDATE"
    RECONCILIATION_EVENT = "RECONCILIATION_EVENT"
    OPERATOR_OVERRIDE = "OPERATOR_OVERRIDE"
    KILL_SWITCH_EVENT = "KILL_SWITCH_EVENT"


def redact_sensitive_data(val: Any) -> Any:
    """Recursively scrub sensitive keys and mask client IDs in audit payloads."""
    if isinstance(val, dict):
        cleaned: dict[str, Any] = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if any(sens in k_lower for sens in SENSITIVE_KEYS):
                cleaned[k] = "[REDACTED]"
            elif k_lower in ("client_id", "dhan_client_id", "dhanclientid"):
                cleaned[k] = mask_client_id(str(v)) if v else "[NONE]"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    if isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    return val


def compute_canonical_hash(
    prev_hash: str,
    event_seq: int,
    event_type: str,
    timestamp: str,
    correlation_id: str,
    order_id: str | None,
    payload: dict[str, Any],
) -> str:
    """Compute SHA-256 digest of canonical representation."""
    canonical_dict = {
        "prev_hash": prev_hash,
        "event_seq": event_seq,
        "event_type": event_type,
        "timestamp": timestamp,
        "correlation_id": correlation_id,
        "order_id": order_id,
        "payload": payload,
    }
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class AuditEvent(BaseModel):
    """Immutable, tamper-evident audit record."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: f"AUD-{uuid.uuid4().hex[:8]}")
    event_seq: int
    event_type: AuditEventType
    timestamp: str
    correlation_id: str
    order_id: str | None = None
    payload: dict[str, Any]
    prev_hash: str
    hash: str

    def verify_integrity(self) -> bool:
        """Check if this event's hash matches its canonical content."""
        expected = compute_canonical_hash(
            prev_hash=self.prev_hash,
            event_seq=self.event_seq,
            event_type=self.event_type.value,
            timestamp=self.timestamp,
            correlation_id=self.correlation_id,
            order_id=self.order_id,
            payload=self.payload,
        )
        return self.hash == expected


class AuditLedger:
    """Append-only, tamper-evident audit ledger with chain verification and reconstruction."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._log_path = Path(log_path) if log_path else None
        if self._log_path and self._log_path.exists():
            self._load_from_disk()

    @property
    def total_events(self) -> int:
        return len(self._events)

    def _load_from_disk(self) -> None:
        if not self._log_path or not self._log_path.exists():
            return
        try:
            with open(self._log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    event = AuditEvent.model_validate(data)
                    self._events.append(event)
            logger.info("Hydrated %d audit events from %s", len(self._events), self._log_path)
        except Exception as exc:
            logger.error("Failed to load audit events from %s: %s", self._log_path, exc)

    def record_event(
        self,
        event_type: AuditEventType,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        order_id: str | None = None,
        timestamp: str | None = None,
    ) -> AuditEvent:
        """Record an event with redacted payload into the tamper-evident hash chain."""
        cid = correlation_id or f"SYS-{uuid.uuid4().hex[:8]}"
        clean_payload = redact_sensitive_data(payload or {})
        seq = len(self._events)
        prev_hash = self._events[-1].hash if self._events else GENESIS_HASH
        ts = timestamp or datetime.now(UTC).isoformat()

        event_hash = compute_canonical_hash(
            prev_hash=prev_hash,
            event_seq=seq,
            event_type=event_type.value,
            timestamp=ts,
            correlation_id=cid,
            order_id=order_id,
            payload=clean_payload,
        )

        event = AuditEvent(
            event_seq=seq,
            event_type=event_type,
            timestamp=ts,
            correlation_id=cid,
            order_id=order_id,
            payload=clean_payload,
            prev_hash=prev_hash,
            hash=event_hash,
        )
        self._events.append(event)

        if self._log_path:
            try:
                self._log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(event.model_dump_json() + "\n")
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
            except Exception as exc:
                logger.error("Failed to persist audit event %d to disk: %s", seq, exc)

        logger.debug("Recorded audit event %d: %s [%s]", seq, event_type, correlation_id)
        return event

    def verify_chain(self) -> tuple[bool, int | None]:
        """Verify complete cryptographic hash chain.

        Returns (True, None) if valid, or (False, invalid_seq) if tampered.
        """
        expected_prev_hash = GENESIS_HASH

        for idx, event in enumerate(self._events):
            if event.event_seq != idx:
                logger.error("Audit chain broken: expected seq %d, found %d", idx, event.event_seq)
                return False, idx

            if event.prev_hash != expected_prev_hash:
                logger.error("Audit chain broken: seq %d prev_hash mismatch", idx)
                return False, idx

            if not event.verify_integrity():
                logger.error("Audit chain broken: seq %d hash integrity check failed", idx)
                return False, idx

            expected_prev_hash = event.hash

        return True, None

    def reconstruct_lifecycle(self, correlation_id: str) -> list[AuditEvent]:
        """Reconstruct the end-to-end chronological lifecycle of a specific trade/order."""
        return [e for e in self._events if e.correlation_id == correlation_id]

    def get_event(self, seq: int) -> AuditEvent | None:
        """Retrieve audit event by sequence number."""
        if 0 <= seq < len(self._events):
            return self._events[seq]
        return None


_process_ledger: AuditLedger | None = None


def get_audit_ledger(log_path: Path | str | None = None) -> AuditLedger:
    """Return process-scoped AuditLedger instance with durable persistence."""
    global _process_ledger
    if _process_ledger is None:
        default_path = Path("data") / "audit_ledger.jsonl"
        _process_ledger = AuditLedger(log_path=log_path or default_path)
    return _process_ledger


def reset_audit_ledger(log_path: Path | str | None = None) -> AuditLedger:
    """Reset the process-scoped AuditLedger (primarily for test isolation)."""
    global _process_ledger
    _process_ledger = AuditLedger(log_path=log_path)
    return _process_ledger
