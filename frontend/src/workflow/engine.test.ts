import { describe, expect, it } from "vitest";
import { TerminalWorkflowEngine } from "./engine";

describe("Terminal Workflow Orchestrator Engine", () => {
  it("ingests tick stream, computes indicators, triggers rule, dispatches order, and calculates PnL", () => {
    const engine = new TerminalWorkflowEngine("RELIANCE", 3, 5, 5);

    // Feed initial declining prices so fast EMA < slow EMA
    const initialTicks = [2500, 2490, 2480, 2470, 2460, 2450];
    for (const price of initialTicks) {
      const res = engine.processTick(price);
      expect(res.signal).toBe("HOLD");
      expect(res.generatedOrder).toBeUndefined();
    }

    // Now inject rapid upward price surge to create Golden Cross (fast EMA > slow EMA)
    const surgeTicks = [2470, 2495, 2520, 2550];
    let triggered = false;

    for (const price of surgeTicks) {
      const res = engine.processTick(price);
      if (res.signal === "BUY") {
        triggered = true;
        expect(res.generatedOrder).toBeDefined();
        expect(res.generatedOrder?.symbol).toBe("RELIANCE");
        expect(res.generatedOrder?.side).toBe("BUY");
        expect(res.generatedOrder?.status).toBe("FILLED");
        expect(res.updatedPositions).toHaveLength(1);
        expect(res.updatedPositions[0].symbol).toBe("RELIANCE");
      }
    }

    expect(triggered).toBe(true);

    // Subsequent tick higher reconciles positive unrealized PnL
    const higherTickRes = engine.processTick(2600);
    expect(higherTickRes.totalUnrealizedPnl).toBeGreaterThan(0);
    expect(higherTickRes.updatedPositions[0].unrealizedPnl).toBeGreaterThan(0);
  });
});
