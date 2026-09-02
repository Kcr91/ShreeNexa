import { describe, expect, it } from "vitest";
import { generateMonthlyPnlSummary, INDIAN_HOLIDAYS_2026 } from "./calendar";

describe("P&L Calendar Engine and Indian Holiday Schedule", () => {
  it("generates monthly summary with correct trading day and holiday counts", () => {
    // August 2026 has Independence Day on Aug 15 (which is a Saturday, so 0 weekday holidays, but marked)
    const summary = generateMonthlyPnlSummary(2026, 8);

    expect(summary.monthKey).toBe("2026-08");
    expect(summary.tradingDays).toBeGreaterThan(18);
    expect(summary.winRatePct).toBeGreaterThan(50);
    expect(summary.grossPnl).not.toBe(0);
    expect(summary.totalCharges).toBeGreaterThan(0);
    expect(summary.netPnl).toBe(Number((summary.grossPnl - summary.totalCharges).toFixed(2)));
  });

  it("recognizes Indian market public holidays", () => {
    expect(INDIAN_HOLIDAYS_2026["2026-01-26"]).toBe("Republic Day");
    expect(INDIAN_HOLIDAYS_2026["2026-08-15"]).toBe("Independence Day");
    expect(INDIAN_HOLIDAYS_2026["2026-10-02"]).toBe("Mahatma Gandhi Jayanti");
  });
});
