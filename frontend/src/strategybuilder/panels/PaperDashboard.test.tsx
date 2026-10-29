import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { PaperDashboard } from "./PaperDashboard";
import * as svc from "../paperDeployService";

const sampleDeployment: svc.StrategyDeployment = {
  deployment_id: "dep-1",
  strategy_id: "strat-1",
  strategy_name: "EMA Cross Paper",
  account_id: "default",
  allocated_capital: 100000,
  state: "RUNNING",
  created_at: "2026-01-01T09:15:00Z",
  updated_at: "2026-01-01T09:15:00Z",
  active_orders_count: 0,
  open_positions_count: 1,
  parameters: {},
  metadata: {},
};

const samplePositions: svc.PaperPosition[] = [
  { security_id: "NIFTY", exchange_segment: "NSE_IDX", quantity: 50, average_price: 24100, current_price: 24150, realized_pnl: 0, unrealized_pnl: 2500 },
];

const sampleFills: svc.PaperFill[] = [
  { fill_id: "f-1", order_id: "o-1", security_id: "NIFTY", exchange_segment: "NSE_IDX", side: "BUY", quantity: 50, price: 24100, timestamp: new Date().toISOString() },
];

const sampleSummary: svc.PortfolioSummary = {
  account_id: "default", cash: 97500, equity: 102500, realized_pnl: 0, unrealized_pnl: 2500, total_pnl: 2500,
};

describe("PaperDashboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders summary, positions, and fills on initial load", async () => {
    const depSpy = vi.spyOn(svc, "getPaperDeployment").mockResolvedValue(sampleDeployment);
    vi.spyOn(svc, "getPaperPositions").mockResolvedValue(samplePositions);
    vi.spyOn(svc, "getPaperFills").mockResolvedValue(sampleFills);
    vi.spyOn(svc, "getPortfolioSummary").mockResolvedValue(sampleSummary);

    render(<PaperDashboard isOpen={true} deploymentId="dep-1" accountId="default" onClose={() => {}} />);

    await waitFor(() => expect(depSpy).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("deployment-state")).toHaveTextContent("RUNNING"));
    expect(screen.getByTestId("positions-table")).toBeInTheDocument();
    expect(screen.getByTestId("fills-table")).toBeInTheDocument();
    expect(screen.getByText("EMA Cross Paper")).toBeInTheDocument();
  });

  it("disables the Promote-to-Live button with Epic 12 tooltip", async () => {
    vi.spyOn(svc, "getPaperDeployment").mockResolvedValue(sampleDeployment);
    vi.spyOn(svc, "getPaperPositions").mockResolvedValue([]);
    vi.spyOn(svc, "getPaperFills").mockResolvedValue([]);
    vi.spyOn(svc, "getPortfolioSummary").mockResolvedValue(sampleSummary);

    render(<PaperDashboard isOpen={true} deploymentId="dep-1" accountId="default" onClose={() => {}} />);
    const btn = await screen.findByTestId("btn-promote-live");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("title", "Live trading activation requires Epic 12 authorization");
  });

  it("calls the pause endpoint when Pause is clicked on a RUNNING deployment", async () => {
    vi.spyOn(svc, "getPaperDeployment").mockResolvedValue(sampleDeployment);
    vi.spyOn(svc, "getPaperPositions").mockResolvedValue([]);
    vi.spyOn(svc, "getPaperFills").mockResolvedValue([]);
    vi.spyOn(svc, "getPortfolioSummary").mockResolvedValue(sampleSummary);
    const lifecycleSpy = vi
      .spyOn(svc, "paperLifecycle")
      .mockResolvedValue({ ...sampleDeployment, state: "PAUSED" });

    render(<PaperDashboard isOpen={true} deploymentId="dep-1" accountId="default" onClose={() => {}} />);
    const pauseBtn = await screen.findByRole("button", { name: "Pause" });
    fireEvent.click(pauseBtn);
    await waitFor(() => expect(lifecycleSpy).toHaveBeenCalledWith("dep-1", "pause"));
    await waitFor(() => expect(screen.getByTestId("deployment-state")).toHaveTextContent("PAUSED"));
  });
});

describe("paperDeployService contract", () => {
  it("createPaperDeployment hits POST /api/v1/paper/deployments", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => sampleDeployment,
    });
    const originalFetch = globalThis.fetch;
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    try {
      const res = await svc.createPaperDeployment({
        strategyId: "strat-1",
        strategyName: "T",
        accountId: "default",
        allocatedCapital: 100000,
      });
      expect(res.deployment_id).toBe("dep-1");
      expect(String(fetchMock.mock.calls[0][0])).toContain("/api/v1/paper/deployments");
      const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
      expect(body.strategy_id).toBe("strat-1");
      expect(body.account_id).toBe("default");
      expect(body.allocated_capital).toBe(100000);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
