export type OptionAction = "BUY" | "SELL";
export type OptionContractType = "CE" | "PE" | "FUT";
export type StrategySentiment = "Bullish" | "Bearish" | "Neutral" | "Others";

export interface OptionLeg {
  legId: string;
  symbol: string;
  strike: number;
  optionType: OptionContractType;
  action: OptionAction;
  lots: number;
  lotSize: number;
  price: number;
  iv: number;
  ivOffset: number; // Strikewise IV offset e.g. +0.6%
  expiryDate: string;
  isEnabled: boolean;
}

export interface StrategyTemplate {
  id: string;
  name: string;
  sentiment: StrategySentiment;
  description: string;
  pathD: string; // Mini SVG path for payoff icon
  builder: (spot: number, step: number, lotSize: number, expiry: string) => OptionLeg[];
}

export interface PayoffPoint {
  price: number;
  expiryPnl: number;
  targetPnl: number;
}

export interface OpenInterestBar {
  strike: number;
  callOi: number; // in number of contracts or units
  putOi: number;
  callOiFormatted: string; // e.g. "13.13L"
  putOiFormatted: string; // e.g. "13.51L"
}

export interface StrategyKPIs {
  netPremium: number;
  maxProfit: number | "Unlimited";
  maxLoss: number | "Unlimited";
  maxProfitFormatted: string;
  maxLossFormatted: string;
  breakevens: number[];
  breakevenPct: number[];
  rewardRisk: string;
  pop: number; // Probability of profit 0 - 100%
  timeValue: number;
  intrinsicValue: number;
  standaloneFunds: number;
  standaloneMargin: number;
  marginAvailable: number;
}

export interface NetGreeks {
  delta: number;
  theta: number;
  decay: number;
  gamma: number;
  vega: number;
}

export interface StandardDeviationMetrics {
  oneSdPoints: number;
  oneSdPct: number;
  oneSdLow: number;
  oneSdHigh: number;
  twoSdPoints: number;
  twoSdPct: number;
  twoSdLow: number;
  twoSdHigh: number;
}
