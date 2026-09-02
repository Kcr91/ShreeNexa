import { widgetRegistry } from "../registry";
import { marketClockDefinition } from "./MarketClockWidget";
import { watchlistDefinition } from "./WatchlistWidget";
import { backtestSummaryDefinition } from "./BacktestSummaryWidget";
import { fixtureTestDefinition } from "./FixtureTestWidget";
import { chartDefinition } from "./ChartWidget";
import { orderTicketDefinition } from "./OrderTicketWidget";
import { blotterDefinition } from "./BlotterWidget";
import { optionChainDefinition } from "./OptionChainWidget";

export function registerBuiltinWidgets(): void {
  widgetRegistry.register(marketClockDefinition);
  widgetRegistry.register(watchlistDefinition);
  widgetRegistry.register(backtestSummaryDefinition);
  widgetRegistry.register(fixtureTestDefinition);
  widgetRegistry.register(chartDefinition);
  widgetRegistry.register(orderTicketDefinition);
  widgetRegistry.register(blotterDefinition);
  widgetRegistry.register(optionChainDefinition);
}

// Auto-register built-in widgets
registerBuiltinWidgets();
