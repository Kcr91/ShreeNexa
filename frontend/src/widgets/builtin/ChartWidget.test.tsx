import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChartWidget, chartDefinition } from "./ChartWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("ChartWidget Component and Toolbar", () => {
  it("renders chart toolbar with symbol and timeframe buttons", () => {
    const handleUpdate = vi.fn();
    render(
      <ChartWidget
        instanceId="chart-1"
        settings={{
          symbol: "RELIANCE",
          timeframe: "5m",
          showSessionBreaks: true,
          showVolume: true,
        }}
        onUpdateSettings={handleUpdate}
      />
    );

    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "15m" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SMA 20" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "EMA 50" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "RSI 14" })).toBeInTheDocument();
  });

  it("updates timeframe when clicking timeframe button", () => {
    const handleUpdate = vi.fn();
    render(
      <ChartWidget
        instanceId="chart-1"
        settings={{
          symbol: "TCS",
          timeframe: "5m",
          showSessionBreaks: true,
          showVolume: true,
        }}
        onUpdateSettings={handleUpdate}
      />
    );

    const btn15m = screen.getByRole("button", { name: "15m" });
    fireEvent.click(btn15m);

    expect(handleUpdate).toHaveBeenCalledWith({ timeframe: "15m" });
  });

  it("is registered in widget registry under chart category", () => {
    expect(widgetRegistry.get("chart")).toBeDefined();
    expect(widgetRegistry.get("chart")?.title).toBe("Candlestick Chart");
    expect(chartDefinition.category).toBe("chart");
  });
});
