export type IndicatorFunction = "ema" | "sma" | "rsi" | "macd" | "vwap";

export type RuleOperator =
  | "CROSS_ABOVE"
  | "CROSS_BELOW"
  | "GREATER_THAN"
  | "LESS_THAN"
  | "EQUALS";

export type RuleBlockType = "ENTRY_LONG" | "EXIT_LONG" | "ENTRY_SHORT" | "EXIT_SHORT";

export interface IndicatorNode {
  id: string;
  name: string;
  function: IndicatorFunction;
  params: Record<string, number | string>;
}

export interface RuleCondition {
  id: string;
  leftOperand: string;
  operator: RuleOperator;
  rightOperand: string;
}

export interface StrategyRuleBlock {
  id: string;
  name: string;
  type: RuleBlockType;
  conditions: RuleCondition[];
  combinator: "AND" | "OR";
}

export interface StrategyBuilderState {
  strategyName: string;
  universe: string;
  timeframe: string;
  indicators: IndicatorNode[];
  rules: StrategyRuleBlock[];
  stopLossPct: number;
  takeProfitPct: number;
}

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
