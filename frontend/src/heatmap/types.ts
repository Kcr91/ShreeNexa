export type WeightingSource =
  | "OFFICIAL_NSE"
  | "FREE_FLOAT_MCAP"
  // Membership derived from the parent index by published methodology screens,
  // used for indices where NSE publishes no constituent CSV (Shariah, ESG, EV).
  | "DERIVED_SCREEN"
  | "FALLBACK_EQUAL_WEIGHT";

export type IndexCategory =
  | "BROAD_MARKET"
  | "SECTORAL"
  | "THEMATIC"
  | "STRATEGY";

export type NseColorBracket = "5" | "3" | "1" | "0" | "-1" | "-3" | "-5";

export interface MarketBreadth {
  totalCount: number;
  advances: number;
  declines: number;
  unchanged: number;
  advanceDeclineRatio: number;
  pctAbovePrevClose: number;
  weightedBreadth: number;
  sentimentPosture:
    | "Strong Bullish"
    | "Moderate Bullish"
    | "Neutral"
    | "Moderate Bearish"
    | "Strong Bearish"
    | "Unavailable";
}

export interface IndexHeatmapItem {
  indexName: string;
  category?: IndexCategory;
  sector: string;
  weight: number;
  changePct?: number;
  ltp?: number;
  advances?: number;
  declines?: number;
  unchanged?: number;
  futuresBasis?: number;
  oiChangePct?: number;
  constituentCount?: number;
  weightingSource: WeightingSource;
  securityId?: string;
  segment?: string;
  marketState?: "LIVE" | "MARKET_CLOSED" | "STALE" | "UNAVAILABLE" | "ERROR";
  source?: "DHAN_WEBSOCKET" | "DHAN_REST";
  receivedAt?: number;
  error?: string;
}

export interface ConstituentHeatmapItem {
  symbol: string;
  name?: string;
  sector: string;
  weight: number;
  isWeightFallback: boolean;
  weightingSource: WeightingSource;
  changePct?: number;
  changeAbs?: number;
  ltp?: number;
  prevClose?: number;
  volume?: number;
  securityId?: string;
  segment?: string;
  marketState?: "LIVE" | "MARKET_CLOSED" | "STALE" | "UNAVAILABLE" | "ERROR";
  source?: "DHAN_WEBSOCKET" | "DHAN_REST";
  receivedAt?: number;
  error?: string;
}

export interface ConstituentHeatmapResponse {
  indexName: string;
  category?: IndexCategory;
  breadth: MarketBreadth;
  cellTotalWeight: number;
  constituents: ConstituentHeatmapItem[];
  marketState?: "LIVE" | "MARKET_CLOSED" | "STALE" | "UNAVAILABLE" | "ERROR";
  error?: string;
}
