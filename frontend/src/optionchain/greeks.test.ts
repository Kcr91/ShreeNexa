import { describe, expect, it } from "vitest";
import {
  calculateBlackScholesGreeks,
  calculateBlack76Greeks,
  solveImpliedVolatilityBlack76,
  generateOptionChain,
} from "./greeks";

describe("Option Chain Black-Scholes and Black-76 Greeks and Ladder Generation", () => {
  it("calculates accurate Call and Put Greeks with Black-Scholes", () => {
    const spot = 24500;
    const strike = 24500;
    const tYears = 7 / 365; // 7 days to expiry
    const r = 0.065;
    const sigma = 0.14;

    // ATM Call
    const call = calculateBlackScholesGreeks(spot, strike, tYears, r, sigma, true);
    expect(call.price).toBeGreaterThan(0);
    expect(call.greeks.delta).toBeGreaterThanOrEqual(0.48);
    expect(call.greeks.delta).toBeLessThanOrEqual(0.58);
    expect(call.greeks.gamma).toBeGreaterThan(0);
    expect(call.greeks.theta).toBeLessThan(0);
    expect(call.greeks.vega).toBeGreaterThan(0);

    // ATM Put
    const put = calculateBlackScholesGreeks(spot, strike, tYears, r, sigma, false);
    expect(put.price).toBeGreaterThan(0);
    expect(put.greeks.delta).toBeLessThanOrEqual(-0.42);
    expect(put.greeks.delta).toBeGreaterThanOrEqual(-0.54);
    expect(put.greeks.theta).toBeLessThan(0);
  });

  it("calculates Black-76 pricing with exact Put-Call parity and Greek bounds", () => {
    const forward = 25000;
    const strike = 25000;
    const tYears = 30 / 365;
    const r = 0.07;
    const sigma = 0.15;

    const call = calculateBlack76Greeks(forward, strike, tYears, r, sigma, true);
    const put = calculateBlack76Greeks(forward, strike, tYears, r, sigma, false);

    expect(call.isReliable).toBe(true);
    expect(put.isReliable).toBe(true);
    expect(call.price).toBeCloseTo(426.41, 0);
    expect(put.price).toBeCloseTo(call.price, 1);

    // Greek bounds
    expect(call.greeks.delta).toBeGreaterThan(0);
    expect(call.greeks.delta).toBeLessThan(1);
    expect(put.greeks.delta).toBeLessThan(0);
    expect(put.greeks.delta).toBeGreaterThan(-1);
    expect(call.greeks.gamma).toBeGreaterThan(0);
    expect(call.greeks.vega).toBeGreaterThan(0);
  });

  it("inverts implied volatility using Brent's method and handles edge cases", () => {
    const forward = 25200;
    const strike = 25000;
    const tYears = 25 / 365;
    const r = 0.07;
    const trueVol = 0.185;

    const ref = calculateBlack76Greeks(forward, strike, tYears, r, trueVol, true);
    const solved = solveImpliedVolatilityBlack76(ref.price, forward, strike, tYears, r, true);

    expect(solved.isReliable).toBe(true);
    expect(solved.iv).toBeCloseTo(trueVol, 2);

    // Deep OTM near zero vega guard
    const unreliable = solveImpliedVolatilityBlack76(0.05, 25000, 50000, 1 / 365, 0.07, true);
    expect(unreliable.isReliable).toBe(false);
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
