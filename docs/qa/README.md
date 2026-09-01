# Quality Assurance Index

## Core rules

- [Feature workflow](feature-workflow.md)
- [QA layers and cross-cutting gates](gates.md)
- [Protected paths](protected-paths.md)
- [Completion report template](completion-report-template.md)
- [Controlled local development autopilot runbook](../runbooks/dev-autopilot.md)
- [Dhan recorded-cassette evidence procedure](../runbooks/dhan-recorded-cassette-evidence.md)

## Acceptance contracts

- [M0.2 — Greenfield architecture](acceptance/M0.2.md)
- [M0.3 — Data lifecycle and rollback](acceptance/M0.3.md)
- [M0.4 — Repository guidance and QA rules](acceptance/M0.4.md)
- [M0.5 — Feature manifest and validated state helper](acceptance/M0.5.md)
- [M0.6 — First green baseline and hashed reference fixtures](acceptance/M0.6.md)
- [F0.1 — Repository standardization and fresh-clone baseline](acceptance/F0.1.md)
- [F0.2 — Local Postgres and Redis services via Docker Compose](acceptance/F0.2.md)
- [F0.3 — Process skeletons and durable heartbeat contract](acceptance/F0.3.md)
- [Development autopilot pilot setup](acceptance/dev-autopilot-pilot.md)
- [F0.4 — Central settings, secret redaction, and Dhan token health](acceptance/F0.4.md)
- [F0.5 — Typed Dhan REST wrapper and recorded cassettes](acceptance/F0.5.md)
- [F0.6 — Dhan Rate Limiter with Redis Token Bucket](acceptance/F0.6.md)
- [F0.7 — Detailed Dhan Instrument Master Ingestion and Typed Search](acceptance/F0.7.md)
- [F0.8 — Index Constituent Ingestion and Point-in-Time Membership](acceptance/F0.8.md)
- [F0.9 — Connection Budget Manager](acceptance/F0.9.md)
- [F1.1 — Immutable DuckDB/Parquet Bar Store](acceptance/F1.1.md)
- [F1.2 — Dhan Daily Backfill Since Inception](acceptance/F1.2.md)
- [F1.3 — Resumable Dhan 1-Minute Backfill in 90-Day Windows](acceptance/F1.3.md)
- [F1.4 — Expired-Option 30-Day Backfill and ATM Limits](acceptance/F1.4.md)
- [F1.5 — Trading Sessions, Holidays, and Calendar Versions](acceptance/F1.5.md)
- [F1.6 — Session-Aware Bar Resampling](acceptance/F1.6.md)
- [F1.7 — Corporate Action Adjustment Pipeline](acceptance/F1.7.md)
- [F1.8 — Continuous Synthetic Futures Series Generator](acceptance/F1.8.md)
- [F1.9 — Synthetic Continuous Option Surface Generator](acceptance/F1.9.md)

Acceptance is written before implementation. A feature is not complete because it has a commit; all applicable proof and review must be green.
