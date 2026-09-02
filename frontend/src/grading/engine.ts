import {
  GradingConfig,
  HorizonGradingConfig,
  HorizonProfile,
  MetricGrade,
  ScorecardSummary,
  ThresholdBand,
  Verdict,
} from "./types";

export const DEFAULT_POSITIONAL_THRESHOLDS: Record<string, ThresholdBand> = {
  sharpe: {
    metricName: "sharpe",
    label: "Sharpe Ratio",
    direction: "HIGHER_IS_BETTER",
    weight: 30,
    excellent: 2.0,
    good: 1.5,
    acceptable: 1.0,
    poor: 0.5,
  },
  max_drawdown: {
    metricName: "max_drawdown",
    label: "Max Drawdown (%)",
    direction: "LOWER_IS_BETTER",
    weight: 30,
    excellent: 10.0,
    good: 15.0,
    acceptable: 20.0,
    poor: 30.0,
  },
  profit_factor: {
    metricName: "profit_factor",
    label: "Profit Factor",
    direction: "HIGHER_IS_BETTER",
    weight: 20,
    excellent: 2.0,
    good: 1.6,
    acceptable: 1.3,
    poor: 1.0,
  },
  win_rate: {
    metricName: "win_rate",
    label: "Win Rate (%)",
    direction: "HIGHER_IS_BETTER",
    weight: 20,
    excellent: 65.0,
    good: 55.0,
    acceptable: 45.0,
    poor: 35.0,
  },
};

export const DEFAULT_GRADING_CONFIG: GradingConfig = {
  version: "v1.0",
  updatedAt: "2026-09-02T10:00:00Z",
  horizons: {
    INTRADAY: {
      horizon: "INTRADAY",
      thresholds: {
        ...DEFAULT_POSITIONAL_THRESHOLDS,
        sharpe: {
          ...DEFAULT_POSITIONAL_THRESHOLDS.sharpe,
          excellent: 2.5,
          good: 1.8,
          acceptable: 1.2,
          poor: 0.8,
        },
        max_drawdown: {
          ...DEFAULT_POSITIONAL_THRESHOLDS.max_drawdown,
          excellent: 5.0,
          good: 8.0,
          acceptable: 12.0,
          poor: 18.0,
        },
      },
    },
    SWING: {
      horizon: "SWING",
      thresholds: {
        ...DEFAULT_POSITIONAL_THRESHOLDS,
      },
    },
    POSITIONAL: {
      horizon: "POSITIONAL",
      thresholds: {
        ...DEFAULT_POSITIONAL_THRESHOLDS,
      },
    },
    INVESTMENT: {
      horizon: "INVESTMENT",
      thresholds: {
        ...DEFAULT_POSITIONAL_THRESHOLDS,
        max_drawdown: {
          ...DEFAULT_POSITIONAL_THRESHOLDS.max_drawdown,
          excellent: 15.0,
          good: 22.0,
          acceptable: 30.0,
          poor: 40.0,
        },
      },
    },
  },
};

export function gradeMetricValue(
  val: number,
  band: ThresholdBand
): { grade: MetricGrade; score: number } {
  if (band.direction === "HIGHER_IS_BETTER") {
    if (val >= band.excellent) {
      const score = Math.min(100, 90 + (10 * (val - band.excellent)) / Math.max(0.01, band.excellent));
      return { grade: "EXCELLENT", score: Number(score.toFixed(1)) };
    } else if (val >= band.good) {
      const frac = (val - band.good) / Math.max(0.01, band.excellent - band.good);
      return { grade: "GOOD", score: Number((75 + 15 * frac).toFixed(1)) };
    } else if (val >= band.acceptable) {
      const frac = (val - band.acceptable) / Math.max(0.01, band.good - band.acceptable);
      return { grade: "ACCEPTABLE", score: Number((60 + 15 * frac).toFixed(1)) };
    } else if (val >= band.poor) {
      const frac = (val - band.poor) / Math.max(0.01, band.acceptable - band.poor);
      return { grade: "POOR", score: Number((40 + 20 * frac).toFixed(1)) };
    } else {
      return { grade: "REJECTED", score: Number(Math.max(0, (40 * val) / Math.max(0.01, band.poor)).toFixed(1)) };
    }
  } else {
    // LOWER_IS_BETTER (e.g. Max Drawdown %)
    if (val <= band.excellent) {
      return { grade: "EXCELLENT", score: 100 };
    } else if (val <= band.good) {
      const frac = (band.good - val) / Math.max(0.01, band.good - band.excellent);
      return { grade: "GOOD", score: Number((75 + 15 * frac).toFixed(1)) };
    } else if (val <= band.acceptable) {
      const frac = (band.acceptable - val) / Math.max(0.01, band.acceptable - band.good);
      return { grade: "ACCEPTABLE", score: Number((60 + 15 * frac).toFixed(1)) };
    } else if (val <= band.poor) {
      const frac = (band.poor - val) / Math.max(0.01, band.poor - band.acceptable);
      return { grade: "POOR", score: Number((40 + 20 * frac).toFixed(1)) };
    } else {
      const excess = val - band.poor;
      return { grade: "REJECTED", score: Number(Math.max(0, 40 - 20 * (excess / Math.max(0.01, band.poor))).toFixed(1)) };
    }
  }
}

export function evaluateScorecard(
  strategyId: string,
  strategyName: string,
  horizon: HorizonProfile,
  metricValues: Record<string, number>,
  config: GradingConfig,
  customThresholds?: HorizonGradingConfig
): ScorecardSummary {
  const horizonConfig = customThresholds || config.horizons[horizon];
  let totalWeightedScore = 0;
  let hasReject = false;

  for (const [key, band] of Object.entries(horizonConfig.thresholds)) {
    const val = metricValues[key] ?? 0;
    const { grade, score } = gradeMetricValue(val, band);
    totalWeightedScore += (score * band.weight) / 100;
    if (grade === "REJECTED") {
      hasReject = true;
    }
  }

  const overallScore = Number(totalWeightedScore.toFixed(1));
  let overallGrade: MetricGrade;
  let verdict: Verdict;

  if (overallScore >= 85 && !hasReject) {
    overallGrade = "EXCELLENT";
    verdict = "DEPLOYABLE";
  } else if (overallScore >= 70 && !hasReject) {
    overallGrade = "GOOD";
    verdict = "DEPLOYABLE";
  } else if (overallScore >= 55) {
    overallGrade = "ACCEPTABLE";
    verdict = "INVESTIGATE";
  } else if (overallScore >= 40) {
    overallGrade = "POOR";
    verdict = "REJECT";
  } else {
    overallGrade = "REJECTED";
    verdict = "REJECT";
  }

  return {
    strategyId,
    strategyName,
    horizon,
    configVersion: config.version,
    status: "CURRENT",
    overallScore,
    overallGrade,
    verdict,
    metricValues,
  };
}

export function markScorecardsStale(
  scorecards: ScorecardSummary[],
  activeConfigVersion: string
): ScorecardSummary[] {
  return scorecards.map((sc) => {
    if (sc.configVersion !== activeConfigVersion) {
      return { ...sc, status: "STALE" };
    }
    return sc;
  });
}

export function regradeScorecards(
  scorecards: ScorecardSummary[],
  newConfig: GradingConfig
): ScorecardSummary[] {
  return scorecards.map((sc) => {
    const regraded = evaluateScorecard(
      sc.strategyId,
      sc.strategyName,
      sc.horizon,
      sc.metricValues,
      newConfig
    );
    return regraded;
  });
}

export const SAMPLE_STRATEGIES = [
  {
    id: "strat-1",
    name: "NIFTY Golden Cross Momentum",
    horizon: "POSITIONAL" as HorizonProfile,
    metricValues: {
      sharpe: 2.1,
      max_drawdown: 8.5,
      profit_factor: 2.2,
      win_rate: 62.0,
    },
  },
  {
    id: "strat-2",
    name: "BankNifty Breakout Scalper",
    horizon: "INTRADAY" as HorizonProfile,
    metricValues: {
      sharpe: 1.4,
      max_drawdown: 14.2,
      profit_factor: 1.5,
      win_rate: 48.0,
    },
  },
  {
    id: "strat-3",
    name: "FinNifty Weekly Iron Condor",
    horizon: "SWING" as HorizonProfile,
    metricValues: {
      sharpe: 1.7,
      max_drawdown: 11.0,
      profit_factor: 1.8,
      win_rate: 68.0,
    },
  },
];
