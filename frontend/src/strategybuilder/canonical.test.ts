import { describe, expect, it } from "vitest";
import {
  compileVisualToCanonicalIR,
  decompileCanonicalIRToVisual,
} from "./canonical";
import { StrategyBuilderState } from "./types";

describe("Canonical StrategyIR Lossless Round-Trip Compiler & Decompiler", () => {
  const initialVisualState: StrategyBuilderState = {
    strategyName: "Dual EMA Momentum",
    universe: "NIFTY 50",
    timeframe: "15m",
    indicators: [
      { id: "ind-1", name: "ema_9", function: "ema", params: { length: 9 } },
      { id: "ind-2", name: "ema_21", function: "ema", params: { length: 21 } },
    ],
    rules: [
      {
        id: "rule-1",
        name: "Bullish Cross Entry",
        type: "ENTRY_LONG",
        combinator: "AND",
        conditions: [
          {
            id: "cond-1",
            leftOperand: "ema_9",
            operator: "CROSS_ABOVE",
            rightOperand: "ema_21",
          },
        ],
      },
      {
        id: "rule-2",
        name: "Bearish Cross Exit",
        type: "EXIT_LONG",
        combinator: "AND",
        conditions: [
          {
            id: "cond-2",
            leftOperand: "ema_9",
            operator: "CROSS_BELOW",
            rightOperand: "ema_21",
          },
        ],
      },
    ],
    stopLossPct: 1.5,
    takeProfitPct: 3.0,
  };

  it("compiles visual state into valid canonical StrategyIR schema", () => {
    const ir = compileVisualToCanonicalIR(initialVisualState);

    expect(ir.ir_version).toBe(1);
    expect(ir.name).toBe("Dual EMA Momentum");
    expect(ir.kind).toBe("stock");
    expect(ir.timeframe).toBe("15m");
    expect(ir.universe.index_name).toBe("NIFTY 50");
    expect(ir.indicators["ema_9"].fn).toBe("EMA");
    expect(ir.indicators["ema_9"].params?.length).toBe(9);
    expect(ir.entries.length).toBe(1);
    expect(ir.entries[0].when.node).toBe("CrossOver");
    expect(ir.exits.length).toBe(3); // tp, sl, + signal exit
  });

  it("losslessly round-trips UI -> IR -> UI preserving meaning", () => {
    // 1. UI -> IR
    const ir = compileVisualToCanonicalIR(initialVisualState);

    // 2. IR -> UI
    const decompiled = decompileCanonicalIRToVisual(ir);

    expect(decompiled.strategyName).toBe(initialVisualState.strategyName);
    expect(decompiled.universe).toBe(initialVisualState.universe);
    expect(decompiled.timeframe).toBe(initialVisualState.timeframe);
    expect(decompiled.indicators.length).toBe(2);
    expect(decompiled.indicators[0].name).toBe("ema_9");
    expect(decompiled.rules.length).toBe(2);
    expect(decompiled.rules[0].conditions[0].operator).toBe("CROSS_ABOVE");
    expect(decompiled.rules[1].conditions[0].operator).toBe("CROSS_BELOW");
    expect(decompiled.stopLossPct).toBe(1.5);
    expect(decompiled.takeProfitPct).toBe(3.0);
  });

  it("compiles composite AND/OR rules and decompiles correctly", () => {
    const compositeState: StrategyBuilderState = {
      strategyName: "RSI & Trend Strategy",
      universe: "BANKNIFTY",
      timeframe: "5m",
      indicators: [
        { id: "ind-1", name: "rsi_14", function: "rsi", params: { length: 14 } },
        { id: "ind-2", name: "sma_50", function: "sma", params: { length: 50 } },
      ],
      rules: [
        {
          id: "rule-1",
          name: "Trend Pullback Buy",
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [
            {
              id: "cond-1",
              leftOperand: "close",
              operator: "GREATER_THAN",
              rightOperand: "sma_50",
            },
            {
              id: "cond-2",
              leftOperand: "rsi_14",
              operator: "LESS_THAN",
              rightOperand: "35",
            },
          ],
        },
      ],
      stopLossPct: 2.0,
      takeProfitPct: 5.0,
    };

    const ir = compileVisualToCanonicalIR(compositeState);
    expect(ir.entries[0].when.node).toBe("And");
    expect(ir.entries[0].when.children?.length).toBe(2);

    const decompiled = decompileCanonicalIRToVisual(ir);
    expect(decompiled.rules[0].conditions.length).toBe(2);
    expect(decompiled.rules[0].combinator).toBe("AND");
  });
});
