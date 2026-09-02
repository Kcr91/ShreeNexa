import { BarData, SessionBreak } from "./types";

export function detectSessionBreaks(bars: BarData[]): SessionBreak[] {
  if (bars.length === 0) return [];
  const breaks: SessionBreak[] = [];

  let lastDate = "";

  for (let i = 0; i < bars.length; i++) {
    const bar = bars[i];
    const timeStr = String(bar.time);

    // Extract Date part (supports YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or UNIX timestamps)
    let barDate = "";
    if (timeStr.includes("T") || timeStr.includes(" ")) {
      barDate = timeStr.split(/[T ]/)[0];
    } else if (/^\d{4}-\d{2}-\d{2}/.test(timeStr)) {
      barDate = timeStr.substring(0, 10);
    } else if (!isNaN(Number(timeStr))) {
      // Unix timestamp (seconds or ms)
      const num = Number(timeStr);
      const dateObj = new Date(num > 1e11 ? num : num * 1000);
      barDate = dateObj.toISOString().split("T")[0];
    }

    if (barDate && barDate !== lastDate) {
      breaks.push({
        time: bar.time,
        sessionName: "REGULAR_MARKET_OPEN",
        date: barDate,
      });
      lastDate = barDate;
    }
  }

  return breaks;
}
