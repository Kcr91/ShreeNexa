import { StrategyBuilderState } from "./types";

export function createDefaultStrategyState(): StrategyBuilderState {
  return {
    strategyName: "New Strategy",
    universe: "NIFTY 50",
    timeframe: "15m",
    indicators: [],
    rules: [],
    stopLossPct: 1.0,
    takeProfitPct: 2.0,
    kind: "stock",
    horizon: "intraday",
    strategyType: "trend_following",
    candleConditions: [],
    timeFilters: [],
    breakoutConditions: [],
    exits: [
      { id: "exit-sl", type: "stop", pct: 1.0 },
      { id: "exit-tp", type: "target", pct: 2.0 },
    ],
    sizing: { type: "fixed_value", value: 50000 },
    risk: {
      maxPositions: 5,
      noTradeWindows: [],
    },
  };
}

// Indicator catalog metadata used by IndicatorPanel.
export interface IndicatorCatalogEntry {
  fn: import("./types").IndicatorFunction;
  label: string;
  category: "trend" | "momentum" | "volatility" | "volume" | "price_levels" | "custom";
  defaultParams: Record<string, number | string>;
  paramFields: Array<{ key: string; label: string; type: "number" | "text"; min?: number; max?: number; step?: number }>;
}

export const INDICATOR_CATALOG: IndicatorCatalogEntry[] = [
  // Trend
  { fn: "ema", label: "EMA", category: "trend", defaultParams: { period: 20, source: "close" }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "sma", label: "SMA", category: "trend", defaultParams: { period: 20, source: "close" }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "supertrend", label: "SuperTrend", category: "trend", defaultParams: { period: 10, multiplier: 3 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }, { key: "multiplier", label: "Multiplier", type: "number", min: 0.1, step: 0.1 }] },
  { fn: "psar", label: "Parabolic SAR", category: "trend", defaultParams: { acceleration: 0.02, maximum: 0.2 }, paramFields: [{ key: "acceleration", label: "Acceleration", type: "number", min: 0.001, step: 0.001 }, { key: "maximum", label: "Maximum", type: "number", min: 0.001, step: 0.01 }] },
  { fn: "ichimoku", label: "Ichimoku", category: "trend", defaultParams: { tenkan: 9, kijun: 26, senkou: 52 }, paramFields: [{ key: "tenkan", label: "Tenkan", type: "number", min: 1 }, { key: "kijun", label: "Kijun", type: "number", min: 1 }, { key: "senkou", label: "Senkou", type: "number", min: 1 }] },
  { fn: "aroon", label: "Aroon", category: "trend", defaultParams: { period: 14 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },

  // Momentum
  { fn: "rsi", label: "RSI", category: "momentum", defaultParams: { period: 14 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "macd", label: "MACD", category: "momentum", defaultParams: { fast: 12, slow: 26, signal: 9 }, paramFields: [{ key: "fast", label: "Fast", type: "number", min: 1 }, { key: "slow", label: "Slow", type: "number", min: 1 }, { key: "signal", label: "Signal", type: "number", min: 1 }] },
  { fn: "stochastic", label: "Stochastic", category: "momentum", defaultParams: { k_period: 14, d_period: 3, slowing: 3 }, paramFields: [{ key: "k_period", label: "K Period", type: "number", min: 1 }, { key: "d_period", label: "D Period", type: "number", min: 1 }, { key: "slowing", label: "Slowing", type: "number", min: 1 }] },
  { fn: "adx", label: "ADX", category: "momentum", defaultParams: { period: 14 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "cci", label: "CCI", category: "momentum", defaultParams: { period: 20 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "williams_r", label: "Williams %R", category: "momentum", defaultParams: { period: 14 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "mfi", label: "Money Flow Index", category: "momentum", defaultParams: { period: 14 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },

  // Volatility
  { fn: "bollinger", label: "Bollinger Bands", category: "volatility", defaultParams: { period: 20, std_dev: 2 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }, { key: "std_dev", label: "Std Dev", type: "number", min: 0.1, step: 0.1 }] },
  { fn: "atr", label: "ATR", category: "volatility", defaultParams: { period: 14 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },
  { fn: "keltner", label: "Keltner Channel", category: "volatility", defaultParams: { period: 20, multiplier: 2 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }, { key: "multiplier", label: "Multiplier", type: "number", min: 0.1, step: 0.1 }] },
  { fn: "donchian", label: "Donchian Channel", category: "volatility", defaultParams: { period: 20 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },

  // Volume
  { fn: "obv", label: "OBV", category: "volume", defaultParams: {}, paramFields: [] },
  { fn: "vwap", label: "VWAP", category: "volume", defaultParams: {}, paramFields: [] },
  { fn: "volume_sma", label: "Volume SMA", category: "volume", defaultParams: { period: 20 }, paramFields: [{ key: "period", label: "Period", type: "number", min: 1 }] },

  // Price Levels
  { fn: "pivot_points", label: "Pivot Points", category: "price_levels", defaultParams: { type: "classic" }, paramFields: [{ key: "type", label: "Type", type: "text" }] },
  { fn: "prev_day_high", label: "Prev Day High", category: "price_levels", defaultParams: {}, paramFields: [] },
  { fn: "prev_day_low", label: "Prev Day Low", category: "price_levels", defaultParams: {}, paramFields: [] },
  { fn: "prev_day_close", label: "Prev Day Close", category: "price_levels", defaultParams: {}, paramFields: [] },
  { fn: "prev_day_open", label: "Prev Day Open", category: "price_levels", defaultParams: {}, paramFields: [] },
  { fn: "opening_range_high", label: "Opening Range High", category: "price_levels", defaultParams: { minutes: 15 }, paramFields: [{ key: "minutes", label: "Minutes", type: "number", min: 1 }] },
  { fn: "opening_range_low", label: "Opening Range Low", category: "price_levels", defaultParams: { minutes: 15 }, paramFields: [{ key: "minutes", label: "Minutes", type: "number", min: 1 }] },

  // Custom
  { fn: "custom", label: "Custom", category: "custom", defaultParams: { formula: "" }, paramFields: [{ key: "formula", label: "Formula", type: "text" }] },
];

export const INDICATOR_CATEGORY_LABELS: Record<IndicatorCatalogEntry["category"], string> = {
  trend: "Trend",
  momentum: "Momentum",
  volatility: "Volatility",
  volume: "Volume",
  price_levels: "Price Levels",
  custom: "Custom",
};

export const TIMEFRAME_OPTIONS = [
  "1m", "3m", "5m", "10m", "15m", "30m", "1h", "2h", "4h", "1D", "1W", "1M",
];

export const INDEX_OPTIONS = [
  "NIFTY 50",
  "NIFTY BANK",
  "NIFTY IT",
  "NIFTY NEXT 50",
  "NIFTY MIDCAP 50",
  "NIFTY FIN SERVICE",
  "SENSEX",
  "BANKEX",
];
