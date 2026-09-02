import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OrderTicketWidget, orderTicketDefinition } from "./OrderTicketWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("OrderTicketWidget Component", () => {
  it("renders stock ticket, displays margin preview, and places paper order", () => {
    render(
      <OrderTicketWidget
        instanceId="ticket-1"
        settings={{
          defaultAssetClass: "EQUITY",
          defaultSymbol: "RELIANCE",
          defaultQuantity: 25,
        }}
      />
    );

    expect(screen.getByText("Equity Stock")).toBeInTheDocument();
    expect(screen.getByText("Required Margin:")).toBeInTheDocument();

    // Click submit order button
    const submitBtn = screen.getByRole("button", { name: /Submit PAPER Order/i });
    fireEvent.click(submitBtn);

    // Displays success message
    expect(screen.getByRole("alert")).toHaveTextContent(/submitted successfully/i);
  });

  it("switches to multi-leg option builder, adds legs, and displays hedging margin", () => {
    render(
      <OrderTicketWidget
        instanceId="ticket-1"
        settings={{
          defaultAssetClass: "OPTION",
          defaultSymbol: "NIFTY",
          defaultQuantity: 50,
        }}
      />
    );

    // Switch to Multi-Leg Options
    const optTab = screen.getByRole("button", { name: "Multi-Leg Options" });
    fireEvent.click(optTab);

    expect(screen.getByText("Underlying Index")).toBeInTheDocument();
    expect(screen.getByText("Hedging Benefit Offset:")).toBeInTheDocument();

    // Click + Add Leg
    const addLegBtn = screen.getByRole("button", { name: "+ Add Leg" });
    fireEvent.click(addLegBtn);

    expect(screen.getByText("Option Legs (3)")).toBeInTheDocument();
  });

  it("blocks live order placement with safety gate alert", () => {
    render(
      <OrderTicketWidget
        instanceId="ticket-1"
        settings={{
          defaultAssetClass: "EQUITY",
          defaultSymbol: "TCS",
          defaultQuantity: 10,
        }}
      />
    );

    // Select LIVE mode
    const modeSelect = screen.getByLabelText("Execution Mode");
    fireEvent.change(modeSelect, { target: { value: "LIVE" } });

    // Submit live order
    const submitBtn = screen.getByRole("button", { name: /Submit LIVE Order/i });
    fireEvent.click(submitBtn);

    // Displays safety block message
    expect(screen.getByRole("alert")).toHaveTextContent(/Live execution locked/i);
  });

  it("is registered in widget registry under order category", () => {
    expect(widgetRegistry.get("order-ticket")).toBeDefined();
    expect(widgetRegistry.get("order-ticket")?.title).toBe("Order Ticket & Leg Builder");
    expect(orderTicketDefinition.category).toBe("order");
  });
});
