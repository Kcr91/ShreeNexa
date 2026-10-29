import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OptionConfigPanel } from "./OptionConfigPanel";
import { createDefaultStrategyState } from "../defaults";
import { compileVisualToCanonicalIR, decompileCanonicalIRToVisual } from "../canonical";
import { StrategyBuilderState } from "../types";

function harness(initial?: Partial<StrategyBuilderState>) {
  let state: StrategyBuilderState = { ...createDefaultStrategyState(), kind: "option", ...initial };
  const onChange = (next: StrategyBuilderState) => {
    state = next;
    rerender(<OptionConfigPanel state={state} onChange={onChange} />);
  };
  const { rerender } = render(<OptionConfigPanel state={state} onChange={onChange} />);
  return { getState: () => state };
}

describe("OptionConfigPanel", () => {
  it("renders underlying, expiry, templates and legs sections", () => {
    harness();
    expect(screen.getByTestId("option-config-panel")).toBeInTheDocument();
    expect(screen.getByLabelText("Underlying symbol")).toBeInTheDocument();
    expect(screen.getByLabelText("Expiry type")).toBeInTheDocument();
    expect(screen.getByTestId("template-short-straddle")).toBeInTheDocument();
    expect(screen.getByText(/No legs defined/)).toBeInTheDocument();
  });

  it("applies Short Straddle template with two SELL legs at ATM+0", () => {
    const h = harness();
    fireEvent.click(screen.getByTestId("template-short-straddle"));
    const cfg = h.getState().optionConfig!;
    expect(cfg.legs).toHaveLength(2);
    expect(cfg.legs.every((l) => l.side === "SELL")).toBe(true);
    expect(cfg.legs.map((l) => l.optionType).sort()).toEqual(["CE", "PE"]);
    for (const leg of cfg.legs) {
      expect(leg.strike.type).toBe("atm");
      if (leg.strike.type === "atm") expect(leg.strike.offset).toBe(0);
    }
  });

  it("applies Iron Condor template with four legs", () => {
    const h = harness();
    fireEvent.click(screen.getByTestId("template-iron-condor"));
    const legs = h.getState().optionConfig!.legs;
    expect(legs).toHaveLength(4);
    expect(legs.filter((l) => l.optionType === "CE")).toHaveLength(2);
    expect(legs.filter((l) => l.optionType === "PE")).toHaveLength(2);
    expect(legs.filter((l) => l.side === "BUY")).toHaveLength(2);
    expect(legs.filter((l) => l.side === "SELL")).toHaveLength(2);
  });

  it("allows adding a blank leg and switching to delta strike", () => {
    const h = harness();
    fireEvent.click(screen.getByRole("button", { name: "+ Leg" }));
    let legs = h.getState().optionConfig!.legs;
    expect(legs).toHaveLength(1);

    const strikeSelect = screen.getByLabelText(`Strike method for ${legs[0].id}`) as HTMLSelectElement;
    fireEvent.change(strikeSelect, { target: { value: "delta" } });
    legs = h.getState().optionConfig!.legs;
    expect(legs[0].strike.type).toBe("delta");
    expect(legs[0].strike.targetDelta).toBeCloseTo(0.3);
  });
});

describe("Option strategy IR compilation + round-trip", () => {
  it("compiles an Iron Condor into OptionLegsUniverse and round-trips it", () => {
    const base = createDefaultStrategyState();
    const state: StrategyBuilderState = {
      ...base,
      kind: "option",
      strategyName: "IC-NIFTY",
      optionConfig: {
        underlyingSymbol: "NIFTY",
        underlyingSegment: "NSE_IDX",
        expiryRule: { type: "weekly", offset: 0 },
        legs: [
          { id: "leg-1", optionType: "PE", strike: { type: "atm", offset: -2 }, side: "SELL", lots: 1 },
          { id: "leg-2", optionType: "PE", strike: { type: "atm", offset: -5 }, side: "BUY", lots: 1 },
          { id: "leg-3", optionType: "CE", strike: { type: "atm", offset: 2 }, side: "SELL", lots: 1 },
          { id: "leg-4", optionType: "CE", strike: { type: "atm", offset: 5 }, side: "BUY", lots: 1 },
        ],
      },
    };

    const ir = compileVisualToCanonicalIR(state);
    expect(ir.kind).toBe("option");
    expect(ir.universe.type).toBe("option_legs");
    if (ir.universe.type === "option_legs") {
      expect(ir.universe.underlying.symbol).toBe("NIFTY");
      expect(ir.universe.expiry_rule.type).toBe("weekly");
      expect(ir.universe.legs).toHaveLength(4);
      expect(ir.universe.legs[0].strike.type).toBe("atm");
      expect(ir.universe.legs[0].strike.offset).toBe(-2);
      expect(ir.universe.legs[0].side).toBe("SELL");
      expect(ir.universe.legs[0].option_type).toBe("PE");
    }

    const back = decompileCanonicalIRToVisual(ir);
    expect(back.kind).toBe("option");
    expect(back.optionConfig?.legs).toHaveLength(4);
    expect(back.optionConfig?.legs[0].optionType).toBe("PE");
    expect(back.optionConfig?.legs[0].side).toBe("SELL");
    const strike0 = back.optionConfig?.legs[0].strike;
    expect(strike0?.type).toBe("atm");
    if (strike0?.type === "atm") expect(strike0.offset).toBe(-2);
  });

  it("round-trips a delta-strike leg", () => {
    const base = createDefaultStrategyState();
    const state: StrategyBuilderState = {
      ...base,
      kind: "option",
      optionConfig: {
        underlyingSymbol: "BANKNIFTY",
        underlyingSegment: "NSE_IDX",
        expiryRule: { type: "weekly", offset: 1 },
        legs: [
          { id: "leg-1", optionType: "CE", strike: { type: "delta", targetDelta: 0.35 }, side: "BUY", lots: 1 },
        ],
      },
    };
    const ir = compileVisualToCanonicalIR(state);
    if (ir.universe.type === "option_legs") {
      expect(ir.universe.legs[0].strike.type).toBe("delta");
      expect(ir.universe.legs[0].strike.target).toBeCloseTo(0.35);
    }
    const back = decompileCanonicalIRToVisual(ir);
    const strike = back.optionConfig?.legs[0].strike;
    expect(strike?.type).toBe("delta");
    if (strike?.type === "delta") expect(strike.targetDelta).toBeCloseTo(0.35);
  });
});
