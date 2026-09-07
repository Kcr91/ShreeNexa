import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { MarketDepthWidget } from "./MarketDepthWidget";

describe("MarketDepthWidget Component", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders 20-level depth ladder with cumulative sums, spread, and imbalance footer", () => {
    render(<MarketDepthWidget instanceId="inst-depth-test" settings={{}} />);

    // Tab buttons
    expect(screen.getByText("Depth Ladder")).toBeInTheDocument();
    expect(screen.getByText(/Depth Watchlist/i)).toBeInTheDocument();

    // Table header columns
    expect(screen.getAllByText("Cum Qty").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Bid Price")).toBeInTheDocument();
    expect(screen.getByText("Ask Price")).toBeInTheDocument();

    // Total book summary footer
    expect(screen.getByText(/Total Bids:/i)).toBeInTheDocument();
    expect(screen.getByText(/Total Asks:/i)).toBeInTheDocument();
    expect(screen.getByText(/Imbalance:/i)).toBeInTheDocument();
  });

  it("switches to 200-level on-demand mode and surfaces dedicated socket connection cost", () => {
    render(<MarketDepthWidget instanceId="inst-depth-test" settings={{}} />);

    // Click 200L button
    const btn200 = screen.getByText("200L");
    fireEvent.click(btn200);

    // Socket allocation updates to Dedicated Socket
    expect(screen.getByText(/Dedicated Socket/i)).toBeInTheDocument();
  });

  it("switches segment to BSE_EQ and displays 5-level fallback with exchange limitation notice", () => {
    render(<MarketDepthWidget instanceId="inst-depth-test" settings={{}} />);

    // Select BSE_EQ segment
    const segmentSelect = screen.getByDisplayValue("NSE_EQ");
    fireEvent.change(segmentSelect, { target: { value: "BSE_EQ" } });

    // Warning banner is displayed
    expect(screen.getByText(/5-Level Depth Active:/i)).toBeInTheDocument();
    expect(screen.getByText(/Exchange limitation/i)).toBeInTheDocument();
  });

  it("switches to depth watchlist tab and focuses a selected symbol", () => {
    render(<MarketDepthWidget instanceId="inst-depth-test" settings={{}} />);

    // Switch to Watchlist tab
    const wlTab = screen.getByText(/Depth Watchlist/i);
    fireEvent.click(wlTab);

    // Pinned symbols render
    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByText("HDFCBANK")).toBeInTheDocument();
    expect(screen.getByText("BSE_SENSEX")).toBeInTheDocument();

    // Click Focus on HDFCBANK
    const focusBtns = screen.getAllByText("Focus");
    fireEvent.click(focusBtns[1]);

    // Switches back to Ladder view with HDFCBANK focused
    expect(screen.getByDisplayValue("HDFCBANK")).toBeInTheDocument();
  });

  it("switches to 5-Level Depth card view and displays Kite-style depth card", () => {
    render(<MarketDepthWidget instanceId="inst-depth-test" settings={{}} />);

    // Click 5-Level Depth tab button
    const cardBtn = screen.getByText("5-Level Depth");
    fireEvent.click(cardBtn);

    // Bids & asks tables with 5 rows render
    expect(screen.getByText("Total Bid")).toBeInTheDocument();
    expect(screen.getByText("Total Ask")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText("Prev. Close")).toBeInTheDocument();
    expect(screen.getByText("Lower circuit")).toBeInTheDocument();
  });

  it("updates active symbol and renders live price and depth on shreenexa:select-symbol event", () => {
    render(
      <MarketDepthWidget
        instanceId="inst-depth-test"
        settings={{ defaultMode: "CARD" }}
      />
    );

    // Initial symbol is RELIANCE
    expect(screen.getAllByText("RELIANCE").length).toBeGreaterThanOrEqual(1);

    // Dispatch select-symbol event for MPHASIS
    act(() => {
      window.dispatchEvent(
        new CustomEvent("shreenexa:select-symbol", {
          detail: {
            symbol: "MPHASIS",
            segment: "NSE_EQ",
            item: {
              symbol: "MPHASIS",
              segment: "NSE_EQ",
              ltp: 2357.10,
              lastPrice: 2357.10,
              changeAbs: -64.90,
              changePct: -2.68,
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
            },
          },
        })
      );
    });

    // Updates to MPHASIS with exact screenshot values
    expect(screen.getAllByText("MPHASIS").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("2357.10").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("-64.90")).toBeInTheDocument();
    expect(screen.getByText(/-2\.68%/i)).toBeInTheDocument();
    expect(screen.getAllByText("2,409.90").length).toBe(2);
    expect(screen.getByText("3,66,195")).toBeInTheDocument();
  });
});
