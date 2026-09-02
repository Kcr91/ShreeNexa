export type DayType = "TRADING_DAY" | "HOLIDAY" | "WEEKEND";

export interface CalendarTrade {
  time: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  pnl: number;
}

export interface DailyPnlRecord {
  date: string; // YYYY-MM-DD
  dayType: DayType;
  holidayName?: string;
  grossPnl: number;
  charges: number;
  netPnl: number;
  tradesCount: number;
  trades: CalendarTrade[];
}

export interface MonthlyPnlSummary {
  monthKey: string; // YYYY-MM
  tradingDays: number;
  greenDays: number;
  redDays: number;
  winRatePct: number;
  grossPnl: number;
  totalCharges: number;
  netPnl: number;
  dailyRecords: Record<string, DailyPnlRecord>;
}

export interface PnlCalendarWidgetSettings {
  defaultMonth: string;
  showCharges: boolean;
  showWeekends: boolean;
}
