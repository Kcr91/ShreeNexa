export type StrategyGrade = "A" | "B" | "C" | "D" | "F";

export interface PerformanceScorecard {
  sharpeRatio: number;
  sortinoRatio: number;
  cagr: number;
  maxDrawdownPct: number;
  maxDrawdownDurationDays: number;
  winRatePct: number;
  profitFactor: number;
  totalTrades: number;
  calmarRatio: number;
  expectancy: number;
  overallGrade: StrategyGrade;
}

export interface EquityCurvePoint {
  time: string | number;
  strategyEquity: number;
  benchmarkEquity: number;
  drawdownPct: number;
}

export interface MonthlyReturnCell {
  year: number;
  month: number;
  monthName: string;
  returnPct: number;
}

export interface TradePnlDistribution {
  bin: string;
  count: number;
  isProfit: boolean;
}

export interface BacktestReport {
  backtestId: string;
  strategyName: string;
  universe: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  finalCapital: number;
  netProfit: number;
  scorecard: PerformanceScorecard;
  equityCurve: EquityCurvePoint[];
  monthlyReturns: MonthlyReturnCell[];
  tradeDistribution: TradePnlDistribution[];
}

export interface AnalyticsWidgetSettings {
  defaultMetricView: "SCORECARD" | "EQUITY_CURVE" | "UNDERWATER" | "MONTHLY_HEATMAP" | "TRADE_DISTRIBUTION";
  showBenchmark: boolean;
}
