import { describe, expect, it } from "vitest";
import { computePositionPnl, computePortfolioSummary } from "./pnl";
import { PositionItem } from "./types";

describe("Blotter Mark-to-Market PnL Calculations", () => {
  it("computes individual position unrealized PnL accurately for long and short positions", () => {
    // Long Position: Bought 50 RELIANCE @ 2900, LTP = 2950
    const longPos: PositionItem = {
      symbol: "RELIANCE",
      product: "CNC",
      quantity: 50,
      buyAvgPrice: 2900,
      ltp: 2950,
      dayChange: 0,
      dayChangePct: 0,
      unrealizedPnl: 0,
      realizedPnl: 100,
      totalPnl: 0,
    };
    const updatedLong = computePositionPnl(longPos, 2960);
    // (2960 - 2900) * 50 = +3000
    expect(updatedLong.unrealizedPnl).toBe(3000);
    expect(updatedLong.totalPnl).toBe(3100);
    expect(updatedLong.dayChangePct).toBeCloseTo(2.07, 1);

    // Short Position: Sold 50 NIFTY CE @ 160, LTP = 140
    const shortPos: PositionItem = {
      symbol: "NIFTY 24500 CE",
      product: "NRML",
      quantity: -50,
      buyAvgPrice: 160,
      ltp: 160,
      dayChange: 0,
      dayChangePct: 0,
      unrealizedPnl: 0,
      realizedPnl: 0,
      totalPnl: 0,
    };
    const updatedShort = computePositionPnl(shortPos, 140);
    // (140 - 160) * (-50) = +1000 profit
    expect(updatedShort.unrealizedPnl).toBe(1000);
    expect(updatedShort.totalPnl).toBe(1000);
  });

  it("aggregates portfolio summary totals across multiple positions", () => {
    const positions: PositionItem[] = [
      {
        symbol: "RELIANCE",
        product: "CNC",
        quantity: 50,
        buyAvgPrice: 2900,
        ltp: 2960,
        dayChange: 60,
        dayChangePct: 2.07,
        unrealizedPnl: 3000,
        realizedPnl: 500,
        totalPnl: 3500,
      },
      {
        symbol: "TCS",
        product: "MIS",
        quantity: 20,
        buyAvgPrice: 4200,
        ltp: 4150,
        dayChange: -50,
        dayChangePct: -1.19,
        unrealizedPnl: -1000,
        realizedPnl: 0,
        totalPnl: -1000,
      },
    ];

    const summary = computePortfolioSummary(positions, 2);
    expect(summary.totalUnrealizedPnl).toBe(2000);
    expect(summary.totalRealizedPnl).toBe(500);
    expect(summary.netPnl).toBe(2500);
    expect(summary.openPositionsCount).toBe(2);
    expect(summary.activeOrdersCount).toBe(2);
  });
});
