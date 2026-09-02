import { DepthLevel, DepthLevelType, MarketDepthBook } from "./types";

export const FULL_DEPTH_SUPPORTED_SEGMENTS = new Set(["NSE_EQ", "NSE_FNO"]);

export function calculateCumulativeDepth(
  rawLevels: { price: number; quantity: number; orders: number }[]
): DepthLevel[] {
  let cum = 0;
  return rawLevels.map((lvl) => {
    cum += lvl.quantity;
    return {
      price: lvl.price,
      quantity: lvl.quantity,
      orders: lvl.orders,
      cumulativeQty: cum,
    };
  });
}

export function resolveSegmentDepthCapability(
  segment: string,
  requestedLevel: DepthLevelType
): {
  actualLevel: DepthLevelType;
  isFallback: boolean;
  fallbackReason?: string;
  connectionCost: string;
} {
  let actualLevel = requestedLevel;
  let isFallback = false;
  let fallbackReason: string | undefined;

  if (
    !FULL_DEPTH_SUPPORTED_SEGMENTS.has(segment) &&
    (requestedLevel === "LEVEL_20" || requestedLevel === "LEVEL_200")
  ) {
    actualLevel = "LEVEL_5";
    isFallback = true;
    fallbackReason = `Exchange limitation: Full Market Depth (${requestedLevel}) is supported only on NSE_EQ and NSE_FNO. 5-level regular feed active for ${segment}.`;
  }

  let connectionCost: string;
  if (actualLevel === "LEVEL_200") {
    connectionCost = "Dedicated Socket (1 instrument / connection)";
  } else if (actualLevel === "LEVEL_20") {
    connectionCost = "Shared Socket Pool (Up to 50 instruments / connection)";
  } else {
    connectionCost = "Regular Feed (No dedicated depth socket consumed)";
  }

  return { actualLevel, isFallback, fallbackReason, connectionCost };
}

export function computeOrderBookImbalance(
  bids: DepthLevel[],
  asks: DepthLevel[]
): number {
  const totalBids = bids.reduce((acc, b) => acc + b.quantity, 0);
  const totalAsks = asks.reduce((acc, a) => acc + a.quantity, 0);
  const total = totalBids + totalAsks;
  if (total === 0) return 0;
  return Number(((totalBids - totalAsks) / total).toFixed(4));
}

export function generateMockDepthBook(
  symbol: string,
  segment: string = "NSE_EQ",
  requestedLevel: DepthLevelType = "LEVEL_20",
  basePrice: number = 1000.0,
  securityId: number = 1333
): MarketDepthBook {
  const capability = resolveSegmentDepthCapability(segment, requestedLevel);
  const targetCount =
    capability.actualLevel === "LEVEL_5"
      ? 5
      : capability.actualLevel === "LEVEL_20"
      ? 20
      : 200;

  const symSeed = symbol.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const tickSize = 0.05;

  const rawBids: { price: number; quantity: number; orders: number }[] = [];
  const rawAsks: { price: number; quantity: number; orders: number }[] = [];

  for (let i = 0; i < targetCount; i++) {
    const bidPrice = Number((basePrice - (i + 1) * tickSize).toFixed(2));
    const bidQty = 50 + ((symSeed * (i + 1) * 37) % 500);
    const bidOrders = 1 + ((symSeed * (i + 1)) % 15);
    rawBids.push({ price: bidPrice, quantity: bidQty, orders: bidOrders });

    const askPrice = Number((basePrice + (i + 1) * tickSize).toFixed(2));
    const askQty = 40 + ((symSeed * (i + 1) * 43) % 480);
    const askOrders = 1 + ((symSeed * (i + 1) * 3) % 12);
    rawAsks.push({ price: askPrice, quantity: askQty, orders: askOrders });
  }

  const bids = calculateCumulativeDepth(rawBids);
  const asks = calculateCumulativeDepth(rawAsks);

  const totalBidQty = bids[bids.length - 1]?.cumulativeQty ?? 0;
  const totalAskQty = asks[asks.length - 1]?.cumulativeQty ?? 0;

  const bestBid = bids[0]?.price ?? basePrice;
  const bestAsk = asks[0]?.price ?? basePrice;
  const spread = Number(Math.max(0, bestAsk - bestBid).toFixed(2));
  const spreadPct = Number(((spread / Math.max(bestBid, 0.01)) * 100).toFixed(4));
  const imbalance = computeOrderBookImbalance(bids, asks);

  return {
    securityId,
    symbol,
    segment,
    depthLevelType: capability.actualLevel,
    isFallback: capability.isFallback,
    fallbackReason: capability.fallbackReason,
    connectionCost: capability.connectionCost,
    bids,
    asks,
    totalBidQty,
    totalAskQty,
    spread,
    spreadPct,
    imbalanceRatio: imbalance,
  };
}
