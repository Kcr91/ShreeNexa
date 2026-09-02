export type HorizonProfile =
  | "INTRADAY"
  | "SWING"
  | "POSITIONAL"
  | "INVESTMENT";

export type MetricGrade =
  | "EXCELLENT"
  | "GOOD"
  | "ACCEPTABLE"
  | "POOR"
  | "REJECTED";

export type Verdict = "DEPLOYABLE" | "INVESTIGATE" | "REJECT";

export type ScorecardStatus = "CURRENT" | "STALE";

export type MetricDirection = "HIGHER_IS_BETTER" | "LOWER_IS_BETTER";

export interface ThresholdBand {
  metricName: string;
  label: string;
  direction: MetricDirection;
  weight: number; // Percentage weight e.g. 25
  excellent: number;
  good: number;
  acceptable: number;
  poor: number;
}

export interface HorizonGradingConfig {
  horizon: HorizonProfile;
  thresholds: Record<string, ThresholdBand>;
}

export interface GradingConfig {
  version: string; // e.g. "v1.0"
  updatedAt: string;
  horizons: Record<HorizonProfile, HorizonGradingConfig>;
}

export interface ScorecardSummary {
  strategyId: string;
  strategyName: string;
  horizon: HorizonProfile;
  configVersion: string;
  status: ScorecardStatus;
  overallScore: number;
  overallGrade: MetricGrade;
  verdict: Verdict;
  metricValues: Record<string, number>;
}

export interface GradingValidationError {
  metricName: string;
  message: string;
}

export interface GradingThresholdsWidgetSettings {
  defaultHorizon: HorizonProfile;
}
