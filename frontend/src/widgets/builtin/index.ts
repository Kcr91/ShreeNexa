import { widgetRegistry } from "../registry";
import {
  createLazyWidgetDefinition,
  type LazyWidgetManifest,
} from "./lazyDefinition";
import { builtinSchemas } from "./schemas";

export const builtinManifests: LazyWidgetManifest[] = [
  {
    id: "market-clock",
    title: "Market Clock",
    description: "Live session clock with timezone selection.",
    category: "system",
    icon: "⏰",
    defaultWidth: 300,
    defaultHeight: 180,
    schema: builtinSchemas["market-clock"],
    load: () =>
      import("./MarketClockWidget").then((module) => module.marketClockDefinition),
  },
  {
    id: "watchlist",
    title: "Market Watchlist",
    description:
      "Multiple manual and F&O watchlists with configurable columns and stable ordering.",
    category: "watchlist",
    icon: "📋",
    defaultWidth: 420,
    defaultHeight: 480,
    schema: builtinSchemas.watchlist,
    load: () =>
      import("./WatchlistWidget").then((module) => module.watchlistDefinition),
  },
  {
    id: "sector-drill-in",
    title: "Sector & Index Drill-In",
    description:
      "Browse sector constituents, effective membership intervals, and transparent provenance.",
    category: "watchlist",
    icon: "📊",
    defaultWidth: 460,
    defaultHeight: 520,
    schema: builtinSchemas["sector-drill-in"],
    load: () =>
      import("./SectorDrillInWidget").then(
        (module) => module.sectorDrillInDefinition,
      ),
  },
  {
    id: "market-heatmap",
    title: "Market Heatmap & Breadth",
    description:
      "Sectoral indices and constituent heatmaps with market breadth and transparent weighting.",
    category: "analytics",
    icon: "🔥",
    defaultWidth: 540,
    defaultHeight: 460,
    schema: builtinSchemas["market-heatmap"],
    load: () =>
      import("./MarketHeatmapWidget").then(
        (module) => module.marketHeatmapDefinition,
      ),
  },
  {
    id: "market-depth",
    title: "Market Depth Ladder & Watchlist",
    description:
      "20-level standard depth, on-demand 200-level book, and 5-level fallback with connection cost tracking.",
    category: "watchlist",
    icon: "📊",
    defaultWidth: 500,
    defaultHeight: 520,
    schema: builtinSchemas["market-depth"],
    load: () =>
      import("./MarketDepthWidget").then(
        (module) => module.marketDepthDefinition,
      ),
  },
  {
    id: "backtest-summary",
    title: "Backtest Performance Summary",
    description: "Key strategy performance metrics and return indicators.",
    category: "analytics",
    icon: "📊",
    defaultWidth: 340,
    defaultHeight: 220,
    schema: builtinSchemas["backtest-summary"],
    load: () =>
      import("./BacktestSummaryWidget").then(
        (module) => module.backtestSummaryDefinition,
      ),
  },
  {
    id: "fixture-test",
    title: "Fixture Dynamic Test Widget",
    description: "Test fixture verifying dynamic palette registration.",
    category: "custom",
    icon: "🧩",
    defaultWidth: 280,
    defaultHeight: 160,
    schema: builtinSchemas["fixture-test"],
    load: () =>
      import("./FixtureTestWidget").then(
        (module) => module.fixtureTestDefinition,
      ),
  },
  {
    id: "chart",
    title: "Candlestick Chart",
    description:
      "Multi-pane candlestick chart with indicators and session breaks.",
    category: "chart",
    icon: "📈",
    defaultWidth: 500,
    defaultHeight: 380,
    schema: builtinSchemas.chart,
    load: () =>
      import("./ChartWidget").then((module) => module.chartDefinition),
  },
  {
    id: "order-ticket",
    title: "Order Ticket & Leg Builder",
    description:
      "Stock and multi-leg options ticket with margin calculation and risk gates.",
    category: "order",
    icon: "🎫",
    defaultWidth: 380,
    defaultHeight: 460,
    schema: builtinSchemas["order-ticket"],
    load: () =>
      import("./OrderTicketWidget").then(
        (module) => module.orderTicketDefinition,
      ),
  },
  {
    id: "blotter",
    title: "Positions & Orders Blotter",
    description:
      "Real-time mark-to-market positions, working orders, trade log, and panic cancel button.",
    category: "order",
    icon: "📑",
    defaultWidth: 500,
    defaultHeight: 380,
    schema: builtinSchemas.blotter,
    load: () =>
      import("./BlotterWidget").then((module) => module.blotterDefinition),
  },
  {
    id: "option-chain",
    title: "Option Chain & Greeks",
    description:
      "Symmetrical strike ladder with Black-Scholes Greeks, IV, PCR, and leg selector.",
    category: "analytics",
    icon: "⛓️",
    defaultWidth: 550,
    defaultHeight: 420,
    schema: builtinSchemas["option-chain"],
    load: () =>
      import("./OptionChainWidget").then(
        (module) => module.optionChainDefinition,
      ),
  },
  {
    id: "backtest-analytics",
    title: "Backtest Analytics & Scorecard",
    description:
      "Institutional tear sheet, underwater drawdown, monthly return heatmap, and trade distribution.",
    category: "analytics",
    icon: "📊",
    defaultWidth: 520,
    defaultHeight: 400,
    schema: builtinSchemas["backtest-analytics"],
    load: () =>
      import("./BacktestAnalyticsWidget").then(
        (module) => module.backtestAnalyticsDefinition,
      ),
  },
  {
    id: "live-feed-status",
    title: "Live Feed & Telemetry",
    description:
      "Real-time WebSocket connection state, latency telemetry, and incoming tick streamer.",
    category: "analytics",
    icon: "📡",
    defaultWidth: 460,
    defaultHeight: 320,
    schema: builtinSchemas["live-feed-status"],
    load: () =>
      import("./LiveFeedStatusWidget").then(
        (module) => module.liveFeedStatusDefinition,
      ),
  },
  {
    id: "alerts-log",
    title: "Alerts & Audit Log",
    description:
      "Real-time notification manager, risk event alerts, and synthesized sound chime controls.",
    category: "analytics",
    icon: "🔔",
    defaultWidth: 480,
    defaultHeight: 340,
    schema: builtinSchemas["alerts-log"],
    load: () =>
      import("./AlertsLogWidget").then(
        (module) => module.alertsLogDefinition,
      ),
  },
  {
    id: "strategy-builder",
    title: "Visual Strategy Builder",
    description:
      "Block-based StrategyIR rule composer and instant vector backtest runner.",
    category: "analytics",
    icon: "🧱",
    defaultWidth: 700,
    defaultHeight: 450,
    schema: builtinSchemas["strategy-builder"],
    load: () =>
      import("./StrategyBuilderWidget").then(
        (module) => module.strategyBuilderDefinition,
      ),
  },
  {
    id: "strategy-marketplace",
    title: "Strategy Marketplace",
    description:
      "Browse curated quantitative strategy library, preview backtest tear sheets, and clone to workspace.",
    category: "analytics",
    icon: "🏪",
    defaultWidth: 720,
    defaultHeight: 480,
    schema: builtinSchemas["strategy-marketplace"],
    load: () =>
      import("./StrategyMarketplaceWidget").then(
        (module) => module.strategyMarketplaceDefinition,
      ),
  },
  {
    id: "pnl-calendar",
    title: "P&L Calendar",
    description:
      "Monthly trading performance grid, holiday schedule indicators, and trade book drill-down.",
    category: "analytics",
    icon: "📅",
    defaultWidth: 640,
    defaultHeight: 420,
    schema: builtinSchemas["pnl-calendar"],
    load: () =>
      import("./PnlCalendarWidget").then(
        (module) => module.pnlCalendarDefinition,
      ),
  },
  {
    id: "returns-timeline",
    title: "Returns & Timeline",
    description:
      "Monthly/yearly compounded returns, rolling return distributions, and Backtest -> Paper -> Live continuous timeline.",
    category: "analytics",
    icon: "📈",
    defaultWidth: 720,
    defaultHeight: 440,
    schema: builtinSchemas["returns-timeline"],
    load: () =>
      import("./ReturnsTimelineWidget").then(
        (module) => module.returnsTimelineDefinition,
      ),
  },
  {
    id: "grading-thresholds",
    title: "Grading Thresholds",
    description:
      "Configurable metric grading bands, live preview before save, stale scorecard tracking, and explicit re-grade.",
    category: "analytics",
    icon: "⚖️",
    defaultWidth: 700,
    defaultHeight: 460,
    schema: builtinSchemas["grading-thresholds"],
    load: () =>
      import("./GradingThresholdsWidget").then(
        (module) => module.gradingThresholdsDefinition,
      ),
  },
  {
    id: "options-analytics",
    title: "Options Analytics & Volatility",
    description:
      "Advanced ATM IV, IV Rank/Percentile, Max Pain, Volatility Smile/Skew, and Term Structure.",
    category: "analytics",
    icon: "📊",
    defaultWidth: 550,
    defaultHeight: 400,
    schema: builtinSchemas["options-analytics"],
    load: () =>
      import("../../optionchain/OptionsAnalyticsPanel").then(
        (module) => module.optionsAnalyticsDefinition,
      ),
  },
  {
    id: "option-strategy-builder",
    title: "Multi-Leg Option Strategy Builder",
    description:
      "Interactive multi-leg option payoff builder, breakevens, extrema, and net Greeks.",
    category: "analytics",
    icon: "🧩",
    defaultWidth: 600,
    defaultHeight: 450,
    schema: builtinSchemas["option-strategy-builder"],
    load: () =>
      import("./OptionStrategyBuilderWidget").then(
        (module) => module.optionStrategyBuilderDefinition,
      ),
  },
  {
    id: "paper_trading",
    title: "Paper Trading Blotter",
    description:
      "Paper order book, trade book, open positions, live MTM, and statutory costs.",
    category: "order",
    icon: "📜",
    defaultWidth: 620,
    defaultHeight: 420,
    schema: builtinSchemas.paper_trading,
    load: () =>
      import("./PaperTradingWidget").then(
        (module) => module.paperTradingDefinition,
      ),
  },
];

export function registerBuiltinWidgets(): void {
  for (const manifest of builtinManifests) {
    widgetRegistry.register(createLazyWidgetDefinition(manifest));
  }
}

// Auto-register built-in widget metadata. Implementations remain lazy.
registerBuiltinWidgets();
