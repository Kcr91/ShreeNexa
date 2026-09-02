import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BlotterWidget, blotterDefinition } from "./BlotterWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("BlotterWidget Component", () => {
  it("renders portfolio summary strip and open positions table", () => {
    render(
      <BlotterWidget
        instanceId="blotter-1"
        settings={{
          defaultTab: "POSITIONS",
          refreshIntervalMs: 1000,
          showRealizedPnl: true,
        }}
      />
    );

    expect(screen.getByText("Unrealized:")).toBeInTheDocument();
    expect(screen.getByText("Net Day PnL:")).toBeInTheDocument();
    expect(screen.getByTestId("position-row-RELIANCE")).toBeInTheDocument();
    expect(screen.getByTestId("position-row-TCS")).toBeInTheDocument();
  });

  it("switches to open orders tab and cancels a single working order", () => {
    render(
      <BlotterWidget
        instanceId="blotter-1"
        settings={{
          defaultTab: "POSITIONS",
          refreshIntervalMs: 1000,
          showRealizedPnl: true,
        }}
      />
    );

    // Switch to Open Orders Tab using data-testid
    const ordersTab = screen.getByTestId("blotter-tab-open-orders");
    fireEvent.click(ordersTab);

    expect(screen.getByTestId("order-row-ORD-90211")).toBeInTheDocument();

    // Cancel ORD-90211
    const cancelBtn = screen.getByLabelText("Cancel ORD-90211");
    fireEvent.click(cancelBtn);

    expect(screen.getByTestId("order-row-ORD-90211")).toHaveTextContent("CANCELLED");
  });

  it("executes cancel-all panic button and cancels all working orders simultaneously", () => {
    render(
      <BlotterWidget
        instanceId="blotter-1"
        settings={{
          defaultTab: "POSITIONS",
          refreshIntervalMs: 1000,
          showRealizedPnl: true,
        }}
      />
    );

    // Click Panic Button
    const panicBtn = screen.getByRole("button", { name: /Cancel All Open Orders/i });
    fireEvent.click(panicBtn);

    // Displays panic execution alert
    expect(screen.getByRole("alert")).toHaveTextContent(/Panic action executed: 2 open orders canceled/i);

    // Open Orders tab reflects cancellations
    const ordersTab = screen.getByTestId("blotter-tab-open-orders");
    fireEvent.click(ordersTab);

    expect(screen.getByTestId("order-row-ORD-90211")).toHaveTextContent("CANCELLED");
    expect(screen.getByTestId("order-row-ORD-90212")).toHaveTextContent("CANCELLED");
  });

  it("is registered in widget registry under order category", () => {
    expect(widgetRegistry.get("blotter")).toBeDefined();
    expect(widgetRegistry.get("blotter")?.title).toBe("Positions & Orders Blotter");
    expect(blotterDefinition.category).toBe("order");
  });
});
