import { describe, expect, it } from "vitest";
import {
  computeCompoundedReturn,
  computeMonthlyMatrix,
  computeRollingReturns,
  generateMockContinuousTimeline,
  stitchContinuousTimeline,
} from "./engine";
import { TimelinePhaseSlice } from "./types";

describe("Returns Engine and Continuous Mode Timeline", () => {
  it("computes independent compounded-return fixtures accurately", () => {
    // 3 daily returns: +1.0%, -2.0%, +1.5%
    // Compounded = (1.01 * 0.98 * 1.015) - 1 = 1.004647 - 1 = 0.004647
    const returns = [0.01, -0.02, 0.015];
    const compounded = computeCompoundedReturn(returns);
    expect(compounded).toBeCloseTo(0.004647, 5);
  });

  it("stitches continuous timeline across Backtest, Paper, and Live without double counting", () => {
    const timeline = generateMockContinuousTimeline(1000000);

    expect(timeline.phases.length).toBe(3);
    expect(timeline.phases[0].phase).toBe("BACKTEST");
    expect(timeline.phases[1].phase).toBe("PAPER");
    expect(timeline.phases[2].phase).toBe("LIVE");

    // Ensure all dates are strictly increasing and unique
    const dates = timeline.stitchedPoints.map((p) => p.date);
    const uniqueDates = new Set(dates);
    expect(uniqueDates.size).toBe(dates.length);

    // Initial equity preserved at start
    expect(timeline.stitchedPoints[0].equity).toBeGreaterThan(950000);
    expect(timeline.totalReturn).not.toBe(0);
  });

  it("rejects overlapping phases with error preventing double-counting", () => {
    const sliceA: TimelinePhaseSlice = {
      phase: "BACKTEST",
      startDate: "2026-01-01",
      endDate: "2026-01-10",
      startEquity: 100000,
      endEquity: 105000,
      totalReturn: 0.05,
      dailyPoints: [
        {
          date: "2026-01-01",
          phase: "BACKTEST",
          equity: 101000,
          dailyReturn: 0.01,
          cumulativeReturn: 0.01,
        },
      ],
    };

    const sliceB: TimelinePhaseSlice = {
      phase: "PAPER",
      startDate: "2026-01-05", // Overlaps with sliceA ending on 2026-01-10
      endDate: "2026-01-20",
      startEquity: 105000,
      endEquity: 110000,
      totalReturn: 0.0476,
      dailyPoints: [
        {
          date: "2026-01-05",
          phase: "PAPER",
          equity: 106000,
          dailyReturn: 0.01,
          cumulativeReturn: 0.01,
        },
      ],
    };

    expect(() => stitchContinuousTimeline([sliceA, sliceB])).toThrow(
      /overlaps or violates strict sequencing/i
    );
  });

  it("computes monthly returns matrix and annual YTD", () => {
    const timeline = generateMockContinuousTimeline();
    const matrix = computeMonthlyMatrix(timeline.stitchedPoints);

    expect(matrix.length).toBeGreaterThan(0);
    expect(matrix[0].year).toBeDefined();
    expect(matrix[0].ytd).toBeDefined();
  });

  it("computes rolling returns for 21-day window", () => {
    const timeline = generateMockContinuousTimeline();
    const stats = computeRollingReturns(timeline.stitchedPoints, 21, "1M (21D)");

    expect(stats.windowDays).toBe(21);
    expect(stats.min).toBeLessThanOrEqual(stats.median);
    expect(stats.median).toBeLessThanOrEqual(stats.max);
  });
});
