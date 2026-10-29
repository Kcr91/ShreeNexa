import { describe, expect, it } from "vitest";
import {
  validateStrategyBuilderState,
  compileVisualStateToStrategyIR,
  runClientSideVectorBacktest,
} from "./compiler";
import {
  compileVisualToCanonicalIR,
  decompileCanonicalIRToVisual,
} from "./canonical";
import {
  StrategyBuilderState,
  DEFAULT_SIZING,
  DEFAULT_RISK,
  DEFAULT_STRATEGY_META,
} from "./types";

function makeValidState(overrides: Partial<StrategyBuilderState> = {}): StrategyBuilderState {
  return {
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
    ...DEFAULT_STRATEGY_META,
    candleConditions: [],
    timeFilters: [],
    breakoutConditions: [],
    exits: [],
    sizing: { ...DEFAULT_SIZING },
    risk: { ...DEFAULT_RISK },
    ...overrides,
  };
}

describe("Visual Strategy Builder Compiler and Backtest Runner", () => {
  it("validates a complete strategy state successfully", () => {
    const res = validateStrategyBuilderState(makeValidState());
    expect(res.isValid).toBe(true);
    expect(res.errors).toHaveLength(0);
  });

  it("detects missing strategy name or undefined rule operands", () => {
    const invalidState = makeValidState({
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
    });
    const res = validateStrategyBuilderState(invalidState);
    expect(res.isValid).toBe(false);
    expect(res.errors.length).toBeGreaterThan(0);
  });

  it("compiles visual state into compliant StrategyIR schema", () => {
    const ir = compileVisualStateToStrategyIR(makeValidState());
    expect(ir.ir_version).toBe(1);
    expect(ir.name).toBe("NIFTY EMA Cross");
    expect(ir.indicators["fast_ema"]).toBeDefined();
    expect(ir.entry_rules).toHaveLength(1);
    expect(ir.exit_rules).toHaveLength(1);
    expect(ir.risk_rules.stop_loss_pct).toBe(1.0);
  });

  it("runs client-side vector backtest and outputs equity curve metrics", () => {
    const ir = compileVisualStateToStrategyIR(makeValidState());
    const result = runClientSideVectorBacktest(ir);
    expect(result.netReturnPct).toBeGreaterThan(0);
    expect(result.winRatePct).toBeGreaterThan(50);
    expect(result.equityCurve.length).toBe(51);
    expect(result.sharpeRatio).toBeGreaterThan(1.0);
  });
});

describe("Expanded validation", () => {
  it("flags candle condition missing required fields", () => {
    const st = makeValidState({
      candleConditions: [{ id: "cc1", type: "color", barOffset: 0 }],
    });
    const res = validateStrategyBuilderState(st);
    expect(res.isValid).toBe(false);
    expect(res.errors.join(" ")).toMatch(/color/);
  });

  it("flags time filter with bad HH:MM", () => {
    const st = makeValidState({
      timeFilters: [{ id: "tf1", mode: "clock", fromTime: "9:15" }],
    });
    const res = validateStrategyBuilderState(st);
    expect(res.isValid).toBe(false);
    expect(res.errors.join(" ")).toMatch(/HH:MM/);
  });

  it("flags breakout opening-range without minutes", () => {
    const st = makeValidState({
      breakoutConditions: [
        { id: "b1", levelType: "opening_range_high", direction: "above" },
      ],
    });
    const res = validateStrategyBuilderState(st);
    expect(res.isValid).toBe(false);
    expect(res.errors.join(" ")).toMatch(/orbMinutes/);
  });

  it("flags option strategy without optionConfig", () => {
    const st = makeValidState({ kind: "option" });
    const res = validateStrategyBuilderState(st);
    expect(res.isValid).toBe(false);
    expect(res.errors.join(" ")).toMatch(/optionConfig/);
  });

  it("flags trailing_stop exit missing trailingPct", () => {
    const st = makeValidState({
      exits: [{ id: "e1", type: "trailing_stop" }],
    });
    const res = validateStrategyBuilderState(st);
    expect(res.isValid).toBe(false);
    expect(res.errors.join(" ")).toMatch(/trailing/);
  });

  it("flags malformed noTradeWindows entry", () => {
    const st = makeValidState({
      risk: { ...DEFAULT_RISK, noTradeWindows: ["0915-0920"] },
    });
    const res = validateStrategyBuilderState(st);
    expect(res.isValid).toBe(false);
    expect(res.errors.join(" ")).toMatch(/HH:MM-HH:MM/);
  });
});

describe("Canonical IR round-trip", () => {
  it("round-trips a simple stock strategy", () => {
    const original = makeValidState();
    const canonical = compileVisualToCanonicalIR(original);
    const back = decompileCanonicalIRToVisual(canonical);

    expect(back.strategyName).toBe(original.strategyName);
    expect(back.kind).toBe("stock");
    expect(back.horizon).toBe("intraday");
    expect(back.strategyType).toBe("trend_following");
    expect(back.timeframe).toBe(original.timeframe);
    expect(Object.keys(back.indicators.map((i) => i.name).sort())).toEqual(
      Object.keys(["fast_ema", "slow_ema"].sort())
    );
    // Entry + Exit rule blocks preserved
    expect(back.rules.filter((r) => r.type === "ENTRY_LONG")).toHaveLength(1);
    expect(back.rules.filter((r) => r.type === "EXIT_LONG")).toHaveLength(1);
    expect(back.stopLossPct).toBe(1.0);
    expect(back.takeProfitPct).toBe(3.0);
  });

  it("round-trips an option strategy with multi-leg config", () => {
    const original = makeValidState({
      kind: "option",
      optionConfig: {
        underlyingSymbol: "NIFTY",
        underlyingSegment: "IDX_I",
        expiryRule: { type: "weekly", offset: 0 },
        legs: [
          {
            id: "ce1",
            optionType: "CE",
            strike: { type: "atm", offset: 0 },
            side: "SELL",
            lots: 1,
          },
          {
            id: "pe1",
            optionType: "PE",
            strike: { type: "delta", targetDelta: 0.3 },
            side: "SELL",
            lots: 1,
          },
        ],
      },
    });
    const canonical = compileVisualToCanonicalIR(original);
    expect(canonical.universe.type).toBe("option_legs");

    const back = decompileCanonicalIRToVisual(canonical);
    expect(back.kind).toBe("option");
    expect(back.optionConfig?.legs).toHaveLength(2);
    expect(back.optionConfig?.legs[0].strike.type).toBe("atm");
    expect(back.optionConfig?.legs[1].strike.type).toBe("delta");
    expect(back.optionConfig?.legs[1].strike.targetDelta).toBeCloseTo(0.3);
  });

  it("round-trips trailing stop and time exits", () => {
    const original = makeValidState({
      exits: [
        { id: "trail", type: "trailing_stop", trailingPct: 1.25 },
        { id: "eod", type: "time", timeExit: "15:15" },
      ],
    });
    const canonical = compileVisualToCanonicalIR(original);
    const trail = canonical.exits.find((e) => e.id === "trail");
    const eod = canonical.exits.find((e) => e.id === "eod");
    expect(trail?.trailing_pct).toBe(1.25);
    expect(eod?.at).toBe("15:15");

    const back = decompileCanonicalIRToVisual(canonical);
    const backTrail = back.exits.find((e) => e.id === "trail");
    const backEod = back.exits.find((e) => e.id === "eod");
    expect(backTrail?.trailingPct).toBe(1.25);
    expect(backEod?.timeExit).toBe("15:15");
  });

  it("round-trips time filters and breakout with volume confirmation", () => {
    const original = makeValidState({
      timeFilters: [{ id: "tf1", mode: "clock", fromTime: "09:30", toTime: "15:00" }],
      breakoutConditions: [
        {
          id: "b1",
          levelType: "opening_range_high",
          direction: "above",
          orbMinutes: 15,
          volumeConfirmation: true,
          volumeMultiplier: 1.5,
        },
      ],
    });
    const canonical = compileVisualToCanonicalIR(original);
    expect(canonical._ui?.timeFilters).toHaveLength(1);
    expect(canonical._ui?.breakoutConditions).toHaveLength(1);

    const back = decompileCanonicalIRToVisual(canonical);
    expect(back.timeFilters[0].fromTime).toBe("09:30");
    expect(back.breakoutConditions[0].orbMinutes).toBe(15);
    expect(back.breakoutConditions[0].volumeMultiplier).toBe(1.5);
  });
});
