import { MarketplaceStrategy } from "./types";

export const MARKETPLACE_CATALOG: MarketplaceStrategy[] = [
  {
    id: "nifty-iron-condor",
    title: "NIFTY Weekly Iron Condor",
    description:
      "Delta 15 OTM short strangle with dynamic wing protection and stop-loss adjustment for weekly expiry.",
    author: {
      name: "Arjun Verma, QF",
      handle: "@arjun_quant",
      verified: true,
      avatar: "🏛️",
    },
    category: "OPTIONS_INCOME",
    tags: ["NIFTY", "Options", "Delta Neutral", "Weekly Expiry"],
    assetClass: "OPTIONS",
    timeframe: "15m",
    performance: {
      cagrPct: 32.4,
      sharpeRatio: 2.41,
      maxDrawdownPct: 4.8,
      winRatePct: 76.5,
      totalTrades: 156,
      profitFactor: 2.85,
    },
    strategyIR: {
      ir_version: 1,
      strategy_id: "ir-nifty-iron-condor",
      name: "NIFTY Weekly Iron Condor",
      universe: "NIFTY 50",
      timeframe: "15m",
      indicators: {
        iv_rank: { function: "rsi", params: { period: 20 } },
      },
      entry_rules: [
        {
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [{ left: "iv_rank", op: "GREATER_THAN", right: "30" }],
        },
      ],
      exit_rules: [
        {
          type: "EXIT_LONG",
          combinator: "OR",
          conditions: [{ left: "iv_rank", op: "LESS_THAN", right: "15" }],
        },
      ],
      risk_rules: {
        stop_loss_pct: 1.5,
        take_profit_pct: 3.0,
      },
    },
    clonesCount: 342,
    likesCount: 890,
  },
  {
    id: "banknifty-supertrend",
    title: "BankNifty Supertrend Breakout",
    description:
      "Intraday breakout strategy using ATR-based Supertrend with volume spike confirmation on 15m bars.",
    author: {
      name: "Priya Sharma",
      handle: "@priya_algo",
      verified: true,
      avatar: "⚡",
    },
    category: "BREAKOUT",
    tags: ["BANKNIFTY", "Futures", "Breakout", "Intraday"],
    assetClass: "FUTURES",
    timeframe: "15m",
    performance: {
      cagrPct: 44.8,
      sharpeRatio: 1.88,
      maxDrawdownPct: 8.2,
      winRatePct: 58.2,
      totalTrades: 284,
      profitFactor: 2.12,
    },
    strategyIR: {
      ir_version: 1,
      strategy_id: "ir-banknifty-supertrend",
      name: "BankNifty Supertrend Breakout",
      universe: "BANKNIFTY",
      timeframe: "15m",
      indicators: {
        fast_ema: { function: "ema", params: { period: 9, source: "close" } },
        slow_ema: { function: "ema", params: { period: 21, source: "close" } },
      },
      entry_rules: [
        {
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [{ left: "fast_ema", op: "CROSS_ABOVE", right: "slow_ema" }],
        },
      ],
      exit_rules: [
        {
          type: "EXIT_LONG",
          combinator: "OR",
          conditions: [{ left: "fast_ema", op: "CROSS_BELOW", right: "slow_ema" }],
        },
      ],
      risk_rules: {
        stop_loss_pct: 1.0,
        take_profit_pct: 2.5,
      },
    },
    clonesCount: 512,
    likesCount: 1240,
  },
  {
    id: "nifty50-golden-cross",
    title: "NIFTY 50 Golden Cross Momentum",
    description:
      "Classic dual moving average trend following system with 9/21 EMA crossover and RSI momentum filter.",
    author: {
      name: "Nexa Quant Lab",
      handle: "@shreenexa_quant",
      verified: true,
      avatar: "📈",
    },
    category: "MOMENTUM",
    tags: ["NIFTY 50", "Equity", "Trend", "Momentum"],
    assetClass: "EQUITY",
    timeframe: "1d",
    performance: {
      cagrPct: 26.5,
      sharpeRatio: 1.95,
      maxDrawdownPct: 6.4,
      winRatePct: 64.2,
      totalTrades: 92,
      profitFactor: 2.45,
    },
    strategyIR: {
      ir_version: 1,
      strategy_id: "ir-nifty50-golden-cross",
      name: "NIFTY 50 Golden Cross Momentum",
      universe: "NIFTY 50",
      timeframe: "1d",
      indicators: {
        ema_9: { function: "ema", params: { period: 9, source: "close" } },
        ema_21: { function: "ema", params: { period: 21, source: "close" } },
        rsi_14: { function: "rsi", params: { period: 14 } },
      },
      entry_rules: [
        {
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [
            { left: "ema_9", op: "CROSS_ABOVE", right: "ema_21" },
            { left: "rsi_14", op: "GREATER_THAN", right: "50" },
          ],
        },
      ],
      exit_rules: [
        {
          type: "EXIT_LONG",
          combinator: "OR",
          conditions: [
            { left: "ema_9", op: "CROSS_BELOW", right: "ema_21" },
            { left: "rsi_14", op: "LESS_THAN", right: "40" },
          ],
        },
      ],
      risk_rules: {
        stop_loss_pct: 2.0,
        take_profit_pct: 5.0,
      },
    },
    clonesCount: 820,
    likesCount: 2100,
  },
  {
    id: "finnifty-gamma-0dte",
    title: "FinNifty Gamma Scalper 0DTE",
    description:
      "Ultra-short intraday gamma scalping on Tuesday expiry using ATM straddle decay and rapid hedging.",
    author: {
      name: "Rohan Kulkarni",
      handle: "@rohan_derivs",
      verified: true,
      avatar: "🎯",
    },
    category: "VOLATILITY",
    tags: ["FINNIFTY", "Options", "0DTE", "Gamma Scalp"],
    assetClass: "OPTIONS",
    timeframe: "5m",
    performance: {
      cagrPct: 52.1,
      sharpeRatio: 2.15,
      maxDrawdownPct: 7.9,
      winRatePct: 71.4,
      totalTrades: 340,
      profitFactor: 2.65,
    },
    strategyIR: {
      ir_version: 1,
      strategy_id: "ir-finnifty-gamma-0dte",
      name: "FinNifty Gamma Scalper 0DTE",
      universe: "FINNIFTY",
      timeframe: "5m",
      indicators: {
        rsi: { function: "rsi", params: { period: 10 } },
      },
      entry_rules: [
        {
          type: "ENTRY_LONG",
          combinator: "AND",
          conditions: [{ left: "rsi", op: "GREATER_THAN", right: "55" }],
        },
      ],
      exit_rules: [
        {
          type: "EXIT_LONG",
          combinator: "OR",
          conditions: [{ left: "rsi", op: "LESS_THAN", right: "45" }],
        },
      ],
      risk_rules: {
        stop_loss_pct: 0.8,
        take_profit_pct: 1.8,
      },
    },
    clonesCount: 420,
    likesCount: 980,
  },
];
