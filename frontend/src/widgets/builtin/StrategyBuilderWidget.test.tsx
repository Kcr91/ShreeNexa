import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StrategyBuilderWidget, strategyBuilderDefinition } from "./StrategyBuilderWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("StrategyBuilderWidget Component", () => {
  it("renders strategy builder workspace with indicator cards and rule blocks", () => {
    render(
      <StrategyBuilderWidget
        instanceId="builder-1"
        settings={{
          showJsonPreview: true,
          defaultUniverse: "NIFTY 50",
        }}
      />
    );

    expect(screen.getByLabelText("Strategy Name")).toHaveValue("EMA Golden Cross Momentum");
    expect(screen.getByTestId("indicator-card-fast_ema")).toBeInTheDocument();
    expect(screen.getByTestId("rule-block-rule-entry")).toBeInTheDocument();
    expect(screen.getByTestId("strategy-ir-preview")).toHaveTextContent('"ir_version": 1');
  });

  it("clicks run vector backtest button and renders results card", () => {
    render(
      <StrategyBuilderWidget
        instanceId="builder-1"
        settings={{
          showJsonPreview: true,
          defaultUniverse: "NIFTY 50",
        }}
      />
    );

    const runBtn = screen.getByRole("button", { name: /Run Vector Backtest/i });
    fireEvent.click(runBtn);

    expect(screen.getByTestId("backtest-result-card")).toBeInTheDocument();
    expect(screen.getByText(/Backtest Complete/i)).toBeInTheDocument();
  });

  it("adds a new EMA indicator to the pipeline", () => {
    render(
      <StrategyBuilderWidget
        instanceId="builder-1"
        settings={{
          showJsonPreview: true,
          defaultUniverse: "NIFTY 50",
        }}
      />
    );

    const addEmaBtn = screen.getByRole("button", { name: "+EMA" });
    fireEvent.click(addEmaBtn);

    expect(screen.getByTestId("indicator-card-ema_3")).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("strategy-builder")).toBeDefined();
    expect(widgetRegistry.get("strategy-builder")?.title).toBe("Visual Strategy Builder");
    expect(strategyBuilderDefinition.category).toBe("analytics");
  });
});
