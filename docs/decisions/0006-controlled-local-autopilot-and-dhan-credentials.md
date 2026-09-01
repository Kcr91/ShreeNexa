# ADR-0006: Controlled Local Autopilot and Dhan Local Credentials

- **Status:** Accepted for the bounded pilot
- **Date:** 2026-09-01
- **Scope:** `feature/dev-autopilot-pilot`, then F0.4–F0.9 only

## Context

The normal repository workflow requires human authorization at each merge
boundary and defers a general feature-builder to Epic 11. The user authorized a
smaller local development supervisor for six named foundation features. The
same authorization resolves F0.4's changing Dhan-token fact and local
credential-storage decision.

Official Dhan v2 authentication documentation says an access token generated
manually in Dhan Web is valid for 24 hours and exposes absolute expiry metadata
in relevant authentication responses. It separately says API key and secret
artifacts are valid for 12 months. The specification's 30-day Data API
subscription renewal remains unrelated and unchanged. See
[DhanHQ v2 authentication](https://dhanhq.co/docs/v2/authentication/).

Microsoft documents that `CryptProtectData` normally allows decryption only by
the user with the same logon credentials on the same computer. Setting
`CRYPTPROTECT_LOCAL_MACHINE` instead makes data decryptable by any user on the
computer. See
[Microsoft CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

## Decision

1. A local supervisor may run one Codex implementation session at a time,
   independently verify controller-defined gates, obtain a fresh read-only
   review for the exact base and candidate SHAs, and fast-forward locally only
   after all evidence is valid.
2. Its product-feature allowlist is exactly F0.4, F0.5, F0.6, F0.7, F0.8, and
   F0.9 in manifest dependency order. It stops after F0.9. This is not the Epic
   11 product feature-builder.
3. This replaces routine per-feature commit/merge/continue confirmation only
   for the setup and allowlisted pilot. It does not authorize remote changes,
   deployment, live trading, protected-path edits, new costs/credentials,
   installation, permission bypasses, or later features.
4. The setup commit pins the controller, policy, gate/review contracts,
   protected definitions, allowlist, and safety tests. Feature workers cannot
   edit or weaken that control plane or mark themselves complete.
5. A manually generated Dhan Web access token has a 24-hour lifetime. When
   expiry metadata is supplied, F0.4 preserves its original absolute instant;
   restart never substitutes a new `now + 24 hours`. Unknown expiry, timezone
   conversion, expiry, revocation, and authentication rejection are explicit
   states.
6. Production Dhan credentials continue to be injected as environment
   variables. Local persistent storage uses Windows DPAPI scoped to the current
   Windows user and never sets `CRYPTPROTECT_LOCAL_MACHINE`.
7. The encrypted payload contains only the Dhan client ID, access token, and
   necessary non-secret expiry metadata. PINs, passwords, TOTP seeds, browser
   cookies, API keys/secrets, and unrelated account data are never accepted or
   stored. There is no plaintext fallback or plaintext intermediate file.
8. The encrypted file lives under a Git-ignored ShreeNexa runtime root and F0.4
   applies current-user-only filesystem access. Real values are entered through
   a local application interface after implementation, never through Codex,
   fixtures, logs, reports, or reviewer processes. Automated proof uses fakes.

## Security limitation

Current-user DPAPI protects data at rest from other Windows users and from
copying the encrypted file to an unrelated account/machine in ordinary use. It
does not protect credentials from malicious or compromised software already
running as that same Windows user. Endpoint security, session integrity, token
expiry/revocation, and prompt response to authentication rejection remain
necessary.

## Consequences

- The controller keeps its atomic operational recovery journal in an ignored
  runtime directory. That journal is not a second project-progress database;
  tracked feature status still changes only through `build/update_state.py`.
- Missing, malformed, skipped, stale-SHA, timed-out, or unverifiable evidence
  blocks integration. A changed candidate invalidates earlier evidence.
- F0.5's recorded-cassette requirement is not weakened. If authorized,
  authentic sanitized evidence cannot be obtained without real credentials or
  a new decision, the pilot stops rather than fabricating a cassette.

## Recovery clarification (2026-09-01)

The recovery task established that the seven F0.5 files were generated during
development and have no evidenced broker origin, capture date, or sanitization
history. They are synthetic deterministic fixtures, not recorded responses.
The controller must reconcile Git implementation, tracked status, durable run
state, and exact-SHA evidence before selection, and feature-specific evidence
checks must execute in the controller path. F0.5 therefore remains blocked on
the original recorded-cassette requirement.
