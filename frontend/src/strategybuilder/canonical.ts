/**
 * Lossless Canonical StrategyIR Compiler & Decompiler for the Visual Strategy
 * Builder. Mirrors backend/app/strategy/ir.py (StrategyIR).
 */

import {
  StrategyBuilderState,
  IndicatorNode,
  StrategyRuleBlock,
  RuleCondition,
  RuleOperator,
  CandleCondition,
  TimeFilter,
  BreakoutCondition,
  OptionConfig,
  OptionLegDef,
  SizingConfig,
  RiskConfig,
  ExitRuleConfig,
  StrategyKind,
  StrategyHorizon,
  StrategyType,
  DEFAULT_SIZING,
  DEFAULT_RISK,
  DEFAULT_STRATEGY_META,
} from "./types";

// --- Canonical IR shapes (match backend StrategyIR JSON) ---------------------

export interface CanonicalIndicatorDef {
  fn: string;
  params?: Record<string, unknown>;
  source?: string;
  indicator_def_id?: number | null;
}

export interface CanonicalSignalNode {
  node: string;
  left?: unknown;
  op?: string;
  right?: unknown;
  children?: CanonicalSignalNode[];
  child?: CanonicalSignalNode;
  // PriceLevelBreak
  level?: unknown;
  direction?: "above" | "below";
  after?: CanonicalSignalNode;
  // TimeWindow
  mode?: "clock" | "from_open" | "to_close" | "dte";
  from?: string;
  to?: string;
  dte?: number;
  // PctChange
  source?: string;
  lookback?: number;
  value?: number;
  // Sequence
  steps?: CanonicalSignalNode[];
  within?: number;
  // Persist
  bars?: number;
  // Regime
  detector?: string;
  state?: string;
  // StrategySignal
  strategy_id?: number | string;
  signal?: string;
  // CustomPython
  ref?: string;
}

export interface CanonicalEntryRule {
  id: string;
  side: "BUY" | "SELL";
  when: CanonicalSignalNode;
}

export interface CanonicalExitRule {
  id: string;
  type: "target" | "stop" | "time" | "signal" | "trailing_stop";
  pct?: number;
  at?: string;
  when?: CanonicalSignalNode;
  trailing_pct?: number;
}

export interface CanonicalInstrumentRef {
  segment: string;
  security_id: string;
  symbol?: string;
}

export interface CanonicalStrikeSelector {
  type: "atm" | "delta" | "premium" | "absolute";
  offset?: number;
  target?: number;
  strike?: number;
}

export interface CanonicalExpiryRule {
  type: "weekly" | "monthly" | "exact";
  offset: number;
  date?: string;
}

export interface CanonicalOptionLegDef {
  id: string;
  option_type: "CE" | "PE";
  strike: CanonicalStrikeSelector;
  side: "BUY" | "SELL";
  lots: number;
}

export type CanonicalUniverse =
  | {
      type: "index";
      index_name: string;
    }
  | {
      type: "static";
      instruments: CanonicalInstrumentRef[];
    }
  | {
      type: "watchlist";
      watchlist_id: number;
    }
  | {
      type: "screener";
      screener_id: number;
      refresh?: "daily" | "hourly" | "every_bar";
    }
  | {
      type: "option_legs";
      underlying: CanonicalInstrumentRef;
      expiry_rule: CanonicalExpiryRule;
      legs: CanonicalOptionLegDef[];
    };

export interface CanonicalSizingRule {
  type: "fixed_qty" | "fixed_value" | "pct_capital" | "risk_pct" | "lots" | "kelly_fraction";
  qty?: number;
  value?: number;
  pct?: number;
  risk_pct?: number;
  stop_ref?: string;
  lots?: number;
  cap?: number;
}

export interface CanonicalRiskRule {
  max_positions: number;
  max_daily_loss_pct?: number;
  max_daily_loss_abs?: number;
  max_position_value_pct?: number;
  no_trade_windows: string[];
  max_trades_per_day?: number;
}

export interface CanonicalStrategyIR {
  ir_version: number;
  name: string;
  kind: StrategyKind;
  horizon: StrategyHorizon;
  strategy_type: StrategyType;
  universe: CanonicalUniverse;
  timeframe: string;
  session?: {
    segment: string;
    timezone?: string;
  };
  indicators: Record<string, CanonicalIndicatorDef>;
  entries: CanonicalEntryRule[];
  exits: CanonicalExitRule[];
  sizing: CanonicalSizingRule;
  risk: CanonicalRiskRule;
  // Non-backend extras preserved for round-trip of UI-only state
  _ui?: {
    candleConditions?: CandleCondition[];
    breakoutConditions?: BreakoutCondition[];
    timeFilters?: TimeFilter[];
    slippagePct?: number;
    slippagePoints?: number;
  };
}

// --- Helpers -----------------------------------------------------------------

const BAR_FIELDS = new Set(["close", "open", "high", "low", "volume", "oi"]);

function operandFromString(ref: string): { field: string } | { ref: string } | { const: number } {
  const n = Number(ref);
  if (!isNaN(n) && ref.trim() !== "") return { const: n };
  if (BAR_FIELDS.has(ref)) return { field: ref };
  return { ref };
}

function operatorToSymbol(op: RuleOperator): string {
  switch (op) {
    case "GREATER_THAN":
      return ">";
    case "LESS_THAN":
      return "<";
    case "GREATER_THAN_EQ":
      return ">=";
    case "LESS_THAN_EQ":
      return "<=";
    case "NOT_EQUALS":
      return "!=";
    case "EQUALS":
      return "==";
    default:
      return "==";
  }
}

function symbolToOperator(sym: string | undefined): RuleOperator {
  switch (sym) {
    case ">":
      return "GREATER_THAN";
    case "<":
      return "LESS_THAN";
    case ">=":
      return "GREATER_THAN_EQ";
    case "<=":
      return "LESS_THAN_EQ";
    case "!=":
      return "NOT_EQUALS";
    case "==":
    default:
      return "EQUALS";
  }
}

function conditionToNode(c: RuleCondition): CanonicalSignalNode {
  const left = operandFromString(c.leftOperand);
  const right = operandFromString(c.rightOperand);

  switch (c.operator) {
    case "CROSS_ABOVE":
      return { node: "CrossOver", left, right };
    case "CROSS_BELOW":
      return { node: "CrossUnder", left, right };
    case "PCT_CHANGE_GT":
      return {
        node: "PctChange",
        source: typeof c.leftOperand === "string" ? c.leftOperand : "close",
        lookback: c.lookback && c.lookback > 0 ? c.lookback : 1,
        op: ">",
        value: Number(c.rightOperand) || 0,
      };
    case "PCT_CHANGE_LT":
      return {
        node: "PctChange",
        source: typeof c.leftOperand === "string" ? c.leftOperand : "close",
        lookback: c.lookback && c.lookback > 0 ? c.lookback : 1,
        op: "<",
        value: Number(c.rightOperand) || 0,
      };
    case "BETWEEN": {
      // Compile BETWEEN as (left >= lower) AND (left <= upper)
      const lower = operandFromString(c.rightOperand);
      const upper = operandFromString(c.rightOperand2 || c.rightOperand);
      return {
        node: "And",
        children: [
          { node: "IndicatorCompare", left, op: ">=", right: lower },
          { node: "IndicatorCompare", left, op: "<=", right: upper },
        ],
      };
    }
    default:
      return {
        node: "IndicatorCompare",
        left,
        op: operatorToSymbol(c.operator),
        right,
      };
  }
}

function extractOperand(opObj: unknown): string {
  if (opObj === null || opObj === undefined) return "close";
  if (typeof opObj === "string") return opObj;
  if (typeof opObj === "number") return String(opObj);
  if (typeof opObj === "object") {
    const o = opObj as Record<string, unknown>;
    if (typeof o.field === "string") return o.field;
    if (typeof o.ref === "string") return o.ref;
    if (o.const !== undefined && o.const !== null) return String(o.const);
  }
  return "close";
}

function candleConditionToSignal(cc: CandleCondition): CanonicalSignalNode {
  // Candle conditions are compiled as CustomPython escape-hatch nodes so the
  // backend's existing signal evaluator can dispatch them without a new node
  // kind. The ref encodes the full visual-builder shape so decompile is lossless.
  return {
    node: "CustomPython",
    ref: `candle:${JSON.stringify(cc)}`,
  };
}

function timeFilterToSignal(tf: TimeFilter): CanonicalSignalNode {
  const node: CanonicalSignalNode = { node: "TimeWindow", mode: tf.mode };
  if (tf.mode === "clock") {
    if (tf.fromTime) node.from = tf.fromTime;
    if (tf.toTime) node.to = tf.toTime;
  } else if (tf.mode === "from_open" || tf.mode === "to_close") {
    if (tf.fromMinutes !== undefined) node.from = String(tf.fromMinutes);
    if (tf.toMinutes !== undefined) node.to = String(tf.toMinutes);
  } else if (tf.mode === "dte") {
    if (tf.dte !== undefined) node.dte = tf.dte;
  }
  return node;
}

function breakoutToSignal(bc: BreakoutCondition): CanonicalSignalNode {
  const level: Record<string, unknown> = { type: bc.levelType };
  if (bc.levelType.startsWith("opening_range") && bc.orbMinutes) {
    level.minutes = bc.orbMinutes;
  }
  if (bc.levelType === "custom_level" && bc.customValue !== undefined) {
    level.custom = bc.customValue;
  }

  const base: CanonicalSignalNode = {
    node: "PriceLevelBreak",
    level,
    direction: bc.direction,
  };

  if (bc.volumeConfirmation) {
    base.after = {
      node: "IndicatorCompare",
      left: { field: "volume" },
      op: ">",
      right: { const: bc.volumeMultiplier ?? 1 },
    };
  }
  return base;
}

function compileOptionConfig(cfg: OptionConfig): CanonicalUniverse {
  const legs: CanonicalOptionLegDef[] = cfg.legs.map((l) => ({
    id: l.id,
    option_type: l.optionType,
    strike: compileStrike(l.strike),
    side: l.side,
    lots: l.lots,
  }));
  return {
    type: "option_legs",
    underlying: {
      segment: cfg.underlyingSegment || "NSE_EQ",
      security_id: cfg.underlyingSymbol,
      symbol: cfg.underlyingSymbol,
    },
    expiry_rule: {
      type: cfg.expiryRule.type,
      offset: cfg.expiryRule.offset,
      date: cfg.expiryRule.exactDate,
    },
    legs,
  };
}

function compileStrike(s: OptionLegDef["strike"]): CanonicalStrikeSelector {
  switch (s.type) {
    case "atm":
      return { type: "atm", offset: s.offset ?? 0 };
    case "delta":
      return { type: "delta", target: s.targetDelta ?? 0.3 };
    case "premium":
      return { type: "premium", target: s.targetPremium ?? 100 };
    case "absolute":
      return { type: "absolute", strike: s.absoluteStrike ?? 0 };
  }
}

function decompileStrike(s: CanonicalStrikeSelector): OptionLegDef["strike"] {
  switch (s.type) {
    case "atm":
      return { type: "atm", offset: s.offset ?? 0 };
    case "delta":
      return { type: "delta", targetDelta: s.target ?? 0.3 };
    case "premium":
      return { type: "premium", targetPremium: s.target ?? 100 };
    case "absolute":
      return { type: "absolute", absoluteStrike: s.strike ?? 0 };
  }
}

function compileSizing(sz: SizingConfig): CanonicalSizingRule {
  return {
    type: sz.type,
    qty: sz.qty,
    value: sz.value,
    pct: sz.pct,
    risk_pct: sz.riskPct,
    stop_ref: sz.stopRef,
    lots: sz.lots,
    cap: sz.kellyCap,
  };
}

function decompileSizing(sz: CanonicalSizingRule | undefined): SizingConfig {
  if (!sz) return { ...DEFAULT_SIZING };
  return {
    type: sz.type,
    qty: sz.qty,
    value: sz.value,
    pct: sz.pct,
    riskPct: sz.risk_pct,
    stopRef: sz.stop_ref,
    lots: sz.lots,
    kellyCap: sz.cap,
  };
}

function compileRisk(r: RiskConfig): CanonicalRiskRule {
  return {
    max_positions: r.maxPositions,
    max_daily_loss_pct: r.maxDailyLossPct,
    max_daily_loss_abs: r.maxDailyLossAbs,
    max_position_value_pct: r.maxPositionValuePct,
    no_trade_windows: r.noTradeWindows ?? [],
    max_trades_per_day: r.maxTradesPerDay,
  };
}

function decompileRisk(r: CanonicalRiskRule | undefined): RiskConfig {
  if (!r) return { ...DEFAULT_RISK };
  return {
    maxPositions: r.max_positions ?? 5,
    maxDailyLossPct: r.max_daily_loss_pct,
    maxDailyLossAbs: r.max_daily_loss_abs,
    maxPositionValuePct: r.max_position_value_pct,
    noTradeWindows: r.no_trade_windows ?? [],
    maxTradesPerDay: r.max_trades_per_day,
  };
}

function compileExit(e: ExitRuleConfig): CanonicalExitRule {
  const out: CanonicalExitRule = { id: e.id, type: e.type };
  if (e.type === "target" || e.type === "stop") {
    if (e.pct !== undefined) out.pct = e.pct;
  } else if (e.type === "trailing_stop") {
    if (e.trailingPct !== undefined) out.trailing_pct = e.trailingPct;
  } else if (e.type === "time") {
    if (e.timeExit) out.at = e.timeExit;
  } else if (e.type === "signal") {
    if (e.signalRuleId) {
      // Represent reference as a StrategySignal node (self-reference by rule id).
      out.when = { node: "StrategySignal", strategy_id: 0, signal: e.signalRuleId };
    }
  }
  return out;
}

function decompileExit(e: CanonicalExitRule): ExitRuleConfig {
  const out: ExitRuleConfig = { id: e.id, type: e.type };
  if (e.pct !== undefined) out.pct = e.pct;
  if (e.trailing_pct !== undefined) out.trailingPct = e.trailing_pct;
  if (e.at) out.timeExit = e.at;
  if (e.when && e.when.node === "StrategySignal" && typeof e.when.signal === "string") {
    out.signalRuleId = e.when.signal;
  }
  return out;
}

// --- Public: compile ---------------------------------------------------------

export function compileVisualToCanonicalIR(state: StrategyBuilderState): CanonicalStrategyIR {
  const indicatorsMap: Record<string, CanonicalIndicatorDef> = {};
  for (const ind of state.indicators) {
    indicatorsMap[ind.name] = {
      fn: ind.function.toUpperCase(),
      params: { ...ind.params },
      source: typeof ind.params?.source === "string" ? (ind.params.source as string) : "close",
    };
  }

  // Compile rule blocks → entries / signal exits
  const entries: CanonicalEntryRule[] = [];
  const signalExits: CanonicalExitRule[] = [];

  const gatingNodes: CanonicalSignalNode[] = [
    ...state.timeFilters.map(timeFilterToSignal),
    ...state.candleConditions.map(candleConditionToSignal),
    ...state.breakoutConditions.map(breakoutToSignal),
  ];

  for (const rule of state.rules) {
    const childNodes: CanonicalSignalNode[] = rule.conditions.map(conditionToNode);

    let compositeSignal: CanonicalSignalNode;
    if (childNodes.length === 1) {
      compositeSignal = childNodes[0];
    } else {
      compositeSignal = {
        node: rule.combinator === "OR" ? "Or" : "And",
        children: childNodes,
      };
    }

    // Only apply gating to entries so exits can fire regardless of time window.
    const isEntry = rule.type.startsWith("ENTRY");
    if (isEntry && gatingNodes.length > 0) {
      compositeSignal = {
        node: "And",
        children: [...gatingNodes, compositeSignal],
      };
    }

    if (isEntry) {
      entries.push({
        id: rule.id || `entry-${entries.length + 1}`,
        side: rule.type === "ENTRY_SHORT" ? "SELL" : "BUY",
        when: compositeSignal,
      });
    } else {
      signalExits.push({
        id: rule.id || `exit-${signalExits.length + 1}`,
        type: "signal",
        when: compositeSignal,
      });
    }
  }

  // Compile explicit exits list; keep legacy stopLossPct / takeProfitPct as a
  // fallback when state.exits is empty so existing widget keeps working.
  let exits: CanonicalExitRule[];
  if (state.exits && state.exits.length > 0) {
    exits = state.exits.map(compileExit);
  } else {
    exits = [
      { id: "tp", type: "target", pct: state.takeProfitPct },
      { id: "sl", type: "stop", pct: state.stopLossPct },
    ];
  }
  exits = exits.concat(signalExits);

  const universe: CanonicalUniverse =
    state.kind === "option" && state.optionConfig
      ? compileOptionConfig(state.optionConfig)
      : { type: "index", index_name: state.universe };

  const ir: CanonicalStrategyIR = {
    ir_version: 1,
    name: state.strategyName,
    kind: state.kind ?? DEFAULT_STRATEGY_META.kind,
    horizon: state.horizon ?? DEFAULT_STRATEGY_META.horizon,
    strategy_type: state.strategyType ?? DEFAULT_STRATEGY_META.strategyType,
    universe,
    timeframe: state.timeframe,
    session: { segment: "NSE_EQ" },
    indicators: indicatorsMap,
    entries,
    exits,
    sizing: compileSizing(state.sizing ?? DEFAULT_SIZING),
    risk: compileRisk(state.risk ?? DEFAULT_RISK),
  };

  // Preserve UI-only state for lossless round-trip.
  const ui: NonNullable<CanonicalStrategyIR["_ui"]> = {};
  if (state.candleConditions.length) ui.candleConditions = state.candleConditions;
  if (state.breakoutConditions.length) ui.breakoutConditions = state.breakoutConditions;
  if (state.timeFilters.length) ui.timeFilters = state.timeFilters;
  if (state.slippagePct !== undefined) ui.slippagePct = state.slippagePct;
  if (state.slippagePoints !== undefined) ui.slippagePoints = state.slippagePoints;
  if (Object.keys(ui).length > 0) ir._ui = ui;

  return ir;
}

// --- Public: decompile -------------------------------------------------------

export function decompileCanonicalIRToVisual(ir: CanonicalStrategyIR): StrategyBuilderState {
  const indicators: IndicatorNode[] = Object.entries(ir.indicators || {}).map(
    ([key, def], idx) => ({
      id: `ind-${idx + 1}`,
      name: key,
      function: ((def.fn || "EMA").toLowerCase() as IndicatorNode["function"]),
      params: (def.params as Record<string, number | string>) || {},
    })
  );

  const rules: StrategyRuleBlock[] = [];

  const parseSignalToConditions = (
    signalNode: CanonicalSignalNode | undefined
  ): { conditions: RuleCondition[]; combinator: "AND" | "OR" } => {
    if (!signalNode) return { conditions: [], combinator: "AND" };

    const leafToCondition = (n: CanonicalSignalNode, idx: number): RuleCondition => {
      let op: RuleOperator = "EQUALS";
      if (n.node === "CrossOver") op = "CROSS_ABOVE";
      else if (n.node === "CrossUnder") op = "CROSS_BELOW";
      else if (n.node === "IndicatorCompare") op = symbolToOperator(n.op);
      else if (n.node === "PctChange") op = n.op === "<" ? "PCT_CHANGE_LT" : "PCT_CHANGE_GT";

      if (n.node === "PctChange") {
        return {
          id: `cond-${idx + 1}`,
          leftOperand: n.source || "close",
          operator: op,
          rightOperand: String(n.value ?? 0),
          lookback: n.lookback,
        };
      }
      return {
        id: `cond-${idx + 1}`,
        leftOperand: extractOperand(n.left),
        operator: op,
        rightOperand: extractOperand(n.right),
      };
    };

    // Entries may be wrapped in an outer And due to time/candle/breakout
    // gating injected during compile. Strip that wrapper by picking only the
    // non-gating children (anything other than TimeWindow, PriceLevelBreak,
    // or candle-encoded CustomPython).
    const isGating = (n: CanonicalSignalNode): boolean =>
      n.node === "TimeWindow" ||
      n.node === "PriceLevelBreak" ||
      (n.node === "CustomPython" && typeof n.ref === "string" && n.ref.startsWith("candle:"));

    let effective = signalNode;
    if (signalNode.node === "And" && Array.isArray(signalNode.children)) {
      const nonGating = signalNode.children.filter((c) => !isGating(c));
      if (nonGating.length === 1) effective = nonGating[0];
      else if (nonGating.length > 1) effective = { node: "And", children: nonGating };
    }

    if ((effective.node === "And" || effective.node === "Or") && Array.isArray(effective.children)) {
      const combinator: "AND" | "OR" = effective.node === "Or" ? "OR" : "AND";
      const conditions = effective.children.map(leafToCondition);
      return { conditions, combinator };
    }
    return { conditions: [leafToCondition(effective, 0)], combinator: "AND" };
  };

  for (const entry of ir.entries || []) {
    const { conditions, combinator } = parseSignalToConditions(entry.when);
    rules.push({
      id: entry.id || `rule-entry-${rules.length + 1}`,
      name: entry.side === "SELL" ? "Short Entry Rule" : "Long Entry Rule",
      type: entry.side === "SELL" ? "ENTRY_SHORT" : "ENTRY_LONG",
      conditions,
      combinator,
    });
  }

  for (const exit of ir.exits || []) {
    if (exit.type === "signal" && exit.when) {
      // Skip self-reference signal-exits (those are decompiled into state.exits only).
      if (exit.when.node === "StrategySignal") continue;
      const { conditions, combinator } = parseSignalToConditions(exit.when);
      rules.push({
        id: exit.id || `rule-exit-${rules.length + 1}`,
        name: "Long Exit Rule",
        type: "EXIT_LONG",
        conditions,
        combinator,
      });
    }
  }

  // Legacy SL/TP mirror for backward-compatible widget consumers.
  let slPct = 1.5;
  let tpPct = 3.5;
  const exits: ExitRuleConfig[] = [];
  for (const exit of ir.exits || []) {
    if (exit.type === "signal" && exit.when && exit.when.node !== "StrategySignal") continue;
    exits.push(decompileExit(exit));
    if (exit.type === "stop" && exit.pct) slPct = exit.pct;
    if (exit.type === "target" && exit.pct) tpPct = exit.pct;
  }

  // Universe extraction
  let universe = "NIFTY 50";
  let optionConfig: OptionConfig | undefined;
  if (ir.universe) {
    if (ir.universe.type === "index") universe = ir.universe.index_name;
    else if (ir.universe.type === "option_legs") {
      optionConfig = {
        underlyingSymbol: ir.universe.underlying.symbol || ir.universe.underlying.security_id,
        underlyingSegment: ir.universe.underlying.segment,
        expiryRule: {
          type: ir.universe.expiry_rule.type,
          offset: ir.universe.expiry_rule.offset,
          exactDate: ir.universe.expiry_rule.date,
        },
        legs: ir.universe.legs.map((l) => ({
          id: l.id,
          optionType: l.option_type,
          strike: decompileStrike(l.strike),
          side: l.side,
          lots: l.lots,
        })),
      };
    }
  }

  const ui = ir._ui || {};

  return {
    strategyName: ir.name || "Imported Strategy",
    universe,
    timeframe: ir.timeframe || "5m",
    indicators:
      indicators.length > 0
        ? indicators
        : [{ id: "ind-1", name: "ema_fast", function: "ema", params: { period: 9 } }],
    rules:
      rules.length > 0
        ? rules
        : [
            {
              id: "rule-1",
              name: "Entry",
              type: "ENTRY_LONG",
              combinator: "AND",
              conditions: [
                {
                  id: "cond-1",
                  leftOperand: "close",
                  operator: "GREATER_THAN",
                  rightOperand: "ema_fast",
                },
              ],
            },
          ],
    stopLossPct: slPct,
    takeProfitPct: tpPct,
    kind: ir.kind,
    horizon: ir.horizon,
    strategyType: ir.strategy_type,
    candleConditions: ui.candleConditions ?? [],
    timeFilters: ui.timeFilters ?? [],
    breakoutConditions: ui.breakoutConditions ?? [],
    optionConfig,
    exits,
    sizing: decompileSizing(ir.sizing),
    risk: decompileRisk(ir.risk),
    slippagePct: ui.slippagePct,
    slippagePoints: ui.slippagePoints,
  };
}
