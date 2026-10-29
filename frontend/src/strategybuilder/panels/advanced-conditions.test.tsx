import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TimeFilterPanel } from "./TimeFilterPanel";
import { CandleConditionPanel } from "./CandleConditionPanel";
import { BreakoutPanel } from "./BreakoutPanel";
import { createDefaultStrategyState } from "../defaults";
import { compileVisualToCanonicalIR, decompileCanonicalIRToVisual } from "../canonical";
import { StrategyBuilderState } from "../types";

type PanelProps = { state: StrategyBuilderState; onChange: (s: StrategyBuilderState) => void };

function harness(
  Component: React.ComponentType<PanelProps>,
  initial?: Partial<StrategyBuilderState>
): { getState: () => StrategyBuilderState } {
  let state: StrategyBuilderState = { ...createDefaultStrategyState(), ...initial };
  const onChange = (next: StrategyBuilderState) => {
    state = next;
    rerender(<Component state={state} onChange={onChange} />);
  };
  const { rerender } = render(<Component state={state} onChange={onChange} />);
  return { getState: () => state };
}

describe("TimeFilterPanel", () => {
  it("renders empty state and adds a clock filter", () => {
    const h = harness(TimeFilterPanel);
    expect(screen.getByTestId("time-filter-panel")).toBeInTheDocument();
    expect(screen.getByText(/No time filters yet/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "+ Time Filter" }));
    const s = h.getState();
    expect(s.timeFilters).toHaveLength(1);
    expect(s.timeFilters[0].mode).toBe("clock");
  });

  it("applies a preset for 'Skip first 15 min'", () => {
    const h = harness(TimeFilterPanel);
    fireEvent.click(screen.getByRole("button", { name: "Skip first 15 min" }));
    const s = h.getState();
    expect(s.timeFilters[0].mode).toBe("from_open");
    expect(s.timeFilters[0].fromMinutes).toBe(15);
  });
});

describe("CandleConditionPanel", () => {
  it("adds a color condition and switches to pattern", () => {
    const h = harness(CandleConditionPanel);
    fireEvent.click(screen.getByRole("button", { name: "+ Candle Condition" }));
    let s = h.getState();
    expect(s.candleConditions).toHaveLength(1);
    expect(s.candleConditions[0].type).toBe("color");
    expect(s.candleConditions[0].color).toBe("green");

    const typeSelect = screen.getByLabelText("Candle condition type") as HTMLSelectElement;
    fireEvent.change(typeSelect, { target: { value: "pattern" } });
    s = h.getState();
    expect(s.candleConditions[0].type).toBe("pattern");
  });

  it("adds previous-day shortcut", () => {
    const h = harness(CandleConditionPanel);
    fireEvent.click(screen.getByRole("button", { name: /Prev day was Red/i }));
    const s = h.getState();
    expect(s.candleConditions[0].color).toBe("red");
    expect(s.candleConditions[0].barOffset).toBe(-1);
    expect(s.candleConditions[0].dayReference).toBe("previous_day");
  });
});

describe("BreakoutPanel", () => {
  it("adds a blank breakout and sets ORB minutes", () => {
    const h = harness(BreakoutPanel);
    fireEvent.click(screen.getByRole("button", { name: "+ Breakout" }));
    let s = h.getState();
    expect(s.breakoutConditions).toHaveLength(1);

    const typeSelect = screen.getByLabelText("Breakout level type") as HTMLSelectElement;
    fireEvent.change(typeSelect, { target: { value: "opening_range_high" } });
    s = h.getState();
    expect(s.breakoutConditions[0].levelType).toBe("opening_range_high");
    expect(s.breakoutConditions[0].orbMinutes ?? 15).toBe(15);
  });

  it("applies the ORB + volume preset", () => {
    const h = harness(BreakoutPanel);
    fireEvent.click(screen.getByRole("button", { name: /ORB Breakout/i }));
    const s = h.getState();
    expect(s.breakoutConditions[0].levelType).toBe("opening_range_high");
    expect(s.breakoutConditions[0].volumeConfirmation).toBe(true);
    expect(s.breakoutConditions[0].volumeMultiplier).toBe(1.5);
  });
});

describe("Advanced condition IR compilation + round-trip", () => {
  it("compiles time filters as entry gating and round-trips them", () => {
    const base = createDefaultStrategyState();
    const state: StrategyBuilderState = {
      ...base,
      strategyName: "WithGates",
      indicators: [{ id: "i1", name: "ema_fast", function: "ema", params: { period: 9 } }],
      rules: [
        {
          id: "entry-1",
          name: "Entry",
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [{ id: "c1", leftOperand: "close", operator: "GREATER_THAN", rightOperand: "ema_fast" }],
        },
      ],
      timeFilters: [{ id: "tf1", mode: "clock", fromTime: "09:30", toTime: "15:15" }],
      breakoutConditions: [{ id: "b1", levelType: "prev_day_high", direction: "above" }],
      candleConditions: [{ id: "cc1", type: "color", color: "green", barOffset: 0, dayReference: "current_day" }],
    };

    const ir = compileVisualToCanonicalIR(state);
    // Entry wrapped with And containing the gating nodes
    const entryWhen = ir.entries[0].when;
    expect(entryWhen.node).toBe("And");
    const kinds = (entryWhen.children ?? []).map((c) => c.node);
    expect(kinds).toContain("TimeWindow");
    expect(kinds).toContain("PriceLevelBreak");
    expect(kinds).toContain("CustomPython");

    // Round-trip restores the collections
    const back = decompileCanonicalIRToVisual(ir);
    expect(back.timeFilters).toHaveLength(1);
    expect(back.timeFilters[0].fromTime).toBe("09:30");
    expect(back.breakoutConditions).toHaveLength(1);
    expect(back.breakoutConditions[0].levelType).toBe("prev_day_high");
    expect(back.candleConditions).toHaveLength(1);
    expect(back.candleConditions[0].color).toBe("green");

    // Non-gating entry condition is preserved
    expect(back.rules.filter((r) => r.type === "ENTRY_LONG")).toHaveLength(1);
    const entryRule = back.rules.find((r) => r.type === "ENTRY_LONG")!;
    expect(entryRule.conditions).toHaveLength(1);
    expect(entryRule.conditions[0].leftOperand).toBe("close");
  });
});
