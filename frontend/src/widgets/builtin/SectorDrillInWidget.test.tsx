import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SectorDrillInWidget } from "./SectorDrillInWidget";
import { loadWatchlists } from "../../watchlist/storage";

describe("SectorDrillInWidget Component", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders sector drill-in header, controls, and visible fallback badge", async () => {
    render(<SectorDrillInWidget instanceId="inst-sector-test" settings={{}} />);

    // Index / Sector dropdown is present
    expect(screen.getByText("Index / Sector:")).toBeInTheDocument();

    // Provenance badge renders visibly
    await waitFor(() => {
      expect(screen.getByText(/Fallback \/ Stale Snapshot Active/i)).toBeInTheDocument();
    });

    // Constituents render in table
    await waitFor(() => {
      expect(screen.getByText("RELIANCE")).toBeInTheDocument();
      expect(screen.getByText("HDFCBANK")).toBeInTheDocument();
    });
  });

  it("switches to historical date mode", async () => {
    render(<SectorDrillInWidget instanceId="inst-sector-test" settings={{}} />);

    const historicalCheckbox = screen.getByLabelText(/Historical Date/i);
    fireEvent.click(historicalCheckbox);

    // Date picker input appears
    const dateInput = screen.getByDisplayValue("2024-01-01");
    expect(dateInput).toBeInTheDocument();

    // Change date
    fireEvent.change(dateInput, { target: { value: "2023-12-31" } });
    expect(dateInput).toHaveValue("2023-12-31");
  });

  it("exports constituents into a new watchlist", async () => {
    render(<SectorDrillInWidget instanceId="inst-sector-test" settings={{}} />);

    await waitFor(() => {
      expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    });

    const exportBtn = screen.getByText(/Save to Watchlist/i);
    fireEvent.click(exportBtn);

    // Confirmation notice appears
    await waitFor(() => {
      expect(screen.getByText(/Exported \d+ symbols to watchlist/i)).toBeInTheDocument();
    });

    // Check localStorage watchlists
    const watchlists = loadWatchlists();
    expect(watchlists.some((w) => w.name.includes("NIFTY 50"))).toBe(true);
  });
});
