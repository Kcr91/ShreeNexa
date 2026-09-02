import { describe, expect, it } from "vitest";
import {
  DEFAULT_GRADING_CONFIG,
  evaluateScorecard,
  markScorecardsStale,
  regradeScorecards,
  SAMPLE_STRATEGIES,
} from "./engine";
import { GradingConfig } from "./types";

describe("Grading Engine and Scorecard Lifecycle", () => {
  it("evaluates a strategy scorecard and generates deployment verdict", () => {
    const strat = SAMPLE_STRATEGIES[0];
    const scorecard = evaluateScorecard(
      strat.id,
      strat.name,
      strat.horizon,
      strat.metricValues,
      DEFAULT_GRADING_CONFIG
    );

    expect(scorecard.strategyName).toBe("NIFTY Golden Cross Momentum");
    expect(scorecard.overallScore).toBeGreaterThan(80);
    expect(scorecard.overallGrade).toBe("EXCELLENT");
    expect(scorecard.verdict).toBe("DEPLOYABLE");
    expect(scorecard.status).toBe("CURRENT");
    expect(scorecard.configVersion).toBe("v1.0");
  });

  it("marks old scorecards as STALE when active config version advances", () => {
    const strat = SAMPLE_STRATEGIES[0];
    const initialScorecard = evaluateScorecard(
      strat.id,
      strat.name,
      strat.horizon,
      strat.metricValues,
      DEFAULT_GRADING_CONFIG
    );

    expect(initialScorecard.status).toBe("CURRENT");

    // Advance config version to v1.1
    const staleScorecards = markScorecardsStale([initialScorecard], "v1.1");
    expect(staleScorecards[0].status).toBe("STALE");
  });

  it("explicitly re-grades scorecards against updated threshold configurations", () => {
    const strat = SAMPLE_STRATEGIES[0];
    const oldScorecard = evaluateScorecard(
      strat.id,
      strat.name,
      strat.horizon,
      strat.metricValues,
      DEFAULT_GRADING_CONFIG
    );

    // Create a stricter v2.0 config requiring higher Sharpe
    const stricterConfig: GradingConfig = {
      ...DEFAULT_GRADING_CONFIG,
      version: "v2.0",
      horizons: {
        ...DEFAULT_GRADING_CONFIG.horizons,
        POSITIONAL: {
          ...DEFAULT_GRADING_CONFIG.horizons.POSITIONAL,
          thresholds: {
            ...DEFAULT_GRADING_CONFIG.horizons.POSITIONAL.thresholds,
            sharpe: {
              ...DEFAULT_GRADING_CONFIG.horizons.POSITIONAL.thresholds.sharpe,
              excellent: 3.5, // Much higher bar
              good: 2.8,
              acceptable: 2.0,
              poor: 1.0,
            },
          },
        },
      },
    };

    const regraded = regradeScorecards([oldScorecard], stricterConfig);
    expect(regraded[0].configVersion).toBe("v2.0");
    expect(regraded[0].status).toBe("CURRENT");
    expect(regraded[0].overallScore).toBeLessThan(oldScorecard.overallScore);
  });
});
