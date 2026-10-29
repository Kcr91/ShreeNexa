// Strategy Builder frontend types. Mirrors backend/app/strategy/ir.py (StrategyIR).
// Backward compatibility: the pre-existing fields are preserved so the current
// StrategyBuilderWidget keeps rendering while Phase 2+ layers on richer UI.

// --- Strategy metadata enums -------------------------------------------------

export type StrategyKind = "stock" | "option" | "futures" | "investing" | "composite";

export type StrategyHorizon = "intraday" | "swing" | "positional" | "investing";

export type StrategyType =
  | "trend_following"
  | "swing_trading"
  | "mean_reversion"
  | "option_selling"
  | "other";

// --- Indicators --------------------------------------------------------------

export type IndicatorFunction =
  | "ema"
  | "sma"
  | "rsi"
  | "macd"
  | "vwap"
  | "bollinger"
  | "atr"
  | "supertrend"
  | "adx"
  | "stochastic"
  | "obv"
  | "cci"
  | "williams_r"
  | "ichimoku"
  | "pivot_points"
  | "donchian"
  | "keltner"
  | "aroon"
  | "mfi"
  | "psar"
  | "volume_sma"
  | "prev_day_high"
  | "prev_day_low"
  | "prev_day_close"
  | "prev_day_open"
  | "opening_range_high"
  | "opening_range_low"
  | "custom";

export interface IndicatorNode {
  id: string;
  name: string;
  function: IndicatorFunction;
  params: Record<string, number | string>;
}

// --- Rule operators ----------------------------------------------------------

export type RuleOperator =
  | "CROSS_ABOVE"
  | "CROSS_BELOW"
  | "GREATER_THAN"
  | "LESS_THAN"
  | "EQUALS"
  | "GREATER_THAN_EQ"
  | "LESS_THAN_EQ"
  | "NOT_EQUALS"
  | "BETWEEN"
  | "PCT_CHANGE_GT"
  | "PCT_CHANGE_LT";

export type RuleBlockType = "ENTRY_LONG" | "EXIT_LONG" | "ENTRY_SHORT" | "EXIT_SHORT";

export interface RuleCondition {
  id: string;
  leftOperand: string;
  operator: RuleOperator;
  rightOperand: string;
  // Optional secondary bound for BETWEEN / PCT_CHANGE ranges
  rightOperand2?: string;
  // Optional lookback for PCT_CHANGE_* operators
  lookback?: number;
}

export interface StrategyRuleBlock {
  id: string;
  name: string;
  type: RuleBlockType;
  conditions: RuleCondition[];
  combinator: "AND" | "OR";
}

// --- Candle conditions -------------------------------------------------------

export type CandleColor = "green" | "red" | "doji";

export type CandlePattern =
  | "bullish_engulfing"
  | "bearish_engulfing"
  | "hammer"
  | "inverted_hammer"
  | "morning_star"
  | "evening_star"
  | "doji"
  | "spinning_top"
  | "marubozu"
  | "harami"
  | "piercing_line"
  | "dark_cloud_cover"
  | "three_white_soldiers"
  | "three_black_crows";

export type CandleConditionType = "color" | "pattern" | "body_size" | "wick_ratio";

export interface CandleCondition {
  id: string;
  type: CandleConditionType;
  color?: CandleColor;
  pattern?: CandlePattern;
  operator?: RuleOperator;
  value?: number;
  // Which candle: 0 = current bar, -1 = previous, -2 = two bars ago, etc.
  barOffset: number;
  dayReference?: "current_day" | "previous_day";
}

// --- Time filters ------------------------------------------------------------

export type TimeFilterMode = "clock" | "from_open" | "to_close" | "dte";

export interface TimeFilter {
  id: string;
  mode: TimeFilterMode;
  fromTime?: string; // HH:MM
  toTime?: string; // HH:MM
  fromMinutes?: number;
  toMinutes?: number;
  dte?: number;
}

// --- Breakout conditions -----------------------------------------------------

export type BreakoutLevelType =
  | "prev_day_high"
  | "prev_day_low"
  | "prev_day_close"
  | "opening_range_high"
  | "opening_range_low"
  | "pivot"
  | "support"
  | "resistance"
  | "custom_level";

export interface BreakoutCondition {
  id: string;
  levelType: BreakoutLevelType;
  direction: "above" | "below";
  orbMinutes?: number;
  customValue?: number;
  volumeConfirmation?: boolean;
  volumeMultiplier?: number;
}

// --- Options -----------------------------------------------------------------

export type StrikeSelectorType = "atm" | "delta" | "premium" | "absolute";

export interface StrikeSelector {
  type: StrikeSelectorType;
  offset?: number;
  targetDelta?: number;
  targetPremium?: number;
  absoluteStrike?: number;
}

export type ExpiryType = "weekly" | "monthly" | "exact";

export interface ExpiryRule {
  type: ExpiryType;
  offset: number;
  exactDate?: string;
}

export interface OptionLegDef {
  id: string;
  optionType: "CE" | "PE";
  strike: StrikeSelector;
  side: "BUY" | "SELL";
  lots: number;
}

export interface OptionConfig {
  underlyingSymbol: string;
  underlyingSegment: string;
  expiryRule: ExpiryRule;
  legs: OptionLegDef[];
}

// --- Sizing & Risk & Exits ---------------------------------------------------

export type SizingType =
  | "fixed_qty"
  | "fixed_value"
  | "pct_capital"
  | "risk_pct"
  | "lots"
  | "kelly_fraction";

export interface SizingConfig {
  type: SizingType;
  qty?: number;
  value?: number;
  pct?: number;
  riskPct?: number;
  stopRef?: string;
  lots?: number;
  kellyCap?: number;
}

export interface RiskConfig {
  maxPositions: number;
  maxDailyLossPct?: number;
  maxDailyLossAbs?: number;
  maxPositionValuePct?: number;
  noTradeWindows: string[]; // e.g. ["09:15-09:20", "15:15-15:30"]
  maxTradesPerDay?: number;
}

export type ExitType = "target" | "stop" | "trailing_stop" | "time" | "signal";

export interface ExitRuleConfig {
  id: string;
  type: ExitType;
  pct?: number;
  trailingPct?: number;
  timeExit?: string;
  signalRuleId?: string;
}

// --- Top-level builder state -------------------------------------------------

export interface StrategyBuilderState {
  strategyName: string;
  universe: string;
  timeframe: string;
  indicators: IndicatorNode[];
  rules: StrategyRuleBlock[];
  stopLossPct: number;
  takeProfitPct: number;

  kind: StrategyKind;
  horizon: StrategyHorizon;
  strategyType: StrategyType;

  candleConditions: CandleCondition[];
  timeFilters: TimeFilter[];
  breakoutConditions: BreakoutCondition[];

  optionConfig?: OptionConfig;

  exits: ExitRuleConfig[];
  sizing: SizingConfig;
  risk: RiskConfig;

  slippagePct?: number;
  slippagePoints?: number;
}

export const DEFAULT_SIZING: SizingConfig = {
  type: "fixed_value",
  value: 50000,
};

export const DEFAULT_RISK: RiskConfig = {
  maxPositions: 5,
  maxDailyLossPct: 3.0,
  noTradeWindows: [],
};

export const DEFAULT_STRATEGY_META = {
  kind: "stock" as StrategyKind,
  horizon: "intraday" as StrategyHorizon,
  strategyType: "trend_following" as StrategyType,
};

// --- Legacy flat IR (kept for compileVisualStateToStrategyIR consumers) -----

export interface StrategyIRSchema {
  ir_version: number;
  strategy_id: string;
  name: string;
  universe: string;
  timeframe: string;
  indicators: Record<string, { function: string; params: Record<string, unknown> }>;
  entry_rules: Array<{
    type: string;
    combinator: string;
    conditions: Array<{ left: string; op: string; right: string }>;
  }>;
  exit_rules: Array<{
    type: string;
    combinator: string;
    conditions: Array<{ left: string; op: string; right: string }>;
  }>;
  risk_rules: {
    stop_loss_pct: number;
    take_profit_pct: number;
  };
}

export interface VectorBacktestResult {
  netReturnPct: number;
  winRatePct: number;
  totalTrades: number;
  sharpeRatio: number;
  maxDrawdownPct: number;
  equityCurve: number[];
}

export interface StrategyBuilderWidgetSettings {
  showJsonPreview: boolean;
  defaultUniverse: string;
}
