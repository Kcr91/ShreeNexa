import { widgetRegistry } from "../registry";
import { marketClockDefinition } from "./MarketClockWidget";
import { watchlistDefinition } from "./WatchlistWidget";
import { backtestSummaryDefinition } from "./BacktestSummaryWidget";
import { fixtureTestDefinition } from "./FixtureTestWidget";
import { chartDefinition } from "./ChartWidget";
import { orderTicketDefinition } from "./OrderTicketWidget";
import { blotterDefinition } from "./BlotterWidget";
import { optionChainDefinition } from "./OptionChainWidget";
import { backtestAnalyticsDefinition } from "./BacktestAnalyticsWidget";
import { liveFeedStatusDefinition } from "./LiveFeedStatusWidget";
import { alertsLogDefinition } from "./AlertsLogWidget";
import { strategyBuilderDefinition } from "./StrategyBuilderWidget";
import { strategyMarketplaceDefinition } from "./StrategyMarketplaceWidget";

export function registerBuiltinWidgets(): void {
  widgetRegistry.register(marketClockDefinition);
  widgetRegistry.register(watchlistDefinition);
  widgetRegistry.register(backtestSummaryDefinition);
  widgetRegistry.register(fixtureTestDefinition);
  widgetRegistry.register(chartDefinition);
  widgetRegistry.register(orderTicketDefinition);
  widgetRegistry.register(blotterDefinition);
  widgetRegistry.register(optionChainDefinition);
  widgetRegistry.register(backtestAnalyticsDefinition);
  widgetRegistry.register(liveFeedStatusDefinition);
  widgetRegistry.register(alertsLogDefinition);
  widgetRegistry.register(strategyBuilderDefinition);
  widgetRegistry.register(strategyMarketplaceDefinition);
}

// Auto-register built-in widgets
registerBuiltinWidgets();
