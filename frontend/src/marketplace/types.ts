import { StrategyIRSchema } from "../strategybuilder/types";

export type StrategyCategory =
  | "ALL"
  | "MOMENTUM"
  | "OPTIONS_INCOME"
  | "BREAKOUT"
  | "VOLATILITY"
  | "TREND_FOLLOWING";

export interface StrategyAuthor {
  name: string;
  handle: string;
  verified: boolean;
  avatar: string;
}

export interface StrategyPerformance {
  cagrPct: number;
  sharpeRatio: number;
  maxDrawdownPct: number;
  winRatePct: number;
  totalTrades: number;
  profitFactor: number;
}

export interface MarketplaceStrategy {
  id: string;
  title: string;
  description: string;
  author: StrategyAuthor;
  category: StrategyCategory;
  tags: string[];
  assetClass: "EQUITY" | "OPTIONS" | "FUTURES";
  timeframe: string;
  performance: StrategyPerformance;
  strategyIR: StrategyIRSchema;
  clonesCount: number;
  likesCount: number;
}

export interface MarketplaceWidgetSettings {
  defaultCategory: string;
  defaultAssetClass: string;
}
