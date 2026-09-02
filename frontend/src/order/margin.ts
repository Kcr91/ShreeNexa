import { StockOrder, OptionLeg, MarginRequirement } from "./types";

export function calculateStockMargin(
  order: StockOrder,
  availableFunds: number = 500000
): MarginRequirement {
  const tradeValue = order.quantity * order.price;
  const isIntraday = order.productType === "MIS";
  const marginRatio = isIntraday ? 0.20 : 1.0; // 20% for MIS, 100% for CNC

  const totalRequiredMargin = Number((tradeValue * marginRatio).toFixed(2));

  // Indian regulatory cost estimates
  const stt = order.side === "BUY" && !isIntraday ? tradeValue * 0.001 : isIntraday && order.side === "SELL" ? tradeValue * 0.00025 : 0;
  const brokerage = Math.min(20, tradeValue * 0.0003);
  const exchangeTurnover = tradeValue * 0.0000325;
  const stampDuty = order.side === "BUY" ? tradeValue * 0.00015 : 0;
  const gst = (brokerage + exchangeTurnover) * 0.18;
  const estimatedCosts = Number((stt + brokerage + exchangeTurnover + stampDuty + gst).toFixed(2));

  return {
    initialMargin: totalRequiredMargin,
    exposureMargin: 0,
    premiumPayable: 0,
    premiumReceivable: 0,
    hedgingBenefit: 0,
    totalRequiredMargin,
    estimatedCosts,
    availableFunds,
    isSufficient: availableFunds >= totalRequiredMargin + estimatedCosts,
  };
}

export function calculateMultiLegOptionMargin(
  legs: OptionLeg[],
  availableFunds: number = 500000
): MarginRequirement {
  if (legs.length === 0) {
    return {
      initialMargin: 0,
      exposureMargin: 0,
      premiumPayable: 0,
      premiumReceivable: 0,
      hedgingBenefit: 0,
      totalRequiredMargin: 0,
      estimatedCosts: 0,
      availableFunds,
      isSufficient: true,
    };
  }

  let premiumPayable = 0;
  let premiumReceivable = 0;
  let grossShortMargin = 0;

  const buyCalls: OptionLeg[] = [];
  const sellCalls: OptionLeg[] = [];
  const buyPuts: OptionLeg[] = [];
  const sellPuts: OptionLeg[] = [];

  for (const leg of legs) {
    const legPremiumValue = leg.premium * leg.quantity;
    if (leg.side === "BUY") {
      premiumPayable += legPremiumValue;
      if (leg.optionType === "CE") buyCalls.push(leg);
      else buyPuts.push(leg);
    } else {
      premiumReceivable += legPremiumValue;
      // Naked short SPAN + Exposure estimate: ~15% of notional
      const notional = leg.strike * leg.quantity;
      grossShortMargin += notional * 0.15;
      if (leg.optionType === "CE") sellCalls.push(leg);
      else sellPuts.push(leg);
    }
  }

  // Calculate Hedging Benefit
  let hedgingBenefit = 0;

  // CE spread hedge benefit
  if (sellCalls.length > 0 && buyCalls.length > 0) {
    const hedgedQty = Math.min(
      sellCalls.reduce((s, c) => s + c.quantity, 0),
      buyCalls.reduce((s, c) => s + c.quantity, 0)
    );
    // Benefit up to 70% of gross naked margin on hedged contracts
    hedgingBenefit += (grossShortMargin * 0.65) * (hedgedQty / (sellCalls[0].quantity || 1));
  }

  // PE spread hedge benefit
  if (sellPuts.length > 0 && buyPuts.length > 0) {
    const hedgedQty = Math.min(
      sellPuts.reduce((s, p) => s + p.quantity, 0),
      buyPuts.reduce((s, p) => s + p.quantity, 0)
    );
    hedgingBenefit += (grossShortMargin * 0.65) * (hedgedQty / (sellPuts[0].quantity || 1));
  }

  // Ensure hedging benefit does not exceed 85% of gross short margin
  hedgingBenefit = Math.min(grossShortMargin * 0.85, hedgingBenefit);

  const netSpanExposure = Math.max(0, grossShortMargin - hedgingBenefit);
  const totalRequiredMargin = Number(
    Math.max(premiumPayable, netSpanExposure + premiumPayable - premiumReceivable * 0.5).toFixed(2)
  );

  // Regulatory cost estimate for options: ₹20/order + STT on sell + GST
  const estimatedCosts = Number((legs.length * 20 + premiumReceivable * 0.00125 * 1.18).toFixed(2));

  return {
    initialMargin: Number((netSpanExposure * 0.8).toFixed(2)),
    exposureMargin: Number((netSpanExposure * 0.2).toFixed(2)),
    premiumPayable: Number(premiumPayable.toFixed(2)),
    premiumReceivable: Number(premiumReceivable.toFixed(2)),
    hedgingBenefit: Number(hedgingBenefit.toFixed(2)),
    totalRequiredMargin,
    estimatedCosts,
    availableFunds,
    isSufficient: availableFunds >= totalRequiredMargin + estimatedCosts,
  };
}
