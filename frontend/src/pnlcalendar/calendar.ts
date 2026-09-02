import { DailyPnlRecord, MonthlyPnlSummary } from "./types";

export const INDIAN_HOLIDAYS_2026: Record<string, string> = {
  "2026-01-26": "Republic Day",
  "2026-03-04": "Holi",
  "2026-04-14": "Dr. Ambedkar Jayanti",
  "2026-05-01": "Maharashtra Day",
  "2026-08-15": "Independence Day",
  "2026-10-02": "Mahatma Gandhi Jayanti",
  "2026-10-20": "Dussehra",
  "2026-11-08": "Diwali Laxmi Pujan",
  "2026-12-25": "Christmas",
};

export function generateMonthlyPnlSummary(
  year: number,
  month: number // 1-12
): MonthlyPnlSummary {
  const monthStr = month < 10 ? `0${month}` : `${month}`;
  const monthKey = `${year}-${monthStr}`;
  const daysInMonth = new Date(year, month, 0).getDate();

  const dailyRecords: Record<string, DailyPnlRecord> = {};
  let tradingDays = 0;
  let greenDays = 0;
  let redDays = 0;
  let grossPnl = 0;
  let totalCharges = 0;

  for (let day = 1; day <= daysInMonth; day++) {
    const dayStr = day < 10 ? `0${day}` : `${day}`;
    const dateStr = `${year}-${monthStr}-${dayStr}`;
    const dateObj = new Date(year, month - 1, day);
    const dayOfWeek = dateObj.getDay(); // 0 = Sun, 6 = Sat

    if (dayOfWeek === 0 || dayOfWeek === 6) {
      dailyRecords[dateStr] = {
        date: dateStr,
        dayType: "WEEKEND",
        grossPnl: 0,
        charges: 0,
        netPnl: 0,
        tradesCount: 0,
        trades: [],
      };
      continue;
    }

    if (INDIAN_HOLIDAYS_2026[dateStr]) {
      dailyRecords[dateStr] = {
        date: dateStr,
        dayType: "HOLIDAY",
        holidayName: INDIAN_HOLIDAYS_2026[dateStr],
        grossPnl: 0,
        charges: 0,
        netPnl: 0,
        tradesCount: 0,
        trades: [],
      };
      continue;
    }

    // Trading Day Mock Data Generator (Deterministic based on day seed)
    tradingDays += 1;
    const isWin = (day * 7 + month * 13) % 10 >= 3; // ~70% win rate
    const multiplier = isWin ? 1 : -1;
    const dayGross = multiplier * ((day * 1450 + 2800) % 12500);
    const dayCharges = 240 + ((day * 35) % 180);
    const dayNet = Number((dayGross - dayCharges).toFixed(2));

    if (dayNet >= 0) {
      greenDays += 1;
    } else {
      redDays += 1;
    }

    grossPnl += dayGross;
    totalCharges += dayCharges;

    dailyRecords[dateStr] = {
      date: dateStr,
      dayType: "TRADING_DAY",
      grossPnl: dayGross,
      charges: dayCharges,
      netPnl: dayNet,
      tradesCount: 3,
      trades: [
        {
          time: "09:30:14",
          symbol: "NIFTY 24500 CE",
          side: "BUY",
          quantity: 50,
          price: 142.5,
          pnl: Math.round(dayGross * 0.6),
        },
        {
          time: "11:15:42",
          symbol: "RELIANCE",
          side: "BUY",
          quantity: 25,
          price: 2940.0,
          pnl: Math.round(dayGross * 0.4),
        },
      ],
    };
  }

  const netPnl = Number((grossPnl - totalCharges).toFixed(2));
  const winRatePct =
    tradingDays > 0 ? Number(((greenDays / tradingDays) * 100).toFixed(1)) : 0;

  return {
    monthKey,
    tradingDays,
    greenDays,
    redDays,
    winRatePct,
    grossPnl: Number(grossPnl.toFixed(2)),
    totalCharges: Number(totalCharges.toFixed(2)),
    netPnl,
    dailyRecords,
  };
}
