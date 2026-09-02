export interface Greeks {
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  rho?: number;
}

export interface OptionContract {
  symbol: string;
  strike: number;
  optionType: "CE" | "PE";
  expiry: string;
  ltp: number;
  bid: number;
  ask: number;
  iv: number;
  oi: number;
  oiChange: number;
  volume: number;
  greeks: Greeks;
}

export interface OptionStrikeRow {
  strike: number;
  isAtm: boolean;
  call: OptionContract;
  put: OptionContract;
}

export interface OptionChainData {
  underlying: string;
  underlyingPrice: number;
  atmStrike: number;
  selectedExpiry: string;
  expiries: string[];
  rows: OptionStrikeRow[];
  pcrRatio: number;
  maxPainStrike: number;
}

export interface OptionChainWidgetSettings {
  defaultUnderlying: string;
  strikesCount: number;
  showGreeks: boolean;
  showIV: boolean;
  showOI: boolean;
}
