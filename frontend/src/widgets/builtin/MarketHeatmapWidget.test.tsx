import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MarketHeatmapWidget } from "./MarketHeatmapWidget";

describe("MarketHeatmapWidget Component", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders index-level heatmap with breadth metrics", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Mode buttons
    expect(screen.getByText("Sectoral Indices")).toBeInTheDocument();
    expect(screen.getByText("Constituents Drill-In")).toBeInTheDocument();

    // Breadth summary bar is present
    expect(screen.getByText(/Adv/i)).toBeInTheDocument();
    expect(screen.getByText(/Dec/i)).toBeInTheDocument();
    expect(screen.getByText(/Above Prev Close:/i)).toBeInTheDocument();

    // Indices are rendered
    expect(screen.getByText("NIFTY 50")).toBeInTheDocument();
    expect(screen.getByText("NIFTY BANK")).toBeInTheDocument();
    expect(screen.getByText("NIFTY IT")).toBeInTheDocument();
  });

  it("switches to constituents drill-in and renders stock cells with fallback weight labels", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Click Constituents Drill-In tab
    const constituentTab = screen.getByText("Constituents Drill-In");
    fireEvent.click(constituentTab);

    // Constituents render
    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByText("HDFCBANK")).toBeInTheDocument();

    // Symbols with missing weights show "Fallback Wt" label
    const fallbackBadges = screen.getAllByText("Fallback Wt");
    expect(fallbackBadges.length).toBeGreaterThan(0);
  });

  it("drills down into constituent view when clicking an index tile", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Click on NIFTY BANK tile in index view
    const bankTile = screen.getByText("NIFTY BANK");
    fireEvent.click(bankTile);

    // Should now show NIFTY BANK constituents
    expect(screen.getByText("KOTAKBANK")).toBeInTheDocument();
    expect(screen.getByText("INDUSINDBK")).toBeInTheDocument();
  });
});
