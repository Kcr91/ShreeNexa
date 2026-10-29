import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyBuilderWidget, strategyBuilderDefinition } from "./StrategyBuilderWidget";
import { widgetRegistry } from "../registry";
import * as backtestService from "../../strategybuilder/backtestService";
import "./index";

const defaultSettings = {
  showJsonPreview: true,
  defaultUniverse: "NIFTY 50",
};

describe("StrategyBuilderWidget Component", () => {
  it("renders strategy builder with header controls and tab bar", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);

    expect(screen.getByLabelText("Strategy Name")).toHaveValue("EMA Golden Cross Momentum");
    // Validation badge appears in header always
    expect(screen.getByTestId("validation-status")).toHaveTextContent("Valid AST");
    // All five tabs present
    expect(screen.getByTestId("tab-setup")).toBeInTheDocument();
    expect(screen.getByTestId("tab-indicators")).toBeInTheDocument();
    expect(screen.getByTestId("tab-conditions")).toBeInTheDocument();
    expect(screen.getByTestId("tab-risk")).toBeInTheDocument();
    expect(screen.getByTestId("tab-preview")).toBeInTheDocument();
  });

  it("shows indicator cards on the Indicators tab", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    fireEvent.click(screen.getByTestId("tab-indicators"));
    expect(screen.getByTestId("indicator-card-fast_ema")).toBeInTheDocument();
    expect(screen.getByTestId("indicator-card-rsi_14")).toBeInTheDocument();
  });

  it("shows rule blocks on the Conditions tab", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    fireEvent.click(screen.getByTestId("tab-conditions"));
    expect(screen.getByTestId("rule-block-rule-entry")).toBeInTheDocument();
    expect(screen.getByTestId("rule-block-rule-exit")).toBeInTheDocument();
  });

  it("renders canonical IR preview on the Preview tab", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    fireEvent.click(screen.getByTestId("tab-preview"));
    expect(screen.getByTestId("strategy-ir-preview")).toHaveTextContent('"ir_version": 1');
    expect(screen.getByText("Copy IR")).toBeInTheDocument();
  });

  it("clicks run vector backtest, calls backend, and renders real metrics card", async () => {
    const sampleResult: backtestService.BacktestResult = {
      backtest_id: "bt-x",
      strategy_name: "T",
      metrics: {
        initial_capital: 100000, final_equity: 112000, total_return_pct: 12, cagr_pct: 12,
        total_pnl: 12000, total_costs: 0, realized_pnl: 12000, unrealized_pnl: 0,
        max_drawdown_pct: 3, max_drawdown_value: 3000, sharpe_ratio: 1.5, sortino_ratio: 2, calmar_ratio: 4,
        total_trades: 10, winning_trades: 6, losing_trades: 4, win_rate_pct: 60, profit_factor: 1.8,
      },
      equity_curve: [
        { timestamp: "2024-01-01T00:00:00Z", equity: 100000, cash: 100000, unrealized_pnl: 0, realized_pnl: 0 },
        { timestamp: "2024-06-01T00:00:00Z", equity: 112000, cash: 100000, unrealized_pnl: 0, realized_pnl: 12000 },
      ],
      trades: [],
      executed_at: "2026-01-01T00:00:00Z",
      engine_commit: "test",
    };
    const spy = vi.spyOn(backtestService, "runBacktest").mockResolvedValue(sampleResult);

    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    const runBtn = screen.getByRole("button", { name: /Run Vector Backtest/i });
    fireEvent.click(runBtn);
    await waitFor(() => expect(spy).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("backtest-result-card")).toBeInTheDocument());
    expect(screen.getByText(/Backtest Complete \(12\.00%\)/i)).toBeInTheDocument();
    expect(screen.getByTestId("equity-sparkline")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("renders error state when backtest service fails", async () => {
    const { ApiError } = await import("../../api/client");
    const spy = vi.spyOn(backtestService, "runBacktest").mockRejectedValue(
      new ApiError("Backend not available. Please ensure the server is running.", 0)
    );
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    fireEvent.click(screen.getByRole("button", { name: /Run Vector Backtest/i }));
    await waitFor(() => expect(screen.getByTestId("backtest-error")).toBeInTheDocument());
    expect(screen.getByTestId("backtest-error")).toHaveTextContent(/Backend not available/i);
    spy.mockRestore();
  });

  it("adds a new EMA indicator via quick-add button", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    fireEvent.click(screen.getByTestId("tab-indicators"));
    const addEmaBtn = screen.getByRole("button", { name: "+EMA" });
    fireEvent.click(addEmaBtn);
    expect(screen.getByTestId("indicator-card-ema_3")).toBeInTheDocument();
  });

  it("opens the AI Strategy Assistant modal when clicking AI Assistant button", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    const aiBtn = screen.getByTestId("btn-ai-assistant");
    fireEvent.click(aiBtn);
    expect(screen.getByTestId("ai-draft-modal")).toBeInTheDocument();
    expect(screen.getByTestId("badge-draft-status")).toHaveTextContent("Status: DRAFT ONLY");
  });

  it("shows Options tab only when strategy kind is 'option'", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    // Default kind is "stock" so Options tab is hidden
    expect(screen.queryByTestId("tab-options")).toBeNull();

    // Switch to option kind via the Setup panel
    fireEvent.click(screen.getByTestId("tab-setup"));
    const kindSelect = screen.getByLabelText("Strategy Kind") as HTMLSelectElement;
    fireEvent.change(kindSelect, { target: { value: "option" } });

    expect(screen.getByTestId("tab-options")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("tab-options"));
    expect(screen.getByTestId("option-config-panel")).toBeInTheDocument();
  });

  it("opens the PDF import modal from the header button", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    fireEvent.click(screen.getByTestId("btn-pdf-import"));
    expect(screen.getByTestId("pdf-extractor-modal")).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("strategy-builder")).toBeDefined();
    expect(widgetRegistry.get("strategy-builder")?.title).toBe("Visual Strategy Builder");
    expect(strategyBuilderDefinition.category).toBe("analytics");
  });
});
