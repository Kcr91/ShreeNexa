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

export function calculateBlack76Greeks(
  forward: number,
  strike: number,
  tYears: number,
  r: number = 0.07,
  sigma: number = 0.15,
  isCall: boolean = true
): { price: number; greeks: Greeks; isReliable: boolean; reason?: string } {
  if (tYears <= 0.0001) {
    const intrinsic = isCall ? Math.max(0, forward - strike) : Math.max(0, strike - forward);
    return {
      price: Number(intrinsic.toFixed(2)),
      greeks: {
        delta: isCall ? (forward >= strike ? 1 : 0) : (strike >= forward ? -1 : 0),
        gamma: 0,
        theta: 0,
        vega: 0,
        rho: 0,
      },
      isReliable: false,
      reason: "Contract has expired (T <= 0)",
    };
  }

  const safeSigma = Math.max(0.0001, sigma);
  const sqrtT = Math.sqrt(tYears);
  const dfR = Math.exp(-r * tYears);

  const d1 = (Math.log(forward / strike) + 0.5 * safeSigma * safeSigma * tYears) / (safeSigma * sqrtT);
  const d2 = d1 - safeSigma * sqrtT;

  const pdfD1 = normalPDF(d1);
  const nd1 = normalCDF(d1);
  const nd2 = normalCDF(d2);

  let price = 0;
  let delta = 0;
  let thetaYear = 0;
  let rho = 0;

  if (isCall) {
    price = dfR * (forward * nd1 - strike * nd2);
    delta = dfR * nd1;
    thetaYear = -(forward * dfR * pdfD1 * safeSigma) / (2 * sqrtT) - (r * dfR * strike * nd2) + (r * dfR * forward * nd1);
    rho = -tYears * dfR * (forward * nd1 - strike * nd2) * 0.01;
  } else {
    const nNegD1 = normalCDF(-d1);
    const nNegD2 = normalCDF(-d2);
    price = dfR * (strike * nNegD2 - forward * nNegD1);
    delta = -dfR * nNegD1;
    thetaYear = -(forward * dfR * pdfD1 * safeSigma) / (2 * sqrtT) + (r * dfR * strike * nNegD2) - (r * dfR * forward * nNegD1);
    rho = -tYears * dfR * (strike * nNegD2 - forward * nNegD1) * 0.01;
  }

  const gamma = (dfR * pdfD1) / (forward * safeSigma * sqrtT);
  const vega = (forward * dfR * sqrtT * pdfD1) * 0.01; // per 1% vol change
  const theta = thetaYear / 365; // per calendar day

  return {
    price: Number(Math.max(0, price).toFixed(2)),
    greeks: {
      delta: Number(delta.toFixed(4)),
      gamma: Number(gamma.toFixed(6)),
      theta: Number(theta.toFixed(2)),
      vega: Number(vega.toFixed(2)),
      rho: Number(rho.toFixed(2)),
    },
    isReliable: true,
  };
}

export function solveImpliedVolatilityBlack76(
  marketPrice: number,
  forward: number,
  strike: number,
  tYears: number,
  r: number = 0.07,
  isCall: boolean = true
): { iv: number; isReliable: boolean; reason?: string } {
  if (marketPrice <= 0 || tYears <= 0 || forward <= 0 || strike <= 0) {
    return { iv: 0, isReliable: false, reason: "Non-positive inputs or expired contract" };
  }

  const dfR = Math.exp(-r * tYears);
  const intrinsic = isCall ? dfR * Math.max(0, forward - strike) : dfR * Math.max(0, strike - forward);

  if (marketPrice < intrinsic - 1e-4) {
    return { iv: 0, isReliable: false, reason: "Market price below discounted intrinsic value" };
  }

  const sqrtT = Math.sqrt(tYears);
  const d1Ref = (Math.log(forward / strike) + 0.5 * 0.20 * 0.20 * tYears) / (0.20 * sqrtT);
  const refVega = forward * dfR * sqrtT * normalPDF(d1Ref) * 0.01;

  if (refVega < 1e-5) {
    return { iv: 0, isReliable: false, reason: "Vega near zero: IV numerically unreliable" };
  }

  let low = 0.001;
  let high = 5.0;

  for (let iter = 0; iter < 50; iter++) {
    const mid = 0.5 * (low + high);
    const res = calculateBlack76Greeks(forward, strike, tYears, r, mid, isCall);
    const diff = res.price - marketPrice;

    if (Math.abs(diff) < 0.01 || (high - low) < 1e-5) {
      return { iv: Number(mid.toFixed(4)), isReliable: true };
    }

    if (diff > 0) {
      high = mid;
    } else {
      low = mid;
    }
  }

  const finalMid = 0.5 * (low + high);
  return { iv: Number(finalMid.toFixed(4)), isReliable: true };
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
  const r = 0.07;
  // Forward price via Cost-of-Carry
  const forward = spotPrice * Math.exp(r * tYears);

  const rows: OptionStrikeRow[] = [];
  let totalCallOi = 0;
  let totalPutOi = 0;

  for (let i = -strikesCount; i <= strikesCount; i++) {
    const strike = atmStrike + i * strikeStep;
    const isAtm = strike === atmStrike;

    // Call contract
    const callRes = calculateBlack76Greeks(forward, strike, tYears, r, iv, true);
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
    const putRes = calculateBlack76Greeks(forward, strike, tYears, r, iv, false);
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
