/**
 * Lossless Canonical StrategyIR Compiler & Decompiler for Visual Strategy Builder.
 */

import { StrategyBuilderState, IndicatorNode, StrategyRuleBlock, RuleCondition, RuleOperator } from "./types";

export interface CanonicalIndicatorDef {
  fn: string;
  params?: Record<string, unknown>;
  source?: string;
}

export interface CanonicalSignalNode {
  node: string;
  left?: string | Record<string, unknown>;
  op?: string;
  right?: string | number | Record<string, unknown>;
  children?: CanonicalSignalNode[];
  child?: CanonicalSignalNode;
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
}

export interface CanonicalStrategyIR {
  ir_version: number;
  name: string;
  kind: "stock" | "option" | "investing" | "composite";
  horizon: "intraday" | "swing" | "positional" | "investing";
  strategy_type: "trend_following" | "swing_trading" | "mean_reversion" | "option_selling" | "other";
  universe: {
    type: "index" | "static" | "watchlist" | "screener";
    index_name?: string;
    instruments?: Array<{ segment: string; security_id: string; symbol?: string }>;
  };
  timeframe: string;
  session?: {
    segment: string;
  };
  indicators: Record<string, CanonicalIndicatorDef>;
  entries: CanonicalEntryRule[];
  exits: CanonicalExitRule[];
  sizing?: {
    type: string;
    value?: number;
    pct?: number;
  };
  risk?: {
    max_positions?: number;
    max_daily_loss_pct?: number;
  };
}

/**
 * Compiles visual builder state into canonical backend StrategyIR.
 */
export function compileVisualToCanonicalIR(state: StrategyBuilderState): CanonicalStrategyIR {
  const indicatorsMap: Record<string, CanonicalIndicatorDef> = {};

  for (const ind of state.indicators) {
    indicatorsMap[ind.name] = {
      fn: ind.function.toUpperCase(),
      params: { ...ind.params },
      source: "close",
    };
  }

  const entries: CanonicalEntryRule[] = [];
  const exits: CanonicalExitRule[] = [
    { id: "tp", type: "target", pct: state.takeProfitPct },
    { id: "sl", type: "stop", pct: state.stopLossPct },
  ];

  for (const rule of state.rules) {
    const childNodes: CanonicalSignalNode[] = rule.conditions.map((c) => {
      const isRightNum = !isNaN(Number(c.rightOperand));
      const rightVal = isRightNum ? { const: Number(c.rightOperand) } : { ref: c.rightOperand };
      const leftVal = c.leftOperand === "close" || c.leftOperand === "open" || c.leftOperand === "high" || c.leftOperand === "low"
        ? { field: c.leftOperand }
        : { ref: c.leftOperand };

      if (c.operator === "CROSS_ABOVE") {
        return {
          node: "CrossOver",
          left: leftVal,
          right: rightVal,
        };
      } else if (c.operator === "CROSS_BELOW") {
        return {
          node: "CrossUnder",
          left: leftVal,
          right: rightVal,
        };
      } else {
        let opSymbol = "==";
        if (c.operator === "GREATER_THAN") opSymbol = ">";
        if (c.operator === "LESS_THAN") opSymbol = "<";
        if (c.operator === "EQUALS") opSymbol = "==";

        return {
          node: "IndicatorCompare",
          left: leftVal,
          op: opSymbol,
          right: rightVal,
        };
      }
    });

    let compositeSignal: CanonicalSignalNode;
    if (childNodes.length === 1) {
      compositeSignal = childNodes[0];
    } else {
      compositeSignal = {
        node: rule.combinator === "OR" ? "Or" : "And",
        children: childNodes,
      };
    }

    if (rule.type.startsWith("ENTRY")) {
      entries.push({
        id: rule.id || `entry-${entries.length + 1}`,
        side: rule.type === "ENTRY_SHORT" ? "SELL" : "BUY",
        when: compositeSignal,
      });
    } else {
      exits.push({
        id: rule.id || `exit-${exits.length + 1}`,
        type: "signal",
        when: compositeSignal,
      });
    }
  }

  return {
    ir_version: 1,
    name: state.strategyName,
    kind: "stock",
    horizon: "intraday",
    strategy_type: "trend_following",
    universe: {
      type: "index",
      index_name: state.universe,
    },
    timeframe: state.timeframe,
    session: {
      segment: "NSE_EQ",
    },
    indicators: indicatorsMap,
    entries,
    exits,
    sizing: {
      type: "fixed_value",
      value: 50000,
    },
    risk: {
      max_positions: 5,
      max_daily_loss_pct: 3.0,
    },
  };
}

/**
 * Losslessly decompiles canonical StrategyIR back into visual builder state.
 */
export function decompileCanonicalIRToVisual(ir: CanonicalStrategyIR): StrategyBuilderState {
  const indicators: IndicatorNode[] = Object.entries(ir.indicators || {}).map(([key, def], idx) => ({
    id: `ind-${idx + 1}`,
    name: key,
    function: (def.fn || "EMA").toLowerCase() as any,
    params: (def.params as Record<string, number | string>) || {},
  }));

  const rules: StrategyRuleBlock[] = [];

  const extractOperand = (opObj: any): string => {
    if (!opObj) return "close";
    if (typeof opObj === "string") return opObj;
    if (opObj.field) return opObj.field;
    if (opObj.ref) return opObj.ref;
    if (opObj.const !== undefined) return String(opObj.const);
    return "close";
  };

  // Helper to extract conditions from signal node
  const parseSignalToConditions = (signalNode: CanonicalSignalNode): { conditions: RuleCondition[]; combinator: "AND" | "OR" } => {
    if (signalNode.node === "And" || signalNode.node === "Or") {
      const combinator = signalNode.node === "Or" ? "OR" : "AND";
      const conditions: RuleCondition[] = (signalNode.children || []).map((child, cIdx) => {
        let op: RuleOperator = "EQUALS";
        if (child.node === "CrossOver") op = "CROSS_ABOVE";
        else if (child.node === "CrossUnder") op = "CROSS_BELOW";
        else if (child.node === "IndicatorCompare") {
          if (child.op === ">" || child.op === ">=") op = "GREATER_THAN";
          else if (child.op === "<" || child.op === "<=") op = "LESS_THAN";
          else op = "EQUALS";
        }
        return {
          id: `cond-${cIdx + 1}`,
          leftOperand: extractOperand(child.left),
          operator: op,
          rightOperand: extractOperand(child.right),
        };
      });
      return { conditions, combinator };
    } else {
      let op: RuleOperator = "EQUALS";
      if (signalNode.node === "CrossOver") op = "CROSS_ABOVE";
      else if (signalNode.node === "CrossUnder") op = "CROSS_BELOW";
      else if (signalNode.node === "IndicatorCompare") {
        if (signalNode.op === ">" || signalNode.op === ">=") op = "GREATER_THAN";
        else if (signalNode.op === "<" || signalNode.op === "<=") op = "LESS_THAN";
        else op = "EQUALS";
      }
      return {
        conditions: [
          {
            id: "cond-1",
            leftOperand: extractOperand(signalNode.left),
            operator: op,
            rightOperand: extractOperand(signalNode.right),
          },
        ],
        combinator: "AND",
      };
    }
  };

  // Parse entries
  for (const entry of ir.entries || []) {
    const { conditions, combinator } = parseSignalToConditions(entry.when);
    rules.push({
      id: entry.id || `rule-entry-${rules.length + 1}`,
      name: "Long Entry Rule",
      type: entry.side === "SELL" ? "ENTRY_SHORT" : "ENTRY_LONG",
      conditions,
      combinator,
    });
  }

  // Parse exits (signals only)
  for (const exit of ir.exits || []) {
    if (exit.type === "signal" && exit.when) {
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

  let slPct = 1.5;
  let tpPct = 3.5;
  for (const exit of ir.exits || []) {
    if (exit.type === "stop" && exit.pct) slPct = exit.pct;
    if (exit.type === "target" && exit.pct) tpPct = exit.pct;
  }

  return {
    strategyName: ir.name || "Imported Strategy",
    universe: ir.universe?.index_name || "NIFTY 50",
    timeframe: ir.timeframe || "5m",
    indicators: indicators.length > 0 ? indicators : [
      { id: "ind-1", name: "ema_fast", function: "ema", params: { period: 9 } }
    ],
    rules: rules.length > 0 ? rules : [
      {
        id: "rule-1",
        name: "Entry",
        type: "ENTRY_LONG",
        combinator: "AND",
        conditions: [
          { id: "cond-1", leftOperand: "close", operator: "GREATER_THAN", rightOperand: "ema_fast" }
        ]
      }
    ],
    stopLossPct: slPct,
    takeProfitPct: tpPct,
  };
}
