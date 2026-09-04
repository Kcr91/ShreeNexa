# 7. Correlation ID Character Set and Length Limits

Date: 2026-09-04
Status: Approved
Deciders: Architecture & Safety Core
Consulted: DhanHQ v2.5 Specification, QA-12

## Context and Problem Statement

The DhanHQ v2 API documentation contains an internal discrepancy regarding valid correlation IDs:
- In `dhan-api-docs.md:1328` (Order Slicing & Validation), the specification states allowed characters are `[^a-zA-Z0-9 _-]` (space permitted).
- In `dhan-api-docs.md:3730` (Order Request Attributes), the specification states allowed characters are `a-zA-Z0-9-_` (space disallowed).
- In `dhan-api-docs.md:3730`, the length cap is defined as 25 characters.

In `backend/app/dhan/orders.py:163-176`, ShreeNexa enforces `^[a-zA-Z0-9_-]+$` with a length limit of 25 characters. QA-12 flagged that being stricter than `dhan-api-docs.md:1328` by forbidding whitespace is a deliberate divergence that must be formally documented.

## Decision

We deliberately enforce the strict alphanumeric character set `^[a-zA-Z0-9_-]+$` (no spaces) with a hard cap of 25 characters.

### Rationale

1. **Safety and Interoperability**: Spaces in correlation IDs create severe hazards across HTTP query parameters, URL path parameters, WebSocket payload deserialization, and audit ledger JSONL formats.
2. **Defensive Invariant**: Being strictly narrower than the most permissive broker specification guarantees that every generated correlation ID is valid across all Dhan API endpoints, exchanges, and third-party gateways without risk of unexpected 400 Bad Request rejections.
3. **Audit and Reconciliation Certainty**: F12.5 reconciliation and F12.6 audit trails rely on deterministic regex matching and indexing. Forbidding spaces ensures token boundaries are unambiguous in logs, disk files, and UI displays.

## Consequences

- Any correlation ID containing spaces or non-standard punctuation will be rejected early at the client-side/API model validation boundary before transmission to Dhan.
- The 25-character maximum length limit is enforced strictly across all order generators and tickets.
