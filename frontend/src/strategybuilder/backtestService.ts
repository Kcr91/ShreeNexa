/**
 * Thin service wrapping the backend `/api/v1/backtests/*` endpoints.
 * The backend validates the request body against `BacktestConfig` (which embeds
 * `StrategyIR`); the IR itself ignores unknown fields, so the UI-only `_ui`
 * block emitted by `compileVisualToCanonicalIR` is dropped silently server-side.
 */

import { apiClient } from "../api/client";
import { CanonicalStrategyIR } from "./canonical";

export interface BacktestRequest {
  strategyIR: CanonicalStrategyIR;
  startDate: string; // ISO date (YYYY-MM-DD) — the backend accepts ISO datetimes too
  endDate: string;
  initialCapital: number;
  slippagePct?: number;
}

export interface BacktestMetrics {
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  cagr_pct: number;
  total_pnl: number;
  total_costs: number;
  realized_pnl: number;
  unrealized_pnl: number;
  max_drawdown_pct: number;
  max_drawdown_value: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  profit_factor: number;
}

export interface BacktestEquityPoint {
  timestamp: string;
  equity: number;
  cash: number;
  unrealized_pnl: number;
  realized_pnl: number;
}

export interface BacktestFill {
  fill_id: string;
  order_id: string;
  security_id: string;
  exchange_segment: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  timestamp: string;
  brokerage: number;
  taxes: number;
  slippage: number;
}

export interface BacktestResult {
  backtest_id: string;
  strategy_name: string;
  metrics: BacktestMetrics;
  equity_curve: BacktestEquityPoint[];
  trades: BacktestFill[];
  executed_at: string;
  engine_commit: string;
}

/** Shape of `POST /api/v1/backtests/run` body. */
interface BacktestRunPayload {
  strategy: CanonicalStrategyIR;
  start_date: string;
  end_date: string;
  initial_cash: number;
  slippage_model: "percent" | "none";
  slippage_param: number;
}

function toIsoDateTime(dateStr: string, endOfDay = false): string {
  // Accept YYYY-MM-DD or full ISO; coerce to full ISO so Pydantic's datetime
  // parser accepts it unambiguously.
  if (dateStr.includes("T")) return dateStr;
  return `${dateStr}T${endOfDay ? "23:59:59" : "00:00:00"}`;
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResult> {
  const slippage = req.slippagePct ?? 0;
  const payload: BacktestRunPayload = {
    strategy: req.strategyIR,
    start_date: toIsoDateTime(req.startDate, false),
    end_date: toIsoDateTime(req.endDate, true),
    initial_cash: req.initialCapital,
    slippage_model: slippage > 0 ? "percent" : "none",
    slippage_param: slippage > 0 ? slippage / 100 : 0,
  };
  return apiClient.request<BacktestResult>("/api/v1/backtests/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBacktest(backtestId: string): Promise<BacktestResult> {
  return apiClient.request<BacktestResult>(`/api/v1/backtests/${backtestId}`);
}

export async function listBacktests(): Promise<BacktestResult[]> {
  return apiClient.request<BacktestResult[]>("/api/v1/backtests");
}
