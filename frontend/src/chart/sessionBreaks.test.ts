import { describe, expect, it } from "vitest";
import { detectSessionBreaks } from "./sessionBreaks";
import { BarData } from "./types";

describe("Indian Market Session Break Detection", () => {
  it("detects daily session break boundaries across intraday bars", () => {
    const bars: BarData[] = [
      { time: "2026-01-05 09:15:00", open: 100, high: 101, low: 99, close: 100 },
      { time: "2026-01-05 10:00:00", open: 100, high: 102, low: 100, close: 101 },
      { time: "2026-01-05 15:30:00", open: 101, high: 103, low: 101, close: 102 },
      { time: "2026-01-06 09:15:00", open: 103, high: 105, low: 102, close: 104 },
      { time: "2026-01-06 15:30:00", open: 104, high: 106, low: 104, close: 105 },
      { time: "2026-01-07 09:15:00", open: 106, high: 107, low: 105, close: 106 },
    ];

    const breaks = detectSessionBreaks(bars);

    expect(breaks).toHaveLength(3);
    expect(breaks[0].date).toBe("2026-01-05");
    expect(breaks[1].date).toBe("2026-01-06");
    expect(breaks[2].date).toBe("2026-01-07");
    expect(breaks[0].sessionName).toBe("REGULAR_MARKET_OPEN");
  });

  it("handles empty bars array gracefully", () => {
    expect(detectSessionBreaks([])).toEqual([]);
  });
});
