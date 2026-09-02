export type WeightingSource =
  | "OFFICIAL_NSE"
  | "FREE_FLOAT_MCAP"
  | "FALLBACK_EQUAL_WEIGHT";

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
    | "Strong Bearish";
}

export interface IndexHeatmapItem {
  indexName: string;
  sector: string;
  weight: number;
  changePct: number;
  ltp: number;
  advances: number;
  declines: number;
  unchanged: number;
  futuresBasis: number;
  oiChangePct: number;
  weightingSource: WeightingSource;
}

export interface ConstituentHeatmapItem {
  symbol: string;
  sector: string;
  weight: number;
  isWeightFallback: boolean;
  weightingSource: WeightingSource;
  changePct: number;
  ltp: number;
  volume: number;
}

export interface ConstituentHeatmapResponse {
  indexName: string;
  breadth: MarketBreadth;
  cellTotalWeight: number;
  constituents: ConstituentHeatmapItem[];
}
