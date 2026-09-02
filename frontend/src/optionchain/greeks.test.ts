import { describe, expect, it } from "vitest";
import { calculateBlackScholesGreeks, generateOptionChain } from "./greeks";

describe("Option Chain Black-Scholes Greeks and Ladder Generation", () => {
  it("calculates accurate Call and Put Greeks", () => {
    const spot = 24500;
    const strike = 24500;
    const tYears = 7 / 365; // 7 days to expiry
    const r = 0.065;
    const sigma = 0.14;

    // ATM Call
    const call = calculateBlackScholesGreeks(spot, strike, tYears, r, sigma, true);
    expect(call.price).toBeGreaterThan(0);
    // ATM Call Delta should be approximately 0.50 - 0.55
    expect(call.greeks.delta).toBeGreaterThanOrEqual(0.48);
    expect(call.greeks.delta).toBeLessThanOrEqual(0.58);
    expect(call.greeks.gamma).toBeGreaterThan(0);
    expect(call.greeks.theta).toBeLessThan(0); // Time decay is negative
    expect(call.greeks.vega).toBeGreaterThan(0);

    // ATM Put
    const put = calculateBlackScholesGreeks(spot, strike, tYears, r, sigma, false);
    expect(put.price).toBeGreaterThan(0);
    // ATM Put Delta should be approximately -0.45 to -0.52
    expect(put.greeks.delta).toBeLessThanOrEqual(-0.42);
    expect(put.greeks.delta).toBeGreaterThanOrEqual(-0.54);
    expect(put.greeks.theta).toBeLessThan(0);
  });

  it("generates symmetrical strike rows around ATM strike", () => {
    const chain = generateOptionChain("NIFTY", 24520, "2026-01-29", 50, 5);

    expect(chain.underlying).toBe("NIFTY");
    expect(chain.atmStrike).toBe(24500);
    expect(chain.rows).toHaveLength(11); // -5 to +5 is 11 rows

    const atmRow = chain.rows.find((r) => r.isAtm);
    expect(atmRow).toBeDefined();
    expect(atmRow?.strike).toBe(24500);
    expect(chain.pcrRatio).toBeGreaterThan(0);
  });
});
