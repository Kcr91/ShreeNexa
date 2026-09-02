import { describe, expect, it } from "vitest";
import { calculateDrawdownCurve, groupMonthlyReturns, getHeatmapCellColor, generateMockBacktestReport } from "./metrics";
import { MonthlyReturnCell } from "./types";

describe("Backtest Analytics Metrics and Transformations", () => {
  it("calculates peak-to-trough drawdown curve correctly", () => {
    const equityValues = [100, 110, 120, 108, 96, 114, 130, 125];
    const { drawdowns, maxDrawdown } = calculateDrawdownCurve(equityValues);

    expect(drawdowns[0]).toBe(0);
    expect(drawdowns[2]).toBe(0); // New peak @ 120
    expect(drawdowns[3]).toBe(-10); // (108 - 120) / 120 = -10%
    expect(drawdowns[4]).toBe(-20); // (96 - 120) / 120 = -20%
    expect(maxDrawdown).toBe(20);
  });

  it("aggregates monthly return cells into yearly matrix and computes compound totals", () => {
    const cells: MonthlyReturnCell[] = [
      { year: 2025, month: 1, monthName: "Jan", returnPct: 2.0 },
      { year: 2025, month: 2, monthName: "Feb", returnPct: 3.0 },
      { year: 2024, month: 1, monthName: "Jan", returnPct: 5.0 },
    ];

    const grouped = groupMonthlyReturns(cells);
    expect(grouped.years).toEqual([2025, 2024]);
    expect(grouped.matrix[2025][1]).toBe(2.0);
    expect(grouped.matrix[2025][2]).toBe(3.0);
    expect(grouped.yearlyTotals[2025]).toBeCloseTo(5.06, 1);
  });

  it("maps return percentages to appropriate heatmap color intensities", () => {
    expect(getHeatmapCellColor(8.0)).toContain("0, 192, 118");
    expect(getHeatmapCellColor(-8.0)).toContain("255, 77, 79");
    expect(getHeatmapCellColor(0)).toContain("rgba(255, 255, 255");
  });

  it("generates a complete mock backtest report with grade A scorecard", () => {
    const report = generateMockBacktestReport("NIFTY Momentum");
    expect(report.strategyName).toBe("NIFTY Momentum");
    expect(report.scorecard.overallGrade).toBe("A");
    expect(report.scorecard.sharpeRatio).toBeGreaterThan(1.5);
    expect(report.monthlyReturns).toHaveLength(24);
  });
});
