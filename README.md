# ShreeNexa Terminal

**Connected Intelligence. Prosperous Decisions.**

ShreeNexa Terminal is an Indian-market (NSE/BSE/MCX F&O) research, backtesting,
paper-trading, and approval-gated live-trading terminal built around the Dhan
API v2.

## Current status

Active development. The backend (FastAPI, ~194 REST endpoints across data,
screener, strategy, backtest, multi-variant, paper, and live engines) and a
React terminal frontend are both substantial and under continuous build. See
`PROJECT_UPDATE.md` for the live progress log and `SHREENEXA_TECHNICAL_SPEC.md`
for the product specification.

Two complementary planning tracks exist and are being reconciled:

- The governed build plan (`SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md`, feature IDs
  `M0.x`/`F0.x`–`F13.x`, with acceptance contracts under `docs/qa/acceptance/`).
- The Strategy Builder track (`Strategy Builder/`, Features 1–6: Data Engine,
  Screener, Strategy Builder, Multi-Variant Engine, Paper Trading, Live
  Trading), which reflects features added during the build.

## Safety posture

- **Live order placement is disabled by default** and is not authorized until
  the explicit activation gate. The default broker path refuses live orders
  unless `SHREENEXA_ENABLE_LIVE_TRADING=true` and a SEBI static-IP preflight
  passes.
- No real broker credentials, tokens, or secrets are committed to this
  repository.

## Repository boundary

The repository is intentionally independent and self-contained.
`F:\Algotrading` is a separate legacy project and is **not** a dependency.

## Getting started

- Python: CPython 3.14 managed by `uv` (`uv sync`).
- Node: Node.js 24 managed by `npm` (`npm.cmd --prefix frontend install`).
- See `AGENTS.md` for the canonical environment, commands, and build workflow.
