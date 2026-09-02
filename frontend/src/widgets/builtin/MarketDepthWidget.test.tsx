import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
});
