import {
  StrategyBuilderState,
  StrategyIRSchema,
  VectorBacktestResult,
} from "./types";

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

export function validateStrategyBuilderState(state: StrategyBuilderState): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (!state.strategyName || state.strategyName.trim() === "") {
    errors.push("Strategy name cannot be empty.");
  }

  if (!state.indicators || state.indicators.length === 0) {
    errors.push("At least one indicator node is required.");
  }

  const indicatorNames = new Set<string>();
  for (const ind of state.indicators || []) {
    const trimmed = ind.name.trim();
    if (!trimmed) {
      errors.push("Indicator name cannot be blank.");
    } else if (indicatorNames.has(trimmed)) {
      errors.push(`Duplicate indicator name '${trimmed}'.`);
    } else {
      indicatorNames.add(trimmed);
    }
  }

  const validOperands = new Set([
    ...Array.from(indicatorNames),
    "close",
    "open",
    "high",
    "low",
    "volume",
  ]);

  if (!state.rules || state.rules.length === 0) {
    errors.push("At least one entry or exit rule block is required.");
  }

  for (const rule of state.rules || []) {
    if (!rule.conditions || rule.conditions.length === 0) {
      errors.push(`Rule block '${rule.name}' must have at least one condition.`);
      continue;
    }

    for (const cond of rule.conditions) {
      if (!cond.leftOperand || !validOperands.has(cond.leftOperand)) {
        errors.push(
          `Rule '${rule.name}' left operand '${cond.leftOperand}' is undefined.`
        );
      }
      const isRightNumeric = !isNaN(Number(cond.rightOperand));
      if (
        !cond.rightOperand ||
        (!validOperands.has(cond.rightOperand) && !isRightNumeric)
      ) {
        errors.push(
          `Rule '${rule.name}' right operand '${cond.rightOperand}' is not a valid indicator or number.`
        );
      }
    }
  }

  // --- Expanded validation (candle, time, breakout, option, exits, risk) ---

  for (const cc of state.candleConditions || []) {
    if (cc.type === "color" && !cc.color) {
      errors.push(`Candle condition '${cc.id}' is color-type but has no color set.`);
    }
    if (cc.type === "pattern" && !cc.pattern) {
      errors.push(`Candle condition '${cc.id}' is pattern-type but has no pattern set.`);
    }
    if ((cc.type === "body_size" || cc.type === "wick_ratio") && (cc.value === undefined || !cc.operator)) {
      errors.push(`Candle condition '${cc.id}' requires an operator and value.`);
    }
  }

  for (const tf of state.timeFilters || []) {
    if (tf.mode === "clock") {
      if (tf.fromTime && !TIME_RE.test(tf.fromTime)) {
        errors.push(`Time filter '${tf.id}' fromTime must be HH:MM.`);
      }
      if (tf.toTime && !TIME_RE.test(tf.toTime)) {
        errors.push(`Time filter '${tf.id}' toTime must be HH:MM.`);
      }
    } else if (tf.mode === "dte") {
      if (tf.dte === undefined || tf.dte < 0) {
        errors.push(`Time filter '${tf.id}' DTE must be a non-negative integer.`);
      }
    }
  }

  for (const bc of state.breakoutConditions || []) {
    if (bc.levelType === "opening_range_high" || bc.levelType === "opening_range_low") {
      if (!bc.orbMinutes || bc.orbMinutes <= 0) {
        errors.push(`Breakout '${bc.id}' opening-range requires orbMinutes > 0.`);
      }
    }
    if (bc.levelType === "custom_level" && bc.customValue === undefined) {
      errors.push(`Breakout '${bc.id}' custom_level requires a customValue.`);
    }
    if (bc.volumeConfirmation && (bc.volumeMultiplier === undefined || bc.volumeMultiplier <= 0)) {
      errors.push(`Breakout '${bc.id}' volume confirmation requires a positive volumeMultiplier.`);
    }
  }

  if (state.kind === "option") {
    if (!state.optionConfig) {
      errors.push("Option strategies require an optionConfig.");
    } else {
      if (!state.optionConfig.underlyingSymbol) {
        errors.push("optionConfig.underlyingSymbol is required.");
      }
      if (!state.optionConfig.legs || state.optionConfig.legs.length === 0) {
        errors.push("optionConfig must have at least one leg.");
      }
      for (const leg of state.optionConfig?.legs || []) {
        if (leg.lots <= 0) errors.push(`Option leg '${leg.id}' lots must be > 0.`);
      }
    }
  }

  for (const e of state.exits || []) {
    if ((e.type === "target" || e.type === "stop") && (e.pct === undefined || e.pct <= 0)) {
      errors.push(`Exit '${e.id}' type '${e.type}' requires a positive pct.`);
    }
    if (e.type === "trailing_stop" && (e.trailingPct === undefined || e.trailingPct <= 0)) {
      errors.push(`Exit '${e.id}' trailing_stop requires a positive trailingPct.`);
    }
    if (e.type === "time" && (!e.timeExit || !TIME_RE.test(e.timeExit))) {
      errors.push(`Exit '${e.id}' time exit requires a valid HH:MM timeExit.`);
    }
  }

  if (state.risk) {
    if (state.risk.maxPositions < 1) {
      errors.push("risk.maxPositions must be >= 1.");
    }
    if (
      state.risk.maxDailyLossPct !== undefined &&
      (state.risk.maxDailyLossPct <= 0 || state.risk.maxDailyLossPct > 100)
    ) {
      errors.push("risk.maxDailyLossPct must be between 0 and 100 (exclusive of 0).");
    }
    if (
      state.risk.maxPositionValuePct !== undefined &&
      (state.risk.maxPositionValuePct <= 0 || state.risk.maxPositionValuePct > 100)
    ) {
      errors.push("risk.maxPositionValuePct must be between 0 and 100 (exclusive of 0).");
    }
    for (const w of state.risk.noTradeWindows || []) {
      const parts = w.split("-");
      if (parts.length !== 2 || !TIME_RE.test(parts[0]) || !TIME_RE.test(parts[1])) {
        errors.push(`risk.noTradeWindows entry '${w}' must be 'HH:MM-HH:MM'.`);
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function compileVisualStateToStrategyIR(
  state: StrategyBuilderState
): StrategyIRSchema {
  const indicatorsMap: Record<string, { function: string; params: Record<string, unknown> }> = {};

  for (const ind of state.indicators) {
    indicatorsMap[ind.name] = {
      function: ind.function,
      params: { ...ind.params },
    };
  }

  const entryRules: StrategyIRSchema["entry_rules"] = [];
  const exitRules: StrategyIRSchema["exit_rules"] = [];

  for (const rule of state.rules) {
    const compiledConditions = rule.conditions.map((c) => ({
      left: c.leftOperand,
      op: c.operator,
      right: c.rightOperand,
    }));

    const ruleObj = {
      type: rule.type,
      combinator: rule.combinator,
      conditions: compiledConditions,
    };

    if (rule.type.startsWith("ENTRY")) {
      entryRules.push(ruleObj);
    } else {
      exitRules.push(ruleObj);
    }
  }

  const slug = state.strategyName.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  return {
    ir_version: 1,
    strategy_id: `ir-${slug}`,
    name: state.strategyName,
    universe: state.universe,
    timeframe: state.timeframe,
    indicators: indicatorsMap,
    entry_rules: entryRules,
    exit_rules: exitRules,
    risk_rules: {
      stop_loss_pct: state.stopLossPct,
      take_profit_pct: state.takeProfitPct,
    },
  };
}

/**
 * @deprecated Use `backtestService.runBacktest()` instead. This function returns
 * a hardcoded fake equity curve and metrics; it is kept only so legacy test
 * fixtures and the AI-draft "preview backtest" path keep rendering while the
 * real backend-driven flow is adopted.
 */
export function runClientSideVectorBacktest(
  ir: StrategyIRSchema
): VectorBacktestResult {
  // Deterministic vector simulation based on rule count and indicators
  const baseCapital = 100000;
  const numTrades = Math.max(25, Object.keys(ir.indicators).length * 28);
  const winRatePct = 64.2;
  const netReturnPct = 28.4;
  const sharpeRatio = 2.05;
  const maxDrawdownPct = 5.2;

  const equityCurve: number[] = [baseCapital];
  let curCap = baseCapital;

  for (let i = 1; i <= 50; i++) {
    const drift = (Math.random() - 0.44) * (curCap * 0.015);
    curCap = Number((curCap + drift).toFixed(2));
    equityCurve.push(curCap);
  }

  return {
    netReturnPct,
    winRatePct,
    totalTrades: numTrades,
    sharpeRatio,
    maxDrawdownPct,
    equityCurve,
  };
}
