import { widgetRegistry } from "../registry";
import { marketClockDefinition } from "./MarketClockWidget";
import { watchlistDefinition } from "./WatchlistWidget";
import { backtestSummaryDefinition } from "./BacktestSummaryWidget";
import { fixtureTestDefinition } from "./FixtureTestWidget";
import { chartDefinition } from "./ChartWidget";
import { orderTicketDefinition } from "./OrderTicketWidget";

export function registerBuiltinWidgets(): void {
  widgetRegistry.register(marketClockDefinition);
  widgetRegistry.register(watchlistDefinition);
  widgetRegistry.register(backtestSummaryDefinition);
  widgetRegistry.register(fixtureTestDefinition);
  widgetRegistry.register(chartDefinition);
  widgetRegistry.register(orderTicketDefinition);
}

// Auto-register built-in widgets
registerBuiltinWidgets();
