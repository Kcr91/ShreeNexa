# Dhan Recorded-Cassette Evidence Procedure

This procedure is a proposal for a separately approved, read-only evidence
task. It is not authorization to execute a broker call, obtain credentials, or
change F0.5 status.

1. Obtain explicit authorization naming the read-only endpoints and capture
   window. Do not include orders, account changes, deliberate rate-limit
   triggering, or live activation.
2. Load a real credential only through the implemented local credential
   interface (environment injection or current-user DPAPI). Never paste it into
   chat, a prompt, a fixture, a report, or source control.
3. Capture only the minimum response body for the approved read-only request.
   Do not persist request headers, tokens, cookies, signed URLs, or raw account
   identifiers. If a required failure response cannot be observed safely and
   naturally, leave that scenario blocked rather than provoking it.
4. Sanitize in a local temporary workspace with an explicit field allowlist.
   Replace account identifiers with the documented test-only format and verify
   the result contains no secret-shaped values before it enters the repository.
5. Record truthful provenance metadata: the actual UTC capture time, endpoint
   and broker origin, and the sanitization method/reviewer. Mark
   `recorded_broker_response: true` only when those facts are evidenced.
6. Run offline parsing/error tests, the repository secret scan, fixture schema
   validation, and an independent review against the exact candidate SHA.
   Preserve hashes and command results; never infer historical evidence from a
   later test run.

Synthetic fixtures remain available for deterministic unit tests. They do not
become recorded evidence through relabeling or added metadata.
