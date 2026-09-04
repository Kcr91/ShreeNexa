import { WorkspaceLayout } from "./types";

export interface WorkspaceTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  layout: WorkspaceLayout;
}

export const PREBUILT_TEMPLATES: WorkspaceTemplate[] = [
  {
    id: "day-trader",
    name: "Day Trader Terminal",
    description: "Real-time Candlestick chart, live watchlist, quick order ticket, and positions blotter.",
    icon: "📈",
    layout: {
      version: 1,
      activeTabId: "tab-day-trading",
      tabs: [
        {
          id: "tab-day-trading",
          name: "Day Trading",
          widgets: [
            {
              instanceId: "inst-chart-1",
              widgetId: "chart",
              position: { x: 0, y: 0, w: 7, h: 5 },
              settings: { symbol: "RELIANCE", timeframe: "5m", showSessionBreaks: true, showVolume: true },
            },
            {
              instanceId: "inst-watchlist-1",
              widgetId: "watchlist",
              position: { x: 7, y: 0, w: 5, h: 5 },
              settings: { title: "Nifty 50 Watchlist", refreshIntervalSeconds: 3 },
            },
            {
              instanceId: "inst-ticket-1",
              widgetId: "order-ticket",
              position: { x: 0, y: 5, w: 5, h: 5 },
              settings: { defaultAssetClass: "EQUITY", defaultSymbol: "RELIANCE", defaultQuantity: 25 },
            },
            {
              instanceId: "inst-blotter-1",
              widgetId: "blotter",
              position: { x: 5, y: 5, w: 7, h: 5 },
              settings: { defaultTab: "POSITIONS", refreshIntervalMs: 1000, showRealizedPnl: true },
            },
          ],
        },
      ],
    },
  },
  {
    id: "options-desk",
    name: "Options Derivatives Desk",
    description: "Symmetrical option chain with Greeks & IV, multi-leg order builder, and position manager.",
    icon: "⛓️",
    layout: {
      version: 1,
      activeTabId: "tab-options-desk",
      tabs: [
        {
          id: "tab-options-desk",
          name: "Options Desk",
          widgets: [
            {
              instanceId: "inst-chain-1",
              widgetId: "option-chain",
              position: { x: 0, y: 0, w: 12, h: 5 },
              settings: { defaultUnderlying: "NIFTY", strikesCount: 8, showGreeks: true, showIV: true },
            },
            {
              instanceId: "inst-ticket-2",
              widgetId: "order-ticket",
              position: { x: 0, y: 5, w: 5, h: 5 },
              settings: { defaultAssetClass: "OPTION", defaultSymbol: "NIFTY", defaultQuantity: 50 },
            },
            {
              instanceId: "inst-blotter-2",
              widgetId: "blotter",
              position: { x: 5, y: 5, w: 7, h: 5 },
              settings: { defaultTab: "POSITIONS", refreshIntervalMs: 1000, showRealizedPnl: true },
            },
          ],
        },
      ],
    },
  },
  {
    id: "quant-lab",
    name: "Quant Research Lab",
    description: "Backtest performance tear sheet, cumulative equity curve, and strategy statistics.",
    icon: "🔬",
    layout: {
      version: 1,
      activeTabId: "tab-quant-lab",
      tabs: [
        {
          id: "tab-quant-lab",
          name: "Quant Research",
          widgets: [
            {
              instanceId: "inst-analytics-1",
              widgetId: "backtest-analytics",
              position: { x: 0, y: 0, w: 8, h: 7 },
              settings: { defaultMetricView: "SCORECARD", showBenchmark: true },
            },
            {
              instanceId: "inst-summary-1",
              widgetId: "backtest-summary",
              position: { x: 8, y: 0, w: 4, h: 7 },
              settings: { strategyName: "NIFTY Intraday Momentum", showBenchmark: true },
            },
          ],
        },
      ],
    },
  },
];
