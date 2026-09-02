import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PnlCalendarWidget, pnlCalendarDefinition } from "./PnlCalendarWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("PnlCalendarWidget Component", () => {
  it("renders monthly PnL grid with scorecard and navigation", () => {
    render(
      <PnlCalendarWidget
        instanceId="calendar-1"
        settings={{
          defaultMonth: "2026-08",
          showCharges: true,
          showWeekends: true,
        }}
      />
    );

    expect(screen.getByText("August 2026")).toBeInTheDocument();
    expect(screen.getByTestId("month-net-pnl")).toBeInTheDocument();
    expect(screen.getByText("Mon")).toBeInTheDocument();

    const nextBtn = screen.getByRole("button", { name: "Next ›" });
    fireEvent.click(nextBtn);
    expect(screen.getByText("September 2026")).toBeInTheDocument();
  });

  it("clicks a trading day tile and opens day trade book drilldown", () => {
    render(
      <PnlCalendarWidget
        instanceId="calendar-1"
        settings={{
          defaultMonth: "2026-08",
          showCharges: true,
          showWeekends: true,
        }}
      />
    );

    // Click first trading day (2026-08-03 or available)
    const tradingDayTile = screen.getAllByTestId(/trading-day-tile-/)[0];
    fireEvent.click(tradingDayTile);

    expect(screen.getByTestId("day-drilldown-panel")).toBeInTheDocument();
    expect(screen.getByText("Trade Book Reconciliations")).toBeInTheDocument();
    expect(screen.getByText(/NIFTY 24500 CE/i)).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("pnl-calendar")).toBeDefined();
    expect(widgetRegistry.get("pnl-calendar")?.title).toBe("P&L Calendar");
    expect(pnlCalendarDefinition.category).toBe("analytics");
  });
});
