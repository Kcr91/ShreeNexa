import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  ReturnsTimelineWidget,
  returnsTimelineDefinition,
} from "./ReturnsTimelineWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("ReturnsTimelineWidget Component", () => {
  it("renders continuous timeline view with phase demarcation slices", () => {
    render(
      <ReturnsTimelineWidget
        instanceId="returns-1"
        settings={{
          activePhaseFilter: "ALL",
          initialCapital: 1000000,
        }}
      />
    );

    expect(screen.getByTestId("total-return-metric")).toBeInTheDocument();
    expect(screen.getByTestId("phase-card-backtest")).toBeInTheDocument();
    expect(screen.getByTestId("phase-card-paper")).toBeInTheDocument();
    expect(screen.getByTestId("phase-card-live")).toBeInTheDocument();
    expect(screen.getByText(/Strict Non-Overlapping Invariant Enforced/i)).toBeInTheDocument();
  });

  it("switches to Monthly Heatmap tab and renders monthly returns matrix", () => {
    render(
      <ReturnsTimelineWidget
        instanceId="returns-1"
        settings={{
          activePhaseFilter: "ALL",
          initialCapital: 1000000,
        }}
      />
    );

    const monthlyTab = screen.getByTestId("tab-monthly");
    fireEvent.click(monthlyTab);

    expect(
      screen.getByText("Monthly & Compounded Annual Return Matrix")
    ).toBeInTheDocument();
    expect(screen.getByText("YTD")).toBeInTheDocument();
    expect(screen.getByText("Jan")).toBeInTheDocument();
  });

  it("switches to Rolling Returns tab and renders distribution statistics", () => {
    render(
      <ReturnsTimelineWidget
        instanceId="returns-1"
        settings={{
          activePhaseFilter: "ALL",
          initialCapital: 1000000,
        }}
      />
    );

    const rollingTab = screen.getByTestId("tab-rolling");
    fireEvent.click(rollingTab);

    expect(
      screen.getByText("Rolling Returns Performance Distribution")
    ).toBeInTheDocument();
    expect(screen.getByText(/1M \(21 Trading Days\)/i)).toBeInTheDocument();
    expect(screen.getByText(/3M \(63 Trading Days\)/i)).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("returns-timeline")).toBeDefined();
    expect(widgetRegistry.get("returns-timeline")?.title).toBe(
      "Returns & Timeline"
    );
    expect(returnsTimelineDefinition.category).toBe("analytics");
  });
});
