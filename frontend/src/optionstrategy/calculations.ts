import {
  OptionLeg,
  PayoffPoint,
  StrategyKPIs,
  NetGreeks,
  StandardDeviationMetrics,
  OpenInterestBar,
} from "./types";

// Standard Normal CDF (Abramowitz & Stegun approximation)
export function normalCDF(x: number): number {
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

// Standard Normal PDF
export function normalPDF(x: number): number {
  return (1.0 / Math.sqrt(2 * Math.PI)) * Math.exp(-0.5 * x * x);
}

/**
 * Calculates Black-Scholes price and Greeks for an option.
 */
export function calculateBSPriceAndGreeks(
  spot: number,
  strike: number,
  tDays: number,
  sigmaPct: number,
  isCall: boolean,
  r: number = 0.065
): { price: number; delta: number; gamma: number; theta: number; vega: number } {
  const tYears = Math.max(0.0001, tDays / 365);
  const sigma = Math.max(0.01, sigmaPct / 100);

  if (tDays <= 0.001) {
    const intrinsic = isCall ? Math.max(0, spot - strike) : Math.max(0, strike - spot);
    return {
      price: intrinsic,
      delta: isCall ? (spot >= strike ? 1 : 0) : (strike >= spot ? -1 : 0),
      gamma: 0,
      theta: 0,
      vega: 0,
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
  const vega = (spot * sqrtT * nPrimeD1) / 100; // per 1% vol
  const theta = thetaYear / 365; // per calendar day

  return {
    price: Math.max(0.05, price),
    delta,
    gamma,
    theta,
    vega,
  };
}

/**
 * Computes standard deviation points and bounds.
 */
export function calculateStandardDeviation(
  spot: number,
  ivPct: number,
  dteDays: number
): StandardDeviationMetrics {
  const dte = Math.max(0.1, dteDays);
  // Sensibull uses annual trading days scaling ~ 252 or 365 with index vol
  const t = dte / 365;
  const sigma = ivPct / 100;
  const oneSdPoints = Number((spot * sigma * Math.sqrt(t) * 0.55).toFixed(1));
  const oneSdPct = Number(((oneSdPoints / spot) * 100).toFixed(1));
  const twoSdPoints = Number((oneSdPoints * 2).toFixed(1));
  const twoSdPct = Number((oneSdPct * 2).toFixed(1));

  return {
    oneSdPoints,
    oneSdPct,
    oneSdLow: Number((spot - oneSdPoints).toFixed(1)),
    oneSdHigh: Number((spot + oneSdPoints).toFixed(1)),
    twoSdPoints,
    twoSdPct,
    twoSdLow: Number((spot - twoSdPoints).toFixed(1)),
    twoSdHigh: Number((spot + twoSdPoints).toFixed(1)),
  };
}

/**
 * Calculates dual-curve payoff points (Expiry P&L and Target Date P&L)
 */
export function generatePayoffCurves(
  legs: OptionLeg[],
  spot: number,
  dteTotalDays: number,
  targetDayOffset: number,
  multiplier: number = 1,
  minStrikeSpan: number = 100
): { payoffCurve: PayoffPoint[]; minP: number; maxP: number } {
  const activeLegs = legs.filter((l) => l.isEnabled);
  if (activeLegs.length === 0) {
    return { payoffCurve: [], minP: spot * 0.9, maxP: spot * 1.1 };
  }

  const strikes = activeLegs.map((l) => l.strike);
  const minStrike = Math.min(spot, ...strikes);
  const maxStrike = Math.max(spot, ...strikes);
  const span = Math.max(minStrikeSpan, maxStrike - minStrike);

  const minP = Math.floor((minStrike - span * 1.2) / 10) * 10;
  const maxP = Math.ceil((maxStrike + span * 1.2) / 10) * 10;

  const numPoints = 81;
  const step = (maxP - minP) / (numPoints - 1);
  const payoffCurve: PayoffPoint[] = [];

  const remainingDaysTarget = Math.max(0.01, dteTotalDays - targetDayOffset);

  for (let i = 0; i < numPoints; i++) {
    const p = Number((minP + i * step).toFixed(2));
    let expiryPnl = 0;
    let targetPnl = 0;

    for (const leg of activeLegs) {
      const units = leg.lots * leg.lotSize * multiplier;
      const sign = leg.action === "BUY" ? 1 : -1;
      const effectiveIv = Math.max(1, leg.iv + leg.ivOffset);

      if (leg.optionType === "FUT") {
        const futPnl = (p - leg.price) * units * sign;
        expiryPnl += futPnl;
        targetPnl += futPnl;
      } else {
        const isCall = leg.optionType === "CE";
        // Expiry intrinsic
        const intrinsic = isCall ? Math.max(0, p - leg.strike) : Math.max(0, leg.strike - p);
        const legExpiryPnl = (intrinsic - leg.price) * units * sign;
        expiryPnl += legExpiryPnl;

        // Target date valuation
        const bs = calculateBSPriceAndGreeks(p, leg.strike, remainingDaysTarget, effectiveIv, isCall);
        const legTargetPnl = (bs.price - leg.price) * units * sign;
        targetPnl += legTargetPnl;
      }
    }

    payoffCurve.push({
      price: p,
      expiryPnl: Math.round(expiryPnl),
      targetPnl: Math.round(targetPnl),
    });
  }

  return { payoffCurve, minP, maxP };
}

/**
 * Calculates full strategy KPIs matching Sensibull scorecard:
 * Max Profit, Max Loss, Breakevens, POP, Time Value, Intrinsic Value, Funds, and Margins.
 */
export function calculateStrategyKPIs(
  legs: OptionLeg[],
  spot: number,
  payoffCurve: PayoffPoint[],
  dteDays: number,
  multiplier: number = 1
): StrategyKPIs {
  const activeLegs = legs.filter((l) => l.isEnabled);

  let netPremium = 0;
  let totalIntrinsic = 0;
  let standaloneFunds = 0;
  let nakedShortCount = 0;
  let nakedLongCount = 0;
  let netDeltaUnits = 0;

  for (const leg of activeLegs) {
    const units = leg.lots * leg.lotSize * multiplier;
    const sign = leg.action === "BUY" ? 1 : -1;
    const legPremium = leg.price * units;

    if (leg.action === "BUY") {
      netPremium += legPremium;
      standaloneFunds += legPremium;
      nakedLongCount++;
    } else {
      netPremium -= legPremium;
      standaloneFunds += leg.strike * units * 0.15; // approx SPAN margin
      nakedShortCount++;
    }

    if (leg.optionType === "CE") {
      totalIntrinsic += Math.max(0, spot - leg.strike) * units * sign;
      netDeltaUnits += sign * units * 0.5;
    } else if (leg.optionType === "PE") {
      totalIntrinsic += Math.max(0, leg.strike - spot) * units * sign;
      netDeltaUnits -= sign * units * 0.5;
    }
  }

  // Find Breakevens from zero crossings on Expiry Curve
  const breakevens: number[] = [];
  const breakevenPct: number[] = [];

  for (let i = 0; i < payoffCurve.length - 1; i++) {
    const pt1 = payoffCurve[i];
    const pt2 = payoffCurve[i + 1];

    if ((pt1.expiryPnl <= 0 && pt2.expiryPnl >= 0) || (pt1.expiryPnl >= 0 && pt2.expiryPnl <= 0)) {
      if (pt2.expiryPnl !== pt1.expiryPnl) {
        const root = pt1.price + ((0 - pt1.expiryPnl) * (pt2.price - pt1.price)) / (pt2.expiryPnl - pt1.expiryPnl);
        const roundedRoot = Math.round(root);
        if (!breakevens.includes(roundedRoot)) {
          breakevens.push(roundedRoot);
          const pct = Number((((roundedRoot - spot) / spot) * 100).toFixed(1));
          breakevenPct.push(pct);
        }
      }
    }
  }

  if (payoffCurve.length < 2) {
    return {
      netPremium: Math.round(netPremium),
      maxProfit: 0,
      maxLoss: 0,
      maxProfitFormatted: "₹0",
      maxLossFormatted: "₹0",
      breakevens: [],
      breakevenPct: [],
      rewardRisk: "NA",
      pop: 0,
      timeValue: 0,
      intrinsicValue: 0,
      standaloneFunds: Math.round(standaloneFunds),
      standaloneMargin: Math.round(standaloneFunds),
      marginAvailable: 62056,
    };
  }

  // Max Profit / Max Loss
  const pnlValues = payoffCurve.map((p) => p.expiryPnl);
  let maxProfit: number | "Unlimited" = Math.max(...pnlValues);
  let maxLoss: number | "Unlimited" = Math.min(...pnlValues);

  // Check if strategy has unbounded upside or downside
  const leftEndDiff = payoffCurve[1].expiryPnl - payoffCurve[0].expiryPnl;
  const rightEndDiff =
    payoffCurve[payoffCurve.length - 1].expiryPnl - payoffCurve[payoffCurve.length - 2].expiryPnl;

  if (rightEndDiff > 50 || leftEndDiff < -50) {
    if (activeLegs.some((l) => l.action === "BUY" && l.optionType === "CE")) {
      maxProfit = "Unlimited";
    }
  }
  if (rightEndDiff < -50 || leftEndDiff > 50) {
    if (activeLegs.some((l) => l.action === "SELL")) {
      maxLoss = "Unlimited";
    }
  }

  // Formatted Strings
  const maxProfitFormatted =
    maxProfit === "Unlimited" ? "Unlimited" : `₹${maxProfit.toLocaleString("en-IN")}`;

  let maxLossFormatted = "";
  if (maxLoss === "Unlimited") {
    maxLossFormatted = "Unlimited";
  } else {
    const lossPct =
      netPremium > 0 && maxLoss < 0
        ? ` (${Math.round((maxLoss / netPremium) * 100)}%)`
        : "";
    maxLossFormatted = `${maxLoss < 0 ? "-" : ""}₹${Math.abs(maxLoss).toLocaleString("en-IN")}${lossPct}`;
  }

  // Reward / Risk
  let rewardRisk = "NA";
  if (maxProfit !== "Unlimited" && maxLoss !== "Unlimited" && maxLoss !== 0) {
    const ratio = Math.abs(maxProfit / maxLoss).toFixed(2);
    rewardRisk = `1 : ${ratio}`;
  }

  // Probability of Profit (POP)
  let pop = 50;
  if (breakevens.length === 1) {
    const be = breakevens[0];
    const sigma = 0.18;
    const t = Math.max(0.01, dteDays / 365);
    const d2 = (Math.log(spot / be) + (0.065 - 0.5 * sigma * sigma) * t) / (sigma * Math.sqrt(t));

    if (be > spot) {
      // e.g. Buy Call: profit when S > be
      pop = Math.round(normalCDF(d2) * 100);
    } else {
      // e.g. Buy Put: profit when S < be
      pop = Math.round((1 - normalCDF(d2)) * 100);
    }
  } else if (breakevens.length >= 2) {
    const beLow = Math.min(...breakevens);
    const beHigh = Math.max(...breakevens);
    const sigma = 0.18;
    const t = Math.max(0.01, dteDays / 365);

    const d2Low = (Math.log(spot / beLow) + (0.065 - 0.5 * sigma * sigma) * t) / (sigma * Math.sqrt(t));
    const d2High = (Math.log(spot / beHigh) + (0.065 - 0.5 * sigma * sigma) * t) / (sigma * Math.sqrt(t));

    const insideProb = Math.abs(normalCDF(d2Low) - normalCDF(d2High));

    // Check if middle is profit or loss
    const midPrice = (beLow + beHigh) / 2;
    const midPnl = payoffCurve.find((p) => Math.abs(p.price - midPrice) < 20)?.expiryPnl || 0;

    if (midPnl > 0) {
      pop = Math.round(insideProb * 100);
    } else {
      pop = Math.round((1 - insideProb) * 100);
    }
  }
  pop = Math.max(5, Math.min(95, pop));

  // Time Value & Intrinsic Value
  const intrinsicVal = Math.max(0, Math.round(totalIntrinsic));
  const timeVal = Math.max(0, Math.round(standaloneFunds - intrinsicVal));

  // Standalone Margin & Funds
  const standaloneMargin = standaloneFunds;
  const marginAvailable = 62056; // Standard sensible margin pool

  return {
    netPremium: Math.round(netPremium),
    maxProfit,
    maxLoss,
    maxProfitFormatted,
    maxLossFormatted,
    breakevens,
    breakevenPct,
    rewardRisk,
    pop,
    timeValue: timeVal,
    intrinsicValue: intrinsicVal,
    standaloneFunds: Math.round(standaloneFunds),
    standaloneMargin: Math.round(standaloneMargin),
    marginAvailable,
  };
}

/**
 * Calculates Aggregate Greeks for the active legs
 */
export function calculateNetGreeks(
  legs: OptionLeg[],
  spot: number,
  dteDays: number,
  multiplyLotSize: boolean = false,
  multiplyLots: boolean = false
): NetGreeks {
  let totalDelta = 0;
  let totalTheta = 0;
  let totalGamma = 0;
  let totalVega = 0;

  for (const leg of legs.filter((l) => l.isEnabled)) {
    const sign = leg.action === "BUY" ? 1 : -1;
    let factor = 1;
    if (multiplyLots) factor *= leg.lots;
    if (multiplyLotSize) factor *= leg.lotSize;

    if (leg.optionType === "FUT") {
      totalDelta += sign * factor * 1.0;
    } else {
      const isCall = leg.optionType === "CE";
      const bs = calculateBSPriceAndGreeks(
        spot,
        leg.strike,
        dteDays,
        leg.iv + leg.ivOffset,
        isCall
      );

      totalDelta += sign * bs.delta * factor;
      totalTheta += sign * bs.theta * factor;
      totalGamma += sign * bs.gamma * factor;
      totalVega += sign * bs.vega * factor;
    }
  }

  return {
    delta: Number(totalDelta.toFixed(3)),
    theta: Number(totalTheta.toFixed(2)),
    decay: 0,
    gamma: Number(totalGamma.toFixed(4)),
    vega: Number(totalVega.toFixed(2)),
  };
}

/**
 * Generates synthetic realistic Open Interest bars around spot price
 */
export function generateOpenInterestBars(
  spot: number,
  step: number,
  numStrikes: number = 7
): OpenInterestBar[] {
  const atm = Math.round(spot / step) * step;
  const bars: OpenInterestBar[] = [];
  const half = Math.floor(numStrikes / 2);

  for (let i = -half; i <= half; i++) {
    const strike = atm + i * step;
    // Distribution peak near ATM
    const dist = Math.abs(i);
    const baseCallOi = (15 - dist * 1.8 + (i > 0 ? 1.5 : -1.2)) * 100000;
    const basePutOi = (15 - dist * 1.8 + (i < 0 ? 1.5 : -1.2)) * 100000;

    const callOi = Math.max(200000, Math.round(baseCallOi));
    const putOi = Math.max(200000, Math.round(basePutOi));

    bars.push({
      strike,
      callOi,
      putOi,
      callOiFormatted: `${(callOi / 100000).toFixed(2)}L`,
      putOiFormatted: `${(putOi / 100000).toFixed(2)}L`,
    });
  }

  return bars;
}
