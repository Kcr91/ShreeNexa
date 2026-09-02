export type DepthLevelType = "LEVEL_5" | "LEVEL_20" | "LEVEL_200";

export interface DepthLevel {
  price: number;
  quantity: number;
  orders: number;
  cumulativeQty: number;
}

export interface MarketDepthBook {
  securityId: number;
  symbol: string;
  segment: string;
  depthLevelType: DepthLevelType;
  isFallback: boolean;
  fallbackReason?: string;
  connectionCost: string;
  bids: DepthLevel[];
  asks: DepthLevel[];
  totalBidQty: number;
  totalAskQty: number;
  spread: number;
  spreadPct: number;
  imbalanceRatio: number;
}

export interface DepthWatchlistItem {
  symbol: string;
  segment: string;
  bestBid: number;
  bestAsk: number;
  spread: number;
  top5Imbalance: number;
  totalBidQty: number;
  totalAskQty: number;
  depthLevelType: DepthLevelType;
  isFallback: boolean;
}
