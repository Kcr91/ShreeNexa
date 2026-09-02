import {
  ContinuousTimeline,
  DailyReturnPoint,
  RollingReturnStats,
  TimelinePhaseSlice,
  YearlyMonthlyReturns,
} from "./types";

export function computeCompoundedReturn(returns: number[]): number {
  if (returns.length === 0) return 0;
  let factor = 1.0;
  for (const r of returns) {
    factor *= 1.0 + r;
  }
  return Number((factor - 1.0).toFixed(6));
}

export function stitchContinuousTimeline(
  slices: TimelinePhaseSlice[]
): ContinuousTimeline {
  if (slices.length === 0) {
    return {
      totalDays: 0,
      startDate: "",
      endDate: "",
      phases: [],
      stitchedPoints: [],
      totalReturn: 0,
    };
  }

  const stitchedPoints: DailyReturnPoint[] = [];
  const seenDates = new Set<string>();
  const initialEquity = slices[0].startEquity;
  let runningEquity = initialEquity;

  // Process slices in sequence and enforce strict non-overlapping dates
  for (let sIdx = 0; sIdx < slices.length; sIdx++) {
    const slice = slices[sIdx];

    if (sIdx > 0) {
      const prevSlice = slices[sIdx - 1];
      if (slice.startDate <= prevSlice.endDate) {
        throw new Error(
          `Phase ${slice.phase} (${slice.startDate}) overlaps or violates strict sequencing with previous phase ${prevSlice.phase} (${prevSlice.endDate}).`
        );
      }
    }

    for (const pt of slice.dailyPoints) {
      if (seenDates.has(pt.date)) {
        throw new Error(
          `Double counting detected: Date ${pt.date} appears in multiple phases.`
        );
      }
      seenDates.add(pt.date);

      runningEquity = Number((runningEquity * (1 + pt.dailyReturn)).toFixed(2));
      const cumulativeReturn = Number(
        (runningEquity / initialEquity - 1.0).toFixed(6)
      );

      stitchedPoints.push({
        date: pt.date,
        phase: slice.phase,
        equity: runningEquity,
        dailyReturn: pt.dailyReturn,
        cumulativeReturn,
      });
    }
  }

  const finalEquity = runningEquity;
  const totalReturn = Number(
    (finalEquity / initialEquity - 1.0).toFixed(6)
  );

  return {
    totalDays: stitchedPoints.length,
    startDate: stitchedPoints[0]?.date || "",
    endDate: stitchedPoints[stitchedPoints.length - 1]?.date || "",
    phases: slices,
    stitchedPoints,
    totalReturn,
  };
}

export function computeMonthlyMatrix(
  dailyPoints: DailyReturnPoint[]
): YearlyMonthlyReturns[] {
  // Group by year and month
  const byYearMonth: Record<number, Record<number, number[]>> = {};

  for (const pt of dailyPoints) {
    const parts = pt.date.split("-");
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10);

    if (!byYearMonth[year]) {
      byYearMonth[year] = {};
    }
    if (!byYearMonth[year][month]) {
      byYearMonth[year][month] = [];
    }
    byYearMonth[year][month].push(pt.dailyReturn);
  }

  const result: YearlyMonthlyReturns[] = [];
  const years = Object.keys(byYearMonth)
    .map(Number)
    .sort((a, b) => b - a); // Descending

  for (const yr of years) {
    const monthlyMap: Record<number, number> = {};
    const allReturnsInYear: number[] = [];

    for (let m = 1; m <= 12; m++) {
      const dailyRets = byYearMonth[yr][m];
      if (dailyRets && dailyRets.length > 0) {
        const compoundedMonth = computeCompoundedReturn(dailyRets);
        monthlyMap[m] = compoundedMonth;
        allReturnsInYear.push(...dailyRets);
      }
    }

    const ytd = computeCompoundedReturn(allReturnsInYear);
    result.push({
      year: yr,
      monthly: monthlyMap,
      ytd,
    });
  }

  return result;
}

export function computeRollingReturns(
  dailyPoints: DailyReturnPoint[],
  windowDays: number,
  windowLabel: string
): RollingReturnStats {
  if (dailyPoints.length < windowDays) {
    return {
      windowDays,
      windowLabel,
      min: 0,
      max: 0,
      median: 0,
      current: 0,
    };
  }

  const rollingValues: number[] = [];
  for (let i = windowDays - 1; i < dailyPoints.length; i++) {
    const windowSlice = dailyPoints
      .slice(i - windowDays + 1, i + 1)
      .map((p) => p.dailyReturn);
    rollingValues.push(computeCompoundedReturn(windowSlice));
  }

  rollingValues.sort((a, b) => a - b);
  const min = rollingValues[0];
  const max = rollingValues[rollingValues.length - 1];
  const mid = Math.floor(rollingValues.length / 2);
  const median =
    rollingValues.length % 2 !== 0
      ? rollingValues[mid]
      : (rollingValues[mid - 1] + rollingValues[mid]) / 2;
  const current = rollingValues[rollingValues.length - 1]; // or last window

  return {
    windowDays,
    windowLabel,
    min: Number(min.toFixed(4)),
    max: Number(max.toFixed(4)),
    median: Number(median.toFixed(4)),
    current: Number(current.toFixed(4)),
  };
}

export function generateMockContinuousTimeline(
  initialCapital = 1000000
): ContinuousTimeline {
  // Backtest: 2024-01-01 to 2025-12-31
  const backtestPoints: DailyReturnPoint[] = [];
  let eq = initialCapital;

  // Generate synthetic weekly steps
  let d = new Date(2025, 0, 1);
  for (let i = 0; i < 180; i++) {
    const dateStr = d.toISOString().split("T")[0];
    const ret = ((i * 17) % 25 - 9) / 1000; // -0.9% to +1.5%
    eq *= 1 + ret;
    backtestPoints.push({
      date: dateStr,
      phase: "BACKTEST",
      equity: Number(eq.toFixed(2)),
      dailyReturn: ret,
      cumulativeReturn: Number((eq / initialCapital - 1).toFixed(6)),
    });
    d.setDate(d.getDate() + 1);
  }

  const backtestSlice: TimelinePhaseSlice = {
    phase: "BACKTEST",
    startDate: backtestPoints[0].date,
    endDate: backtestPoints[backtestPoints.length - 1].date,
    startEquity: initialCapital,
    endEquity: eq,
    totalReturn: Number((eq / initialCapital - 1).toFixed(4)),
    dailyPoints: backtestPoints,
  };

  // Paper: contiguous next day to 60 days later
  const paperStartCapital = eq;
  const paperPoints: DailyReturnPoint[] = [];
  d.setDate(d.getDate() + 1);
  for (let i = 0; i < 45; i++) {
    const dateStr = d.toISOString().split("T")[0];
    const ret = ((i * 13) % 23 - 8) / 1000;
    eq *= 1 + ret;
    paperPoints.push({
      date: dateStr,
      phase: "PAPER",
      equity: Number(eq.toFixed(2)),
      dailyReturn: ret,
      cumulativeReturn: Number((eq / initialCapital - 1).toFixed(6)),
    });
    d.setDate(d.getDate() + 1);
  }

  const paperSlice: TimelinePhaseSlice = {
    phase: "PAPER",
    startDate: paperPoints[0].date,
    endDate: paperPoints[paperPoints.length - 1].date,
    startEquity: paperStartCapital,
    endEquity: eq,
    totalReturn: Number((eq / paperStartCapital - 1).toFixed(4)),
    dailyPoints: paperPoints,
  };

  // Live: contiguous next day to 30 days later
  const liveStartCapital = eq;
  const livePoints: DailyReturnPoint[] = [];
  d.setDate(d.getDate() + 1);
  for (let i = 0; i < 30; i++) {
    const dateStr = d.toISOString().split("T")[0];
    const ret = ((i * 19) % 27 - 10) / 1000;
    eq *= 1 + ret;
    livePoints.push({
      date: dateStr,
      phase: "LIVE",
      equity: Number(eq.toFixed(2)),
      dailyReturn: ret,
      cumulativeReturn: Number((eq / initialCapital - 1).toFixed(6)),
    });
    d.setDate(d.getDate() + 1);
  }

  const liveSlice: TimelinePhaseSlice = {
    phase: "LIVE",
    startDate: livePoints[0].date,
    endDate: livePoints[livePoints.length - 1].date,
    startEquity: liveStartCapital,
    endEquity: eq,
    totalReturn: Number((eq / liveStartCapital - 1).toFixed(4)),
    dailyPoints: livePoints,
  };

  return stitchContinuousTimeline([backtestSlice, paperSlice, liveSlice]);
}
