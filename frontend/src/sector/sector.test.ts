import { describe, it, expect } from "vitest";
import { fetchSectorCatalog, fetchIndexDrillIn } from "./api";

describe("Sector Catalog and Index Drill-In API Client", () => {
  it("fetches sector catalog with recognized sectors", async () => {
    const catalog = await fetchSectorCatalog();
    expect(catalog.length).toBeGreaterThanOrEqual(8);
    const sectors = catalog.map((c) => c.sector);
    expect(sectors).toContain("Banking");
    expect(sectors).toContain("Information Technology");
    expect(sectors).toContain("Automotive");
  });

  it("fetches constituents drill-in and computes sector distribution", async () => {
    const drillIn = await fetchIndexDrillIn("NIFTY IT");
    expect(drillIn.index_name).toBe("NIFTY IT");
    expect(drillIn.total_constituents).toBeGreaterThan(0);
    expect(drillIn.constituents.some((c) => c.symbol === "TCS")).toBe(true);
    expect(drillIn.constituents.some((c) => c.symbol === "INFY")).toBe(true);

    // Provenance and fallback visibility
    expect(drillIn.provenance_sources).toBeDefined();
    expect(drillIn.has_fallback).toBe(true);
    expect(drillIn.sector_weights["Information Technology"]).toBeGreaterThan(50);
  });

  it("handles historical date queries", async () => {
    const drillIn = await fetchIndexDrillIn("NIFTY BANK", "2024-01-01");
    expect(drillIn.index_name).toBe("NIFTY BANK");
    expect(drillIn.as_of).toBe("2024-01-01");
    expect(drillIn.constituents.some((c) => c.symbol === "HDFCBANK")).toBe(true);
  });
});
