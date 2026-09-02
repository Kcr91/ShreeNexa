import { describe, it, expect } from "vitest";
import {
  calculateCumulativeDepth,
  resolveSegmentDepthCapability,
  computeOrderBookImbalance,
  generateMockDepthBook,
} from "./engine";

describe("Market Depth Engine", () => {
  it("calculates strictly monotonic cumulative quantities", () => {
    const raw = [
      { price: 100.0, quantity: 150, orders: 3 },
      { price: 99.5, quantity: 200, orders: 5 },
      { price: 99.0, quantity: 350, orders: 8 },
    ];
    const res = calculateCumulativeDepth(raw);
    expect(res).toHaveLength(3);
    expect(res[0].cumulativeQty).toBe(150);
    expect(res[1].cumulativeQty).toBe(350);
    expect(res[2].cumulativeQty).toBe(700);

    for (let i = 1; i < res.length; i++) {
      expect(res[i].cumulativeQty).toBeGreaterThan(res[i - 1].cumulativeQty);
    }
  });

  it("handles 20-level and 200-level depth on supported NSE segments", () => {
    const book20 = generateMockDepthBook("RELIANCE", "NSE_EQ", "LEVEL_20", 2980.0);
    expect(book20.depthLevelType).toBe("LEVEL_20");
    expect(book20.isFallback).toBe(false);
    expect(book20.bids).toHaveLength(20);
    expect(book20.asks).toHaveLength(20);
    expect(book20.connectionCost).toContain("Shared Socket Pool");

    const book200 = generateMockDepthBook("NIFTY_FUT", "NSE_FNO", "LEVEL_200", 25200.0);
    expect(book200.depthLevelType).toBe("LEVEL_200");
    expect(book200.isFallback).toBe(false);
    expect(book200.bids).toHaveLength(200);
    expect(book200.asks).toHaveLength(200);
    expect(book200.connectionCost).toContain("Dedicated Socket");
  });

  it("falls back to 5-level depth on unsupported BSE/MCX segments with explicit explanation", () => {
    const bseRes = resolveSegmentDepthCapability("BSE_EQ", "LEVEL_20");
    expect(bseRes.actualLevel).toBe("LEVEL_5");
    expect(bseRes.isFallback).toBe(true);
    expect(bseRes.fallbackReason).toContain("Exchange limitation");

    const mcxBook = generateMockDepthBook("GOLD_FUT", "MCX_COMM", "LEVEL_200", 74000.0);
    expect(mcxBook.depthLevelType).toBe("LEVEL_5");
    expect(mcxBook.isFallback).toBe(true);
    expect(mcxBook.bids).toHaveLength(5);
    expect(mcxBook.asks).toHaveLength(5);
    expect(mcxBook.fallbackReason).toContain("Exchange limitation");
  });

  it("computes bounded order book imbalance ratio", () => {
    const bids = calculateCumulativeDepth([
      { price: 100, quantity: 300, orders: 1 },
      { price: 99, quantity: 200, orders: 1 },
    ]);
    const asks = calculateCumulativeDepth([
      { price: 101, quantity: 100, orders: 1 },
      { price: 102, quantity: 150, orders: 1 },
    ]);

    // Total bids = 500, total asks = 250 -> (500 - 250) / 750 = 250 / 750 = 0.3333
    const imb = computeOrderBookImbalance(bids, asks);
    expect(imb).toBe(0.3333);
    expect(imb).toBeGreaterThanOrEqual(-1.0);
    expect(imb).toBeLessThanOrEqual(1.0);
  });
});
