import { Greeks, OptionChainData, OptionStrikeRow, OptionContract } from "./types";

// Standard Normal Cumulative Distribution Function approximation (Abramowitz & Stegun)
function normalCDF(x: number): number {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  const absX = Math.abs(x) / Math.SQRT2;

  const t = 1.0 / (1.0 + p * absX);
  const y = 1.0 - (((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t) * Math.exp(-absX * absX);

  return 0.5 * (1.0 + sign * y);
}

// Standard Normal Probability Density Function
function normalPDF(x: number): number {
  return (1.0 / Math.sqrt(2 * Math.PI)) * Math.exp(-0.5 * x * x);
}

export function calculateBlackScholesGreeks(
  spot: number,
  strike: number,
  tYears: number,
  r: number = 0.065, // 6.5% Indian risk-free rate
  sigma: number = 0.14, // 14% Implied Volatility
  isCall: boolean = true
): { price: number; greeks: Greeks } {
  if (tYears <= 0.0001) {
    const intrinsic = isCall ? Math.max(0, spot - strike) : Math.max(0, strike - spot);
    return {
      price: intrinsic,
      greeks: {
        delta: isCall ? (spot >= strike ? 1 : 0) : (strike >= spot ? -1 : 0),
        gamma: 0,
        theta: 0,
        vega: 0,
      },
    };
  }

  const sqrtT = Math.sqrt(tYears);
  const d1 = (Math.log(spot / strike) + (r + 0.5 * sigma * sigma) * tYears) / (sigma * sqrtT);
  const d2 = d1 - sigma * sqrtT;

  const nd1 = normalCDF(d1);
  const nd2 = normalCDF(d2);
  const nPrimeD1 = normalPDF(d1);

  const discountFactor = Math.exp(-r * tYears);

  let price = 0;
  let delta = 0;
  let thetaYear = 0;

  if (isCall) {
    price = spot * nd1 - strike * discountFactor * nd2;
    delta = nd1;
    thetaYear = -(spot * nPrimeD1 * sigma) / (2 * sqrtT) - r * strike * discountFactor * nd2;
  } else {
    const nMinusD1 = normalCDF(-d1);
    const nMinusD2 = normalCDF(-d2);
    price = strike * discountFactor * nMinusD2 - spot * nMinusD1;
    delta = nd1 - 1.0;
    thetaYear = -(spot * nPrimeD1 * sigma) / (2 * sqrtT) + r * strike * discountFactor * nMinusD2;
  }

  const gamma = nPrimeD1 / (spot * sigma * sqrtT);
  const vega = (spot * sqrtT * nPrimeD1) / 100; // per 1% change in vol
  const theta = thetaYear / 365; // per calendar day

  return {
    price: Number(Math.max(0.05, price).toFixed(2)),
    greeks: {
      delta: Number(delta.toFixed(3)),
      gamma: Number(gamma.toFixed(5)),
      theta: Number(theta.toFixed(2)),
      vega: Number(vega.toFixed(2)),
    },
  };
}

export function generateOptionChain(
  underlying: string = "NIFTY",
  spotPrice: number = 24520,
  expiry: string = "2026-01-29",
  strikeStep: number = 50,
  strikesCount: number = 10
): OptionChainData {
  const atmStrike = Math.round(spotPrice / strikeStep) * strikeStep;
  const tYears = 7 / 365; // 7 DTE weekly
  const iv = 0.135; // 13.5% IV

  const rows: OptionStrikeRow[] = [];
  let totalCallOi = 0;
  let totalPutOi = 0;

  for (let i = -strikesCount; i <= strikesCount; i++) {
    const strike = atmStrike + i * strikeStep;
    const isAtm = strike === atmStrike;

    // Call contract
    const callRes = calculateBlackScholesGreeks(spotPrice, strike, tYears, 0.065, iv, true);
    const callOi = Math.floor(100000 + Math.max(0, 500000 - Math.abs(strike - spotPrice) * 300));
    totalCallOi += callOi;

    const call: OptionContract = {
      symbol: `${underlying} ${strike} CE`,
      strike,
      optionType: "CE",
      expiry,
      ltp: callRes.price,
      bid: Number((callRes.price - 0.25).toFixed(2)),
      ask: Number((callRes.price + 0.25).toFixed(2)),
      iv: Number((iv * 100).toFixed(1)),
      oi: callOi,
      oiChange: Math.floor(callOi * 0.08),
      volume: Math.floor(callOi * 1.5),
      greeks: callRes.greeks,
    };

    // Put contract
    const putRes = calculateBlackScholesGreeks(spotPrice, strike, tYears, 0.065, iv, false);
    const putOi = Math.floor(95000 + Math.max(0, 480000 - Math.abs(strike - spotPrice) * 300));
    totalPutOi += putOi;

    const put: OptionContract = {
      symbol: `${underlying} ${strike} PE`,
      strike,
      optionType: "PE",
      expiry,
      ltp: putRes.price,
      bid: Number((putRes.price - 0.25).toFixed(2)),
      ask: Number((putRes.price + 0.25).toFixed(2)),
      iv: Number((iv * 100).toFixed(1)),
      oi: putOi,
      oiChange: Math.floor(putOi * 0.06),
      volume: Math.floor(putOi * 1.4),
      greeks: putRes.greeks,
    };

    rows.push({
      strike,
      isAtm,
      call,
      put,
    });
  }

  const pcrRatio = totalCallOi > 0 ? Number((totalPutOi / totalCallOi).toFixed(2)) : 1.0;

  return {
    underlying,
    underlyingPrice: spotPrice,
    atmStrike,
    selectedExpiry: expiry,
    expiries: ["2026-01-29", "2026-02-05", "2026-02-26"],
    rows,
    pcrRatio,
    maxPainStrike: atmStrike,
  };
}
