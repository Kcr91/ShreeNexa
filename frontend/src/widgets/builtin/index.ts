import { widgetRegistry } from "../registry";
import { marketClockDefinition } from "./MarketClockWidget";
import { watchlistDefinition } from "./WatchlistWidget";
import { backtestSummaryDefinition } from "./BacktestSummaryWidget";
import { fixtureTestDefinition } from "./FixtureTestWidget";

export function registerBuiltinWidgets(): void {
  widgetRegistry.register(marketClockDefinition);
  widgetRegistry.register(watchlistDefinition);
  widgetRegistry.register(backtestSummaryDefinition);
  widgetRegistry.register(fixtureTestDefinition);
}

// Auto-register built-in widgets
registerBuiltinWidgets();
