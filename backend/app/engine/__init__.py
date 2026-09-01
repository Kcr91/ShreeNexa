"""engine: owns paper/live deployment event loops, broker boundary,
portfolio/risk evaluation, orders, fills, positions, checkpoint/recovery
(per ADR-0002). Not yet implemented -- see backend/app/engine/core.py and
F3.1+. backend/app/engine/risk.py and broker.py are protected paths once
they exist (docs/qa/protected-paths.md)."""
