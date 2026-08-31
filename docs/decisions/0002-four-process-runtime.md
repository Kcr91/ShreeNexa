# ADR-0002: Four-Process Runtime and Supervision Boundaries

- **Status:** Accepted
- **Date:** 2026-08-31
- **Feature:** M0.2

## Context

The web API must be deployable without interrupting running strategies. Dhan feed handling, strategy execution, and long-running jobs have different failure and scaling characteristics. Keeping them in one process would turn an API restart into a trading-engine restart and make ownership ambiguous.

## Decision

The backend has exactly four runtime process roles:

| Process | Owns | Must not own |
|---|---|---|
| `api` | REST endpoints, browser WebSocket fan-out, validation, development auth boundary, user commands | Dhan feed sockets, strategy event loops, long-running backfills, authoritative fills or positions |
| `engine` | Paper/live deployment event loops, broker boundary, portfolio/risk evaluation, orders, fills, positions, checkpoint/recovery | Browser sessions, historical backfill, dashboard rendering, Dhan market-feed fan-out |
| `feedd` | Dhan market-feed and depth connections, subscription state, packet decoding, normalized hot-market state and feed health | Strategy decisions, orders, historical warehouse mutation, browser-specific layout state |
| `worker` | Backfills, corrections, backtests, screeners, parameter sweeps, scheduled and queued jobs | Live strategy loops, Dhan feed sockets, browser connections |

The roles may share tested library modules, but one process entry point must never import or invoke another process entry point. Cross-process work uses versioned commands/events and durable stores.

## Runtime invariants

1. `api` can restart independently while `engine`, `feedd`, and `worker` continue.
2. No process holds authoritative orders, fills, positions, deployments, or job results only in memory.
3. `engine` persists a state transition before treating it as acknowledged and recovers from durable state.
4. `feedd` is the only owner of Dhan market-feed/depth sockets. A central connection-budget component within that boundary will enforce the shared conservative limit in F0.9.
5. `worker` is the sole mutator of historical Parquet partitions; readers never rewrite a partition.
6. The supervisor starts and observes processes independently. Selecting the Windows supervisor implementation is deferred to F0.3, but independent restart semantics are not.

## Communication boundaries

- `api` issues durable commands and enqueues jobs; it does not call a live engine loop in-process.
- `feedd` publishes normalized market state to Redis; it does not call strategies.
- `engine` reads market state and durable deployment state, then writes execution state transactionally.
- `worker` consumes jobs and writes job progress/results; large historical results remain in the warehouse.
- Browser clients communicate only with `api` over HTTP/WebSocket.

## Consequences

- Four independently runnable entry points and health checks are required in F0.3.
- Shared code is organized by capability, not copied between processes.
- A single-process development shortcut is not permitted if it changes ownership or restart semantics.
- Live order capability remains absent until Epic 12 and requires explicit approval.
