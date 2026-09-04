import type { WidgetSettingsSchema } from "../types";

export const builtinSchemas = {
  watchlist: {
    fields: [
      {
        name: "defaultWatchlistId",
        label: "Default Watchlist",
        type: "select",
        default: "wl-nifty50",
        options: [
          { label: "NIFTY 50", value: "wl-nifty50" },
          { label: "BANK NIFTY F&O", value: "wl-banknifty-fno" },
          { label: "Breakout Stocks", value: "wl-breakout" },
        ],
      },
      {
        name: "refreshIntervalSec",
        label: "Refresh Interval (s)",
        type: "number",
        default: 1,
        min: 1,
        max: 60,
      },
    ],
  },
  "sector-drill-in": {
    fields: [
      {
        name: "defaultIndexName",
        label: "Default Index",
        type: "select",
        default: "NIFTY 50",
        options: [
          { label: "NIFTY 50", value: "NIFTY 50" },
          { label: "NIFTY BANK", value: "NIFTY BANK" },
          { label: "NIFTY IT", value: "NIFTY IT" },
          { label: "NIFTY AUTO", value: "NIFTY AUTO" },
        ],
      },
    ],
  },
  "market-heatmap": {
    fields: [
      {
        name: "defaultMode",
        label: "Default Mode",
        type: "select",
        default: "INDICES",
        options: [
          { label: "Sectoral Indices", value: "INDICES" },
          { label: "Constituents Drill-In", value: "CONSTITUENTS" },
        ],
      },
      {
        name: "defaultIndexName",
        label: "Default Index",
        type: "select",
        default: "NIFTY 50",
        options: [
          { label: "NIFTY 50", value: "NIFTY 50" },
          { label: "NIFTY BANK", value: "NIFTY BANK" },
          { label: "NIFTY IT", value: "NIFTY IT" },
          { label: "NIFTY AUTO", value: "NIFTY AUTO" },
        ],
      },
    ],
  },
  "market-depth": {
    fields: [
      {
        name: "defaultSymbol",
        label: "Default Symbol",
        type: "string",
        default: "RELIANCE",
      },
      {
        name: "defaultSegment",
        label: "Default Segment",
        type: "select",
        default: "NSE_EQ",
        options: [
          { label: "NSE Equity", value: "NSE_EQ" },
          { label: "NSE Derivatives", value: "NSE_FNO" },
          { label: "BSE Equity (5-Level)", value: "BSE_EQ" },
          { label: "MCX Commodities (5-Level)", value: "MCX_COMM" },
        ],
      },
      {
        name: "defaultLevel",
        label: "Depth Level",
        type: "select",
        default: "LEVEL_20",
        options: [
          { label: "5-Level", value: "LEVEL_5" },
          { label: "20-Level (Standard)", value: "LEVEL_20" },
          { label: "200-Level (On Demand)", value: "LEVEL_200" },
        ],
      },
      {
        name: "defaultMode",
        label: "Default View",
        type: "select",
        default: "LADDER",
        options: [
          { label: "Depth Ladder", value: "LADDER" },
          { label: "Depth Watchlist", value: "WATCHLIST" },
        ],
      },
    ],
  },
  "backtest-summary": {
    fields: [
      {
        name: "strategyName",
        label: "Strategy Name",
        type: "string",
        default: "NIFTY Alpha Trend",
        required: true,
      },
      {
        name: "displayMode",
        label: "Display Mode",
        type: "select",
        default: "detailed",
        options: [
          { label: "Compact", value: "compact" },
          { label: "Detailed", value: "detailed" },
        ],
      },
    ],
  },
  "fixture-test": {
    fields: [
      {
        name: "customMessage",
        label: "Custom Message",
        type: "string",
        default: "Hello ShreeNexa",
        required: true,
      },
      {
        name: "samplingRate",
        label: "Sampling Rate",
        type: "number",
        default: 10,
        min: 1,
        max: 100,
      },
    ],
  },
  chart: {
    fields: [
      {
        name: "symbol",
        label: "Symbol",
        type: "select",
        default: "RELIANCE",
        options: [
          { label: "RELIANCE", value: "RELIANCE" },
          { label: "TCS", value: "TCS" },
          { label: "HDFCBANK", value: "HDFCBANK" },
          { label: "INFY", value: "INFY" },
        ],
      },
      {
        name: "timeframe",
        label: "Default Timeframe",
        type: "select",
        default: "5m",
        options: [
          { label: "1 Minute", value: "1m" },
          { label: "5 Minutes", value: "5m" },
          { label: "15 Minutes", value: "15m" },
          { label: "1 Hour", value: "1h" },
          { label: "1 Day", value: "1d" },
        ],
      },
      {
        name: "showSessionBreaks",
        label: "Show Session Breaks",
        type: "boolean",
        default: true,
      },
      {
        name: "showVolume",
        label: "Show Volume Pane",
        type: "boolean",
        default: true,
      },
    ],
  },
  "order-ticket": {
    fields: [
      {
        name: "defaultAssetClass",
        label: "Default Asset Class",
        type: "select",
        default: "EQUITY",
        options: [
          { label: "Equity Stock", value: "EQUITY" },
          { label: "Multi-Leg Options", value: "OPTION" },
        ],
      },
      {
        name: "defaultSymbol",
        label: "Default Symbol",
        type: "string",
        default: "RELIANCE",
      },
      {
        name: "defaultQuantity",
        label: "Default Quantity",
        type: "number",
        default: 25,
        min: 1,
      },
    ],
  },
  blotter: {
    fields: [
      {
        name: "defaultTab",
        label: "Default Active Tab",
        type: "select",
        default: "POSITIONS",
        options: [
          { label: "Positions", value: "POSITIONS" },
          { label: "Open Orders", value: "OPEN_ORDERS" },
          { label: "Trade Log", value: "TRADE_LOG" },
        ],
      },
      {
        name: "showRealizedPnl",
        label: "Show Realized PnL",
        type: "boolean",
        default: true,
      },
    ],
  },
  "option-chain": {
    fields: [
      {
        name: "defaultUnderlying",
        label: "Default Index",
        type: "select",
        default: "NIFTY",
        options: [
          { label: "NIFTY", value: "NIFTY" },
          { label: "BANKNIFTY", value: "BANKNIFTY" },
        ],
      },
      {
        name: "strikesCount",
        label: "Strikes Count (± ATM)",
        type: "number",
        default: 8,
        min: 4,
        max: 20,
      },
      {
        name: "showGreeks",
        label: "Display Greeks",
        type: "boolean",
        default: true,
      },
      {
        name: "showIV",
        label: "Display IV",
        type: "boolean",
        default: true,
      },
    ],
  },
  "backtest-analytics": {
    fields: [
      {
        name: "defaultMetricView",
        label: "Default View",
        type: "select",
        default: "SCORECARD",
        options: [
          { label: "Tear Sheet Scorecard", value: "SCORECARD" },
          { label: "Equity Curve", value: "EQUITY_CURVE" },
          { label: "Underwater Drawdown", value: "UNDERWATER" },
          { label: "Monthly Heatmap", value: "MONTHLY_HEATMAP" },
          { label: "Trade Distribution", value: "TRADE_DISTRIBUTION" },
        ],
      },
      {
        name: "showBenchmark",
        label: "Show Benchmark Comparison",
        type: "boolean",
        default: true,
      },
    ],
  },
  "live-feed-status": {
    fields: [
      {
        name: "showTickStream",
        label: "Show Live Tick Stream",
        type: "boolean",
        default: true,
      },
      {
        name: "maxStreamHistory",
        label: "Max Stream Rows",
        type: "number",
        default: 15,
      },
    ],
  },
  "alerts-log": {
    fields: [
      {
        name: "defaultFilter",
        label: "Default Filter",
        type: "select",
        default: "ALL",
        options: [
          { label: "All Alerts", value: "ALL" },
          { label: "Critical & Risk", value: "CRITICAL" },
          { label: "Order Executions", value: "ORDERS" },
          { label: "Risk Breaches", value: "RISK" },
        ],
      },
      {
        name: "showSoundToggle",
        label: "Show Sound Toggle",
        type: "boolean",
        default: true,
      },
    ],
  },
  "strategy-builder": {
    fields: [
      {
        name: "showJsonPreview",
        label: "Show StrategyIR Preview",
        type: "boolean",
        default: true,
      },
      {
        name: "defaultUniverse",
        label: "Default Universe",
        type: "string",
        default: "NIFTY 50",
      },
    ],
  },
  "strategy-marketplace": {
    fields: [
      {
        name: "defaultCategory",
        label: "Default Category",
        type: "select",
        default: "ALL",
        options: [
          { label: "All Categories", value: "ALL" },
          { label: "Options Income", value: "OPTIONS_INCOME" },
          { label: "Momentum", value: "MOMENTUM" },
          { label: "Breakout", value: "BREAKOUT" },
          { label: "Volatility", value: "VOLATILITY" },
        ],
      },
      {
        name: "defaultAssetClass",
        label: "Default Asset Class",
        type: "select",
        default: "ALL",
        options: [
          { label: "All Assets", value: "ALL" },
          { label: "Equity", value: "EQUITY" },
          { label: "Options", value: "OPTIONS" },
          { label: "Futures", value: "FUTURES" },
        ],
      },
    ],
  },
  "pnl-calendar": {
    fields: [
      {
        name: "defaultMonth",
        label: "Default Month",
        type: "string",
        default: "2026-08",
      },
      {
        name: "showCharges",
        label: "Show Brokerage & Taxes",
        type: "boolean",
        default: true,
      },
      {
        name: "showWeekends",
        label: "Show Weekends",
        type: "boolean",
        default: true,
      },
      {
        name: "sourceKind",
        label: "Execution Source",
        type: "select",
        default: "backtest",
        options: [
          { label: "Backtest", value: "backtest" },
          { label: "Paper Trading", value: "paper" },
        ],
      },
    ],
  },
  "returns-timeline": {
    fields: [
      {
        name: "activePhaseFilter",
        label: "Initial Phase Filter",
        type: "string",
        default: "ALL",
      },
      {
        name: "initialCapital",
        label: "Initial Capital (₹)",
        type: "number",
        default: 1000000,
      },
    ],
  },
  "grading-thresholds": {
    fields: [
      {
        name: "defaultHorizon",
        label: "Default Horizon Profile",
        type: "string",
        default: "POSITIONAL",
      },
    ],
  },
  "options-analytics": {
    fields: [
      {
        name: "underlying",
        label: "Underlying Index",
        type: "select",
        default: "NIFTY",
        options: [
          { label: "NIFTY", value: "NIFTY" },
          { label: "BANKNIFTY", value: "BANKNIFTY" },
        ],
      },
    ],
  },
  "option-strategy-builder": {
    fields: [
      {
        name: "defaultUnderlying",
        label: "Underlying Index",
        type: "select",
        default: "NIFTY",
        options: [
          { label: "NIFTY", value: "NIFTY" },
          { label: "BANKNIFTY", value: "BANKNIFTY" },
        ],
      },
    ],
  },
  paper_trading: {
    fields: [
      {
        name: "accountId",
        label: "Account ID",
        type: "string",
        default: "default",
      },
      {
        name: "defaultTab",
        label: "Default Tab",
        type: "select",
        default: "POSITIONS",
        options: [
          { label: "Positions", value: "POSITIONS" },
          { label: "Order Book", value: "ORDER_BOOK" },
          { label: "Trade Book", value: "TRADE_BOOK" },
          { label: "Reconciliation", value: "RECONCILIATION" },
        ],
      },
      {
        name: "autoRefreshInterval",
        label: "Auto Refresh (ms)",
        type: "number",
        default: 3000,
      },
    ],
  },
} satisfies Record<string, WidgetSettingsSchema>;
