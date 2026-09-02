import { describe, expect, it } from "vitest";
import { calculateStockMargin, calculateMultiLegOptionMargin } from "./margin";
import { StockOrder, OptionLeg } from "./types";

describe("Order Margin and Regulatory Cost Calculations", () => {
  it("calculates stock margin correctly for CNC delivery and MIS intraday leverage", () => {
    const cncOrder: StockOrder = {
      symbol: "RELIANCE",
      side: "BUY",
      orderType: "LIMIT",
      productType: "CNC",
      quantity: 100,
      price: 3000,
    };

    const cncMargin = calculateStockMargin(cncOrder, 500000);
    // Trade value = 300,000. CNC = 100% margin -> 300,000
    expect(cncMargin.totalRequiredMargin).toBe(300000);
    expect(cncMargin.estimatedCosts).toBeGreaterThan(0);
    expect(cncMargin.isSufficient).toBe(true);

    const misOrder: StockOrder = { ...cncOrder, productType: "MIS" };
    const misMargin = calculateStockMargin(misOrder, 500000);
    // MIS = 20% margin -> 60,000
    expect(misMargin.totalRequiredMargin).toBe(60000);
  });

  it("calculates multi-leg options margin and grants hedging benefit offset", () => {
    // 1. Naked Short Strangle (Sell 24500 CE, Sell 24000 PE)
    const nakedStrangle: OptionLeg[] = [
      { id: "1", symbol: "NIFTY", expiry: "2026-01-29", strike: 24500, optionType: "CE", side: "SELL", quantity: 50, premium: 140 },
      { id: "2", symbol: "NIFTY", expiry: "2026-01-29", strike: 24000, optionType: "PE", side: "SELL", quantity: 50, premium: 130 },
    ];
    const nakedMargin = calculateMultiLegOptionMargin(nakedStrangle, 1000000);
    expect(nakedMargin.totalRequiredMargin).toBeGreaterThan(200000);
    expect(nakedMargin.hedgingBenefit).toBe(0);

    // 2. Iron Condor (Naked Strangle + Buy 24700 CE + Buy 23800 PE protective wings)
    const ironCondor: OptionLeg[] = [
      ...nakedStrangle,
      { id: "3", symbol: "NIFTY", expiry: "2026-01-29", strike: 24700, optionType: "CE", side: "BUY", quantity: 50, premium: 60 },
      { id: "4", symbol: "NIFTY", expiry: "2026-01-29", strike: 23800, optionType: "PE", side: "BUY", quantity: 50, premium: 50 },
    ];
    const condorMargin = calculateMultiLegOptionMargin(ironCondor, 1000000);

    // Hedging benefit reduces net required margin significantly
    expect(condorMargin.hedgingBenefit).toBeGreaterThan(0);
    expect(condorMargin.totalRequiredMargin).toBeLessThan(nakedMargin.totalRequiredMargin);
  });
});
