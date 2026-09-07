import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MarketHeatmapWidget } from "./MarketHeatmapWidget";

describe("MarketHeatmapWidget - NSE India Heatmap Component", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("renders broad market indices by default with official 7-bracket legend and breadth metrics", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Official 4 Category Navigation in Left Panel
    expect(screen.getByRole("button", { name: "Broad Market Indices" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sectoral Indices" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thematic Indices" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Strategy Indices" })).toBeInTheDocument();

    // Header shows Broad Market Indices(21)
    expect(screen.getByText("Broad Market Indices(21)")).toBeInTheDocument();

    // 7-tier NSE color bracket badges
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(screen.getByText("-1")).toBeInTheDocument();
    expect(screen.getByText("-3")).toBeInTheDocument();
    expect(screen.getByText("-5")).toBeInTheDocument();

    // Streaming toggle & Breadth bar
    expect(screen.getByText("Streaming")).toBeInTheDocument();
    expect(screen.getByText(/Adv/i)).toBeInTheDocument();
    expect(screen.getByText(/Dec/i)).toBeInTheDocument();

    // Key Broad Market indices are rendered
    expect(screen.getByText("NIFTY 50")).toBeInTheDocument();
    expect(screen.getByText("NIFTY NEXT 50")).toBeInTheDocument();
    expect(screen.getByText("NIFTY MIDCAP 50")).toBeInTheDocument();
    expect(screen.getByText("NIFTY 100")).toBeInTheDocument();
    expect(screen.getByText("NIFTY 500")).toBeInTheDocument();
  });

  it("switches to Sectoral Indices and displays all 23 sectoral indices", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Click Sectoral Indices in the left navigation panel
    const sectoralBtn = screen.getByRole("button", { name: "Sectoral Indices" });
    fireEvent.click(sectoralBtn);

    // Header updates to Sectoral Indices(23)
    expect(screen.getByText("Sectoral Indices(23)")).toBeInTheDocument();

    // Sectoral indices rendered
    expect(screen.getByText("NIFTY BANK")).toBeInTheDocument();
    expect(screen.getByText("NIFTY IT")).toBeInTheDocument();
    expect(screen.getByText("NIFTY AUTO")).toBeInTheDocument();
    expect(screen.getByText("NIFTY PHARMA")).toBeInTheDocument();
    expect(screen.getByText("NIFTY FMCG")).toBeInTheDocument();
    expect(screen.getByText("NIFTY METAL")).toBeInTheDocument();
  });

  it("switches to Thematic Indices and displays all 39 thematic indices", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Click Thematic Indices in the left navigation panel
    const thematicBtn = screen.getByRole("button", { name: "Thematic Indices" });
    fireEvent.click(thematicBtn);

    // Header updates to Thematic Indices(39)
    expect(screen.getByText("Thematic Indices(39)")).toBeInTheDocument();

    // Key thematic indices rendered
    expect(screen.getByText("NIFTY COMMODITIES")).toBeInTheDocument();
    expect(screen.getByText("NIFTY CPSE")).toBeInTheDocument();
    expect(screen.getByText("NIFTY ENERGY")).toBeInTheDocument();
    expect(screen.getByText("NIFTY INFRA")).toBeInTheDocument();
    expect(screen.getByText("NIFTY PSE")).toBeInTheDocument();
  });

  it("drills down into constituent view when clicking an index tile, showing all constituent stocks and navigation panel", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Click on NIFTY 50 card in overview
    const nifty50Tile = screen.getByText("NIFTY 50");
    fireEvent.click(nifty50Tile);

    // Header should now show NIFTY 50(50) and Back button
    expect(screen.getByText("NIFTY 50(50)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "← Back" })).toBeInTheDocument();

    // Left navigation panel in constituent mode lists the indices in this category
    expect(screen.getByRole("button", { name: "← Categories" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "NIFTY NEXT 50" })).toBeInTheDocument();

    // Constituent stocks for Nifty 50 matching Image 4
    expect(screen.getByText("APOLLOHOSP")).toBeInTheDocument();
    expect(screen.getByText("LT")).toBeInTheDocument();
    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByText("HDFCBANK")).toBeInTheDocument();
    expect(screen.getByText("INFY")).toBeInTheDocument();

    // Clicking Back button returns to the Category overview
    const backBtn = screen.getByRole("button", { name: "← Back" });
    fireEvent.click(backBtn);

    expect(screen.getByText("Broad Market Indices(21)")).toBeInTheDocument();
  });

  it("switches constituent stocks when selecting another index from the left navigation panel", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Drill down into NIFTY 50
    fireEvent.click(screen.getByText("NIFTY 50"));
    expect(screen.getByText("NIFTY 50(50)")).toBeInTheDocument();

    // In left navigation panel, click NIFTY NEXT 50
    const next50NavBtn = screen.getByRole("button", { name: "NIFTY NEXT 50" });
    fireEvent.click(next50NavBtn);

    // View updates to NIFTY NEXT 50
    expect(screen.getByText(/NIFTY NEXT 50\(\d+\)/)).toBeInTheDocument();
  });

  it("dispatches symbol select event when clicking a constituent stock card", () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // Drill into NIFTY 50
    fireEvent.click(screen.getByText("NIFTY 50"));

    // Click RELIANCE stock tile
    const relianceTile = screen.getByText("RELIANCE");
    fireEvent.click(relianceTile);

    expect(dispatchSpy).toHaveBeenCalled();
    const event = dispatchSpy.mock.calls.find(
      (call) => (call[0] as CustomEvent).type === "shreenexa:select-symbol"
    );
    expect(event).toBeDefined();
    expect((event?.[0] as CustomEvent).detail).toEqual({ symbol: "RELIANCE" });
  });

  it("toggles streaming on and off", () => {
    render(<MarketHeatmapWidget instanceId="inst-heatmap-test" settings={{}} />);

    // By default streaming is On
    const streamingBtn = screen.getByRole("button", { name: "On" });
    expect(streamingBtn).toBeInTheDocument();

    // Toggle off
    fireEvent.click(streamingBtn);
    expect(screen.getByRole("button", { name: "Off" })).toBeInTheDocument();

    // Toggle back on
    fireEvent.click(screen.getByRole("button", { name: "Off" }));
    expect(screen.getByRole("button", { name: "On" })).toBeInTheDocument();
  });
});
