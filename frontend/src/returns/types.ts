export type ExecutionPhase = "BACKTEST" | "PAPER" | "LIVE";

export interface DailyReturnPoint {
  date: string; // YYYY-MM-DD
  phase: ExecutionPhase;
  equity: number;
  dailyReturn: number; // decimal, e.g. 0.015 for +1.5%
  cumulativeReturn: number; // decimal, compounded from timeline start
}

export interface TimelinePhaseSlice {
  phase: ExecutionPhase;
  startDate: string;
  endDate: string;
  startEquity: number;
  endEquity: number;
  totalReturn: number;
  dailyPoints: DailyReturnPoint[];
}

export interface ContinuousTimeline {
  totalDays: number;
  startDate: string;
  endDate: string;
  phases: TimelinePhaseSlice[];
  stitchedPoints: DailyReturnPoint[];
  totalReturn: number;
}

export interface RollingReturnStats {
  windowDays: number;
  windowLabel: string;
  min: number;
  max: number;
  median: number;
  current: number;
}

export interface YearlyMonthlyReturns {
  year: number;
  monthly: Record<number, number>; // 1-12 month index to return decimal
  ytd: number; // decimal compounded return
}

export interface ReturnsTimelineWidgetSettings {
  activePhaseFilter: "ALL" | "BACKTEST" | "PAPER" | "LIVE";
  initialCapital: number;
}
