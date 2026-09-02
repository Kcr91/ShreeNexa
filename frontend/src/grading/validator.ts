import {
  GradingValidationError,
  HorizonGradingConfig,
  ThresholdBand,
} from "./types";

export function validateThresholdBand(
  band: ThresholdBand
): GradingValidationError[] {
  const errors: GradingValidationError[] = [];

  if (band.direction === "HIGHER_IS_BETTER") {
    if (
      !(
        band.excellent > band.good &&
        band.good > band.acceptable &&
        band.acceptable > band.poor
      )
    ) {
      errors.push({
        metricName: band.metricName,
        message: `${band.label}: Invalid threshold order. For higher-is-better metrics, values must strictly satisfy Excellent (${band.excellent}) > Good (${band.good}) > Acceptable (${band.acceptable}) > Poor (${band.poor}).`,
      });
    }
  } else {
    // LOWER_IS_BETTER (e.g. Max Drawdown)
    if (
      !(
        band.excellent < band.good &&
        band.good < band.acceptable &&
        band.acceptable < band.poor
      )
    ) {
      errors.push({
        metricName: band.metricName,
        message: `${band.label}: Invalid threshold order. For lower-is-better metrics, values must strictly satisfy Excellent (${band.excellent}) < Good (${band.good}) < Acceptable (${band.acceptable}) < Poor (${band.poor}).`,
      });
    }
  }

  if (band.weight <= 0 || band.weight > 100) {
    errors.push({
      metricName: band.metricName,
      message: `${band.label}: Weight must be between 1% and 100%.`,
    });
  }

  return errors;
}

export function validateHorizonConfig(
  config: HorizonGradingConfig
): GradingValidationError[] {
  const allErrors: GradingValidationError[] = [];
  let totalWeight = 0;

  for (const band of Object.values(config.thresholds)) {
    totalWeight += band.weight;
    const bandErrors = validateThresholdBand(band);
    allErrors.push(...bandErrors);
  }

  if (Math.abs(totalWeight - 100) > 1.0) {
    allErrors.push({
      metricName: "TOTAL_WEIGHT",
      message: `Total metric weights must sum to 100% (currently ${totalWeight}%).`,
    });
  }

  return allErrors;
}
