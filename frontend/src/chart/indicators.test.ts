import { describe, expect, it } from "vitest";
import { computeSMA, computeEMA, computeRSI, computeMACD, computeVWAP } from "./indicators";
import { BarData } from "./types";

describe("Chart Vector Indicators Calculation", () => {
  const sampleBars: BarData[] = Array.from({ length: 30 }, (_, i) => ({
    time: `2026-01-${String(i + 1).padStart(2, "0")}`,
    open: 100 + i,
    high: 105 + i,
    low: 95 + i,
    close: 100 + i * 2,
    volume: 1000 + i * 100,
  }));

  it("computes SMA correctly over sliding windows", () => {
    const sma5 = computeSMA(sampleBars, 5);
    expect(sma5.length).toBe(sampleBars.length - 5 + 1);
    // First SMA5 at index 4: closes are 100, 102, 104, 106, 108 -> sum 520 / 5 = 104
    expect(sma5[0].value).toBe(104);
  });

  it("computes EMA correctly with exponential weighting", () => {
    const ema5 = computeEMA(sampleBars, 5);
    expect(ema5.length).toBe(sampleBars.length - 5 + 1);
    expect(ema5[0].value).toBe(104); // Initial seed
    expect(ema5[1].value).toBeGreaterThan(104);
  });

  it("computes RSI correctly within [0, 100] bounds", () => {
    const rsi14 = computeRSI(sampleBars, 14);
    expect(rsi14.length).toBeGreaterThan(0);
    for (const pt of rsi14) {
      expect(pt.value).toBeGreaterThanOrEqual(0);
      expect(pt.value).toBeLessThanOrEqual(100);
    }
  });

  it("computes MACD, signal line, and histogram", () => {
    const macdRes = computeMACD(sampleBars, 5, 15, 5);
    expect(macdRes.macdLine.length).toBeGreaterThan(0);
    expect(macdRes.signalLine.length).toBeGreaterThan(0);
    expect(macdRes.histogram.length).toBeGreaterThan(0);
    expect(macdRes.histogram[0].color).toBeDefined();
  });

  it("computes VWAP weighted by typical price and volume", () => {
    const vwap = computeVWAP(sampleBars);
    expect(vwap.length).toBe(sampleBars.length);
    expect(vwap[0].value).toBeCloseTo((sampleBars[0].high + sampleBars[0].low + sampleBars[0].close) / 3, 1);
  });
});
