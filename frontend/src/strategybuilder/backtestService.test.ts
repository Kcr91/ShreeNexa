import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { runBacktest, getBacktest, BacktestResult } from "./backtestService";
import { ApiError } from "../api/client";
import { CanonicalStrategyIR } from "./canonical";

const sampleIR: CanonicalStrategyIR = {
  ir_version: 1,
  name: "T",
  kind: "stock",
  horizon: "intraday",
  strategy_type: "trend_following",
  universe: { type: "index", index_name: "NIFTY 50" },
  timeframe: "15m",
  indicators: {},
  entries: [],
  exits: [],
  sizing: { type: "fixed_value", value: 50000 },
  risk: { max_positions: 5, no_trade_windows: [] },
};

const sampleResult: BacktestResult = {
  backtest_id: "bt-1",
  strategy_name: "T",
  metrics: {
    initial_capital: 100000,
    final_equity: 112000,
    total_return_pct: 12,
    cagr_pct: 12,
    total_pnl: 12000,
    total_costs: 100,
    realized_pnl: 12000,
    unrealized_pnl: 0,
    max_drawdown_pct: 3,
    max_drawdown_value: 3000,
    sharpe_ratio: 1.5,
    sortino_ratio: 2,
    calmar_ratio: 4,
    total_trades: 10,
    winning_trades: 6,
    losing_trades: 4,
    win_rate_pct: 60,
    profit_factor: 1.8,
  },
  equity_curve: [],
  trades: [],
  executed_at: "2026-01-01T00:00:00Z",
  engine_commit: "test",
};

declare const globalThis: { fetch: typeof fetch };

describe("backtestService", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("POSTs the correct payload shape to /api/v1/backtests/run", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => sampleResult,
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await runBacktest({
      strategyIR: sampleIR,
      startDate: "2024-01-01",
      endDate: "2024-12-31",
      initialCapital: 100000,
      slippagePct: 0.5,
    });

    expect(result.backtest_id).toBe("bt-1");
    const call = fetchMock.mock.calls[0];
    expect(String(call[0])).toContain("/api/v1/backtests/run");
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body.start_date).toBe("2024-01-01T00:00:00");
    expect(body.end_date).toBe("2024-12-31T23:59:59");
    expect(body.initial_cash).toBe(100000);
    expect(body.slippage_model).toBe("percent");
    expect(body.slippage_param).toBeCloseTo(0.005);
    expect(body.strategy.name).toBe("T");
  });

  it("uses 'none' slippage when slippagePct is omitted", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => sampleResult,
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await runBacktest({
      strategyIR: sampleIR,
      startDate: "2024-01-01",
      endDate: "2024-01-10",
      initialCapital: 50000,
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.slippage_model).toBe("none");
    expect(body.slippage_param).toBe(0);
  });

  it("surfaces API errors with status 0 for network failures", async () => {
    globalThis.fetch = (() => Promise.reject(new TypeError("Failed to fetch"))) as unknown as typeof fetch;
    await expect(
      runBacktest({ strategyIR: sampleIR, startDate: "2024-01-01", endDate: "2024-01-10", initialCapital: 100000 })
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("GETs by id for getBacktest", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => sampleResult,
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const r = await getBacktest("bt-1");
    expect(r.backtest_id).toBe("bt-1");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/v1/backtests/bt-1");
  });
});
