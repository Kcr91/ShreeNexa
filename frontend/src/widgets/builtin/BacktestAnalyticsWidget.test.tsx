import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BacktestAnalyticsWidget, backtestAnalyticsDefinition } from "./BacktestAnalyticsWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("BacktestAnalyticsWidget Component", () => {
  it("renders tear sheet scorecard metrics and strategy grade badge", () => {
    render(
      <BacktestAnalyticsWidget
        instanceId="analytics-1"
        settings={{
          defaultMetricView: "SCORECARD",
          showBenchmark: true,
        }}
      />
    );

    expect(screen.getByText("Sharpe Ratio")).toBeInTheDocument();
    expect(screen.getByText("Sortino Ratio")).toBeInTheDocument();
    expect(screen.getByText("CAGR")).toBeInTheDocument();
    expect(screen.getByText("Max Drawdown")).toBeInTheDocument();
    expect(screen.getByTestId("strategy-grade-badge")).toHaveTextContent("GRADE A");
  });

  it("switches to monthly heatmap tab and displays years matrix", () => {
    render(
      <BacktestAnalyticsWidget
        instanceId="analytics-1"
        settings={{
          defaultMetricView: "SCORECARD",
          showBenchmark: true,
        }}
      />
    );

    const heatmapTab = screen.getByTestId("analytics-tab-heatmap");
    fireEvent.click(heatmapTab);

    expect(screen.getByText("2025")).toBeInTheDocument();
    expect(screen.getByText("2024")).toBeInTheDocument();
  });

  it("switches to equity curve and underwater drawdown tabs", () => {
    render(
      <BacktestAnalyticsWidget
        instanceId="analytics-1"
        settings={{
          defaultMetricView: "SCORECARD",
          showBenchmark: true,
        }}
      />
    );

    const equityTab = screen.getByTestId("analytics-tab-equity");
    fireEvent.click(equityTab);
    expect(screen.getByTestId("equity-curve-view")).toBeInTheDocument();

    const underwaterTab = screen.getByTestId("analytics-tab-underwater");
    fireEvent.click(underwaterTab);
    expect(screen.getByTestId("underwater-chart-view")).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("backtest-analytics")).toBeDefined();
    expect(widgetRegistry.get("backtest-analytics")?.title).toBe("Backtest Analytics & Scorecard");
    expect(backtestAnalyticsDefinition.category).toBe("analytics");
  });
});
