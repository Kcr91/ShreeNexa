import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MarketDepthCard } from "./MarketDepthCard";

describe("MarketDepthCard Component", () => {
  const mockMphasis = {
    symbol: "MPHASIS",
    tradingSymbol: "MPHASIS-EQ",
    name: "Mphasis Ltd",
    ltp: 2357.10,
    changePct: -2.68,
    changeAbs: -64.90,
    open: 2409.90,
    prevClose: 2422.00,
    high: 2409.90,
    low: 2340.30,
    volume: 366195,
    avgPrice: 2359.56,
    lowerCircuit: 2179.80,
    upperCircuit: 2664.20,
    ltq: 3,
    ltt: "2026-09-07 11:40:03",
    fiftyTwoWeekHigh: 3125.00,
    fiftyTwoWeekLow: 2180.00,
  };

  it("renders MPHASIS header with exact screenshot numbers and negative accent", () => {
    render(<MarketDepthCard item={mockMphasis} />);

    expect(screen.getByText("MPHASIS")).toBeInTheDocument();
    expect(screen.getByText("-64.90")).toBeInTheDocument();
    expect(screen.getByText(/-2.68%/i)).toBeInTheDocument();
    expect(screen.getAllByText("2357.10").length).toBe(2); // Header LTP and Best Bid Price
  });

  it("renders 5-level bids and offers with exact totals from screenshot", () => {
    render(<MarketDepthCard item={mockMphasis} />);

    // Check depth columns
    expect(screen.getByText("Bid")).toBeInTheDocument();
    expect(screen.getByText("Offer")).toBeInTheDocument();

    // Check bid and ask totals
    expect(screen.getByTestId("total-bid-qty")).toHaveTextContent("35,801");
    expect(screen.getByTestId("total-ask-qty")).toHaveTextContent("23,606");

    // Check depth rows
    expect(screen.getByText("2357.50")).toBeInTheDocument();
    expect(screen.getByText("99")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
  });

  it("renders Open, Prev Close, Low, High, Volume, Avg price, Circuits, and 52W metrics", () => {
    render(<MarketDepthCard item={mockMphasis} />);

    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getAllByText("2,409.90").length).toBe(2); // Open and High have 2,409.90
    expect(screen.getByText("Prev. Close")).toBeInTheDocument();
    expect(screen.getByText("2,422.00")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
    expect(screen.getByText("2,340.30")).toBeInTheDocument();

    expect(screen.getByText("Volume")).toBeInTheDocument();
    expect(screen.getByText("3,66,195")).toBeInTheDocument();
    expect(screen.getByText("Avg. price")).toBeInTheDocument();
    expect(screen.getByText("2,359.56")).toBeInTheDocument();
    expect(screen.getByText("Lower circuit")).toBeInTheDocument();
    expect(screen.getByText("2,179.80")).toBeInTheDocument();
    expect(screen.getByText("Upper circuit")).toBeInTheDocument();
    expect(screen.getByText("2,664.20")).toBeInTheDocument();

    expect(screen.getByText("LTQ")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("LTT")).toBeInTheDocument();
    expect(screen.getByText("2026-09-07 11:40:03")).toBeInTheDocument();

    // 52W Low & High with % distance
    expect(screen.getByText("52W Low")).toBeInTheDocument();
    expect(screen.getByText("52W High")).toBeInTheDocument();
    expect(screen.getByText(/\(\+8\.1%\)/)).toBeInTheDocument();
    expect(screen.getByText(/\(-24\.6%\)/)).toBeInTheDocument();
  });

  it("expands to 20-level NSE bid and ask list when clicking down arrow in bid and ask section", () => {
    render(<MarketDepthCard item={mockMphasis} />);

    // Initially, exactly 5 bid/offer rows are displayed
    expect(screen.getAllByTestId("depth-row").length).toBe(5);
    expect(screen.getByText("Show 20 depth")).toBeInTheDocument();
    expect(screen.getByText("Volume")).toBeInTheDocument();

    // Click the down arrow toggle in bid and ask section
    const chevron = screen.getByTestId("depth-collapse-toggle");
    fireEvent.click(chevron);

    // Should now display all 20 NSE bid/ask rows
    expect(screen.getAllByTestId("depth-row").length).toBe(20);
    expect(screen.getByText("Show 5 depth")).toBeInTheDocument();
    expect(screen.getByText("20-Level Full Depth (NSE)")).toBeInTheDocument();

    // Market statistics remain visible
    expect(screen.getByText("Volume")).toBeInTheDocument();

    // Click again to collapse back to 5 depth
    fireEvent.click(chevron);
    expect(screen.getAllByTestId("depth-row").length).toBe(5);
    expect(screen.getByText("Show 20 depth")).toBeInTheDocument();
  });
});
