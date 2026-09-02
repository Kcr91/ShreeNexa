import { describe, it, expect } from "vitest";
import {
  calculateMarketBreadth,
  handleMissingWeights,
  getHeatmapTileColor,
} from "./engine";

describe("Market Heatmap Engine", () => {
  it("calculates market breadth, advance/decline ratio, and sentiment posture accurately", () => {
    const items = [
      { changePct: 2.5, weight: 30 },
      { changePct: 1.2, weight: 20 },
      { changePct: -0.8, weight: 25 },
      { changePct: -1.5, weight: 15 },
      { changePct: 0.0, weight: 10 },
    ];

    const breadth = calculateMarketBreadth(items);
    expect(breadth.totalCount).toBe(5);
    expect(breadth.advances).toBe(2);
    expect(breadth.declines).toBe(2);
    expect(breadth.unchanged).toBe(1);
    expect(breadth.advanceDeclineRatio).toBe(1.0);
    expect(breadth.pctAbovePrevClose).toBe(40.0);
    expect(breadth.sentimentPosture).toBe("Moderate Bearish");

    // Weighted breadth check
    // 30*2.5 + 20*1.2 - 25*0.8 - 15*1.5 + 10*0 = 75 + 24 - 20 - 22.5 = 56.5 / 100 = 0.565 -> 0.57
    expect(breadth.weightedBreadth).toBeCloseTo(0.565, 2);
  });

  it("handles deterministic missing weight assignment and guarantees 100% cell totals", () => {
    const rawItems = [
      { symbol: "RELIANCE", sector: "Energy", weight: 30.0, changePct: 1.2, ltp: 2980 },
      { symbol: "TCS", sector: "IT", weight: 25.0, changePct: -0.5, ltp: 4200 },
      { symbol: "HDFCBANK", sector: "Banking", weight: 25.0, changePct: 0.8, ltp: 1640 },
      // The following 2 symbols have missing weights (null or undefined)
      { symbol: "NEWCO1", sector: "Pharma", weight: null, changePct: 2.1, ltp: 450 },
      { symbol: "NEWCO2", sector: "Auto", weight: undefined, changePct: -1.2, ltp: 890 },
    ];

    const result = handleMissingWeights(rawItems);

    // Invariant: cell totals strictly sum to 100.0%
    expect(result.cellTotalWeight).toBe(100.0);
    const sumWeights = result.constituents.reduce((acc, c) => acc + c.weight, 0);
    expect(Math.round(sumWeights)).toBe(100);

    // Invariant: Missing weights are labelled and assigned deterministically
    const newco1 = result.constituents.find((c) => c.symbol === "NEWCO1")!;
    expect(newco1.isWeightFallback).toBe(true);
    expect(newco1.weightingSource).toBe("FALLBACK_EQUAL_WEIGHT");
    expect(newco1.weight).toBeGreaterThan(9); // (100 - 80) / 2 = 10%

    const reliance = result.constituents.find((c) => c.symbol === "RELIANCE")!;
    expect(reliance.isWeightFallback).toBe(false);
    expect(reliance.weightingSource).toBe("OFFICIAL_NSE");
  });

  it("produces appropriate color gradients based on return percentages", () => {
    expect(getHeatmapTileColor(3.5)).toContain("16, 185, 129");
    expect(getHeatmapTileColor(-3.5)).toContain("239, 68, 68");
    expect(getHeatmapTileColor(0.0)).toContain("100, 116, 139");
  });
});
