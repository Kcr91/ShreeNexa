import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StrategyBuilderWidget, strategyBuilderDefinition } from "./StrategyBuilderWidget";
import { widgetRegistry } from "../registry";
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

  it("clicks run vector backtest button and renders results card", () => {
    render(<StrategyBuilderWidget instanceId="builder-1" settings={defaultSettings} />);
    const runBtn = screen.getByRole("button", { name: /Run Vector Backtest/i });
    fireEvent.click(runBtn);
    fireEvent.click(screen.getByTestId("tab-preview"));
    expect(screen.getByTestId("backtest-result-card")).toBeInTheDocument();
    expect(screen.getByText(/Backtest Complete/i)).toBeInTheDocument();
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

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("strategy-builder")).toBeDefined();
    expect(widgetRegistry.get("strategy-builder")?.title).toBe("Visual Strategy Builder");
    expect(strategyBuilderDefinition.category).toBe("analytics");
  });
});
