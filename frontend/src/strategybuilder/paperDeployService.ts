/**
 * Service wrapping the existing backend paper-trading deployment API at
 * `/api/v1/paper/*`. The backend route is paper-only by construction
 * (prefix); there is no live-trading surface here and this service MUST
 * NOT be extended to call any live-engine endpoint.
 */

import { apiClient } from "../api/client";

export type DeploymentState = "CREATED" | "RUNNING" | "PAUSED" | "STOPPED" | "FAILED";

export interface StrategyDeployment {
  deployment_id: string;
  strategy_id: string;
  strategy_name: string;
  account_id: string;
  allocated_capital: number;
  state: DeploymentState;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  stopped_at?: string | null;
  active_orders_count: number;
  open_positions_count: number;
  parameters: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface PaperPosition {
  symbol?: string;
  security_id: string;
  exchange_segment: string;
  side?: string;
  quantity: number;
  average_price: number;
  current_price: number;
  realized_pnl: number;
  unrealized_pnl: number;
}

export interface PaperFill {
  fill_id: string;
  order_id: string;
  security_id: string;
  exchange_segment: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  timestamp: string;
}

export interface PortfolioSummary {
  account_id: string;
  cash: number;
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  positions_count?: number;
  open_orders_count?: number;
}

export interface DeployParams {
  strategyId: string;
  strategyName: string;
  accountId: string;
  allocatedCapital: number;
}

export async function createPaperDeployment(p: DeployParams): Promise<StrategyDeployment> {
  return apiClient.request<StrategyDeployment>("/api/v1/paper/deployments", {
    method: "POST",
    body: JSON.stringify({
      strategy_id: p.strategyId,
      strategy_name: p.strategyName,
      account_id: p.accountId,
      allocated_capital: p.allocatedCapital,
      actor: "builder-ui",
      reason: "Deploy from Strategy Builder",
    }),
  });
}

export async function listPaperDeployments(state?: DeploymentState): Promise<StrategyDeployment[]> {
  const qs = state ? `?state=${state}` : "";
  return apiClient.request<StrategyDeployment[]>(`/api/v1/paper/deployments${qs}`);
}

export async function getPaperDeployment(id: string): Promise<StrategyDeployment> {
  return apiClient.request<StrategyDeployment>(`/api/v1/paper/deployments/${id}`);
}

type LifecycleOp = "pause" | "resume" | "stop";

export async function paperLifecycle(
  id: string,
  op: LifecycleOp,
  closePositions = false
): Promise<StrategyDeployment> {
  return apiClient.request<StrategyDeployment>(`/api/v1/paper/deployments/${id}/${op}`, {
    method: "POST",
    body: JSON.stringify({ actor: "builder-ui", reason: `Operator ${op}`, close_positions: closePositions }),
  });
}

export async function getPaperPositions(accountId = "default"): Promise<PaperPosition[]> {
  return apiClient.request<PaperPosition[]>(`/api/v1/paper/positions?account_id=${encodeURIComponent(accountId)}`);
}

export async function getPaperFills(accountId = "default"): Promise<PaperFill[]> {
  return apiClient.request<PaperFill[]>(`/api/v1/paper/fills?account_id=${encodeURIComponent(accountId)}`);
}

export async function getPortfolioSummary(accountId = "default"): Promise<PortfolioSummary> {
  return apiClient.request<PortfolioSummary>(
    `/api/v1/paper/portfolio/summary?account_id=${encodeURIComponent(accountId)}`
  );
}
