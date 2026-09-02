import { BacktestReport, MonthlyReturnCell, EquityCurvePoint, TradePnlDistribution } from "./types";

export function calculateDrawdownCurve(equityValues: number[]): {
  drawdowns: number[];
  maxDrawdown: number;
} {
  let peak = -Infinity;
  const drawdowns: number[] = [];
  let maxDrawdown = 0;

  for (const val of equityValues) {
    if (val > peak) {
      peak = val;
    }
    const dd = peak > 0 ? Number((((val - peak) / peak) * 100).toFixed(2)) : 0;
    drawdowns.push(dd);
    if (dd < maxDrawdown) {
      maxDrawdown = dd;
    }
  }

  return {
    drawdowns,
    maxDrawdown: Math.abs(maxDrawdown),
  };
}

export function groupMonthlyReturns(cells: MonthlyReturnCell[]): {
  years: number[];
  matrix: Record<number, Record<number, number>>;
  yearlyTotals: Record<number, number>;
} {
  const matrix: Record<number, Record<number, number>> = {};
  const yearsSet = new Set<number>();

  for (const cell of cells) {
    yearsSet.add(cell.year);
    if (!matrix[cell.year]) {
      matrix[cell.year] = {};
    }
    matrix[cell.year][cell.month] = cell.returnPct;
  }

  const years = Array.from(yearsSet).sort((a, b) => b - a); // Newest year first
  const yearlyTotals: Record<number, number> = {};

  for (const y of years) {
    let compound = 1.0;
    for (let m = 1; m <= 12; m++) {
      const r = matrix[y]?.[m] ?? 0;
      compound *= 1.0 + r / 100;
    }
    yearlyTotals[y] = Number(((compound - 1.0) * 100).toFixed(2));
  }

  return {
    years,
    matrix,
    yearlyTotals,
  };
}

export function getHeatmapCellColor(returnPct: number | undefined): string {
  if (returnPct === undefined || returnPct === 0) return "rgba(255, 255, 255, 0.04)";
  if (returnPct >= 6.0) return "rgba(0, 192, 118, 0.85)";
  if (returnPct >= 3.0) return "rgba(0, 192, 118, 0.55)";
  if (returnPct > 0) return "rgba(0, 192, 118, 0.25)";
  if (returnPct <= -6.0) return "rgba(255, 77, 79, 0.85)";
  if (returnPct <= -3.0) return "rgba(255, 77, 79, 0.55)";
  return "rgba(255, 77, 79, 0.25)";
}

export function generateMockBacktestReport(
  strategyName: string = "NIFTY Intraday Momentum"
): BacktestReport {
  const startDate = "2025-01-01";
  const endDate = "2025-12-31";
  const initialCapital = 1000000;

  // Generate 12 months of daily equity points
  const equityCurve: EquityCurvePoint[] = [];
  let stratCap = initialCapital;
  let benchCap = initialCapital;
  let peak = stratCap;

  for (let d = 1; d <= 250; d++) {
    const stratDailyRet = (Math.random() - 0.44) * 0.016; // positive drift
    const benchDailyRet = (Math.random() - 0.48) * 0.012;

    stratCap = Number((stratCap * (1 + stratDailyRet)).toFixed(2));
    benchCap = Number((benchCap * (1 + benchDailyRet)).toFixed(2));
    peak = Math.max(peak, stratCap);
    const dd = Number((((stratCap - peak) / peak) * 100).toFixed(2));

    equityCurve.push({
      time: `2025-D${d}`,
      strategyEquity: stratCap,
      benchmarkEquity: benchCap,
      drawdownPct: dd,
    });
  }

  const finalCapital = stratCap;
  const netProfit = Number((finalCapital - initialCapital).toFixed(2));

  // Monthly Return Cells for 2024 and 2025
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const monthlyReturns: MonthlyReturnCell[] = [];

  const returns2024 = [3.2, 2.1, -1.4, 4.5, 1.8, 5.2, -2.1, 3.8, 4.1, 1.2, -0.8, 3.5];
  const returns2025 = [2.8, 4.1, 1.9, -1.2, 3.4, 2.7, 5.1, -0.9, 3.3, 4.0, 2.1, 1.5];

  for (let m = 1; m <= 12; m++) {
    monthlyReturns.push({
      year: 2024,
      month: m,
      monthName: monthNames[m - 1],
      returnPct: returns2024[m - 1],
    });
    monthlyReturns.push({
      year: 2025,
      month: m,
      monthName: monthNames[m - 1],
      returnPct: returns2025[m - 1],
    });
  }

  // Trade PnL Distribution
  const tradeDistribution: TradePnlDistribution[] = [
    { bin: "<-5k", count: 8, isProfit: false },
    { bin: "-5k to -2k", count: 18, isProfit: false },
    { bin: "-2k to 0", count: 32, isProfit: false },
    { bin: "0 to 2k", count: 45, isProfit: true },
    { bin: "2k to 5k", count: 62, isProfit: true },
    { bin: ">5k", count: 25, isProfit: true },
  ];

  return {
    backtestId: "BT-2026-NIFTY-MOM-01",
    strategyName,
    universe: "NIFTY 50",
    startDate,
    endDate,
    initialCapital,
    finalCapital,
    netProfit,
    scorecard: {
      sharpeRatio: 2.14,
      sortinoRatio: 3.25,
      cagr: 32.4,
      maxDrawdownPct: 6.8,
      maxDrawdownDurationDays: 14,
      winRatePct: 68.5,
      profitFactor: 2.18,
      totalTrades: 190,
      calmarRatio: 4.76,
      expectancy: 1850.0,
      overallGrade: "A",
    },
    equityCurve,
    monthlyReturns,
    tradeDistribution,
  };
}
