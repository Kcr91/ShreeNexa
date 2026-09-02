import { describe, expect, it } from "vitest";
import { validateHorizonConfig, validateThresholdBand } from "./validator";
import { HorizonGradingConfig, ThresholdBand } from "./types";

describe("Grading Threshold Validator", () => {
  it("passes valid monotonic higher-is-better thresholds", () => {
    const band: ThresholdBand = {
      metricName: "sharpe",
      label: "Sharpe Ratio",
      direction: "HIGHER_IS_BETTER",
      weight: 30,
      excellent: 2.0,
      good: 1.5,
      acceptable: 1.0,
      poor: 0.5,
    };
    const errors = validateThresholdBand(band);
    expect(errors.length).toBe(0);
  });

  it("rejects non-monotonic higher-is-better thresholds", () => {
    const band: ThresholdBand = {
      metricName: "sharpe",
      label: "Sharpe Ratio",
      direction: "HIGHER_IS_BETTER",
      weight: 30,
      excellent: 1.2, // INVALID: excellent is lower than good (1.5)
      good: 1.5,
      acceptable: 1.0,
      poor: 0.5,
    };
    const errors = validateThresholdBand(band);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0].message).toMatch(/Invalid threshold order/i);
  });

  it("passes valid lower-is-better thresholds and rejects inverted ones", () => {
    const validBand: ThresholdBand = {
      metricName: "max_drawdown",
      label: "Max Drawdown (%)",
      direction: "LOWER_IS_BETTER",
      weight: 30,
      excellent: 8.0,
      good: 12.0,
      acceptable: 18.0,
      poor: 25.0,
    };
    expect(validateThresholdBand(validBand).length).toBe(0);

    const invertedBand: ThresholdBand = {
      ...validBand,
      excellent: 20.0, // INVALID: excellent is higher than good (12.0)
    };
    const errors = validateThresholdBand(invertedBand);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0].message).toMatch(/Invalid threshold order/i);
  });

  it("validates horizon configuration total weight sum", () => {
    const config: HorizonGradingConfig = {
      horizon: "POSITIONAL",
      thresholds: {
        sharpe: {
          metricName: "sharpe",
          label: "Sharpe Ratio",
          direction: "HIGHER_IS_BETTER",
          weight: 40,
          excellent: 2.0,
          good: 1.5,
          acceptable: 1.0,
          poor: 0.5,
        },
        max_drawdown: {
          metricName: "max_drawdown",
          label: "Max Drawdown (%)",
          direction: "LOWER_IS_BETTER",
          weight: 40, // Sum = 80%, not 100%
          excellent: 8.0,
          good: 12.0,
          acceptable: 18.0,
          poor: 25.0,
        },
      },
    };

    const errors = validateHorizonConfig(config);
    expect(errors.some((e) => e.metricName === "TOTAL_WEIGHT")).toBe(true);
  });
});
