import React from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";

export interface BacktestSummarySettings {
  strategyName: string;
  displayMode: "compact" | "detailed";
}

export const BacktestSummaryWidget: React.FC<WidgetComponentProps<BacktestSummarySettings>> = ({
  settings,
}) => {
  return (
    <div style={{ height: "100%", padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
      <div style={{ fontSize: "var(--font-size-sm)", fontWeight: "bold", color: "var(--text-primary)" }}>
        Strategy: {settings.strategyName || "Momentum Breakout v1"}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-2)", fontSize: "var(--font-size-sm)" }}>
        <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Total Return</div>
          <div style={{ fontWeight: 600, color: "var(--color-up)", fontFamily: "var(--font-family-mono)" }}>+38.5%</div>
        </div>

        <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Sharpe Ratio</div>
          <div style={{ fontWeight: 600, fontFamily: "var(--font-family-mono)" }}>1.85</div>
        </div>

        <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Max Drawdown</div>
          <div style={{ fontWeight: 600, color: "var(--color-down)", fontFamily: "var(--font-family-mono)" }}>-6.2%</div>
        </div>

        <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Win Rate</div>
          <div style={{ fontWeight: 600, fontFamily: "var(--font-family-mono)" }}>58.4%</div>
        </div>
      </div>
    </div>
  );
};

export const backtestSummaryDefinition: WidgetDefinition<BacktestSummarySettings> = {
  id: "backtest-summary",
  title: "Backtest Performance Summary",
  description: "Key strategy performance metrics and return indicators.",
  category: "analytics",
  icon: "📊",
  defaultWidth: 340,
  defaultHeight: 220,
  schema: {
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
  component: BacktestSummaryWidget,
};
