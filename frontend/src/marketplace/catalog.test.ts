import { describe, expect, it } from "vitest";
import { MARKETPLACE_CATALOG } from "./catalog";

describe("Marketplace Strategy Catalog", () => {
  it("contains curated high-grade strategies with valid StrategyIR", () => {
    expect(MARKETPLACE_CATALOG.length).toBeGreaterThanOrEqual(4);

    for (const strategy of MARKETPLACE_CATALOG) {
      expect(strategy.id).toBeTruthy();
      expect(strategy.title).toBeTruthy();
      expect(strategy.author.name).toBeTruthy();
      expect(strategy.performance.cagrPct).toBeGreaterThan(0);
      expect(strategy.performance.sharpeRatio).toBeGreaterThan(1.0);
      expect(strategy.performance.maxDrawdownPct).toBeGreaterThan(0);
      expect(strategy.strategyIR.ir_version).toBe(1);
      expect(strategy.strategyIR.indicators).toBeDefined();
      expect(strategy.strategyIR.entry_rules.length).toBeGreaterThan(0);
    }
  });
});
