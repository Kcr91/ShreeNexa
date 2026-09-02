import { describe, expect, it } from "vitest";
import {
  validateStrategyBuilderState,
  compileVisualStateToStrategyIR,
  runClientSideVectorBacktest,
} from "./compiler";
import { StrategyBuilderState } from "./types";

describe("Visual Strategy Builder Compiler and Backtest Runner", () => {
  const validState: StrategyBuilderState = {
    strategyName: "NIFTY EMA Cross",
    universe: "NIFTY 50",
    timeframe: "15m",
    indicators: [
      { id: "1", name: "fast_ema", function: "ema", params: { period: 9, source: "close" } },
      { id: "2", name: "slow_ema", function: "ema", params: { period: 21, source: "close" } },
    ],
    rules: [
      {
        id: "r1",
        name: "Entry Long",
        type: "ENTRY_LONG",
        combinator: "AND",
        conditions: [
          { id: "c1", leftOperand: "fast_ema", operator: "CROSS_ABOVE", rightOperand: "slow_ema" },
        ],
      },
      {
        id: "r2",
        name: "Exit Long",
        type: "EXIT_LONG",
        combinator: "AND",
        conditions: [
          { id: "c2", leftOperand: "fast_ema", operator: "CROSS_BELOW", rightOperand: "slow_ema" },
        ],
      },
    ],
    stopLossPct: 1.0,
    takeProfitPct: 3.0,
  };

  it("validates a complete strategy state successfully", () => {
    const res = validateStrategyBuilderState(validState);
    expect(res.isValid).toBe(true);
    expect(res.errors).toHaveLength(0);
  });

  it("detects missing strategy name or undefined rule operands", () => {
    const invalidState: StrategyBuilderState = {
      ...validState,
      strategyName: "",
      rules: [
        {
          id: "r1",
          name: "Invalid Rule",
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [
            { id: "c1", leftOperand: "unknown_ind", operator: "CROSS_ABOVE", rightOperand: "slow_ema" },
          ],
        },
      ],
    };

    const res = validateStrategyBuilderState(invalidState);
    expect(res.isValid).toBe(false);
    expect(res.errors.length).toBeGreaterThan(0);
  });

  it("compiles visual state into compliant StrategyIR schema", () => {
    const ir = compileVisualStateToStrategyIR(validState);
    expect(ir.ir_version).toBe(1);
    expect(ir.name).toBe("NIFTY EMA Cross");
    expect(ir.indicators["fast_ema"]).toBeDefined();
    expect(ir.entry_rules).toHaveLength(1);
    expect(ir.exit_rules).toHaveLength(1);
    expect(ir.risk_rules.stop_loss_pct).toBe(1.0);
  });

  it("runs client-side vector backtest and outputs equity curve metrics", () => {
    const ir = compileVisualStateToStrategyIR(validState);
    const result = runClientSideVectorBacktest(ir);

    expect(result.netReturnPct).toBeGreaterThan(0);
    expect(result.winRatePct).toBeGreaterThan(50);
    expect(result.equityCurve.length).toBe(51);
    expect(result.sharpeRatio).toBeGreaterThan(1.0);
  });
});
