import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { BarData, ChartIndicatorConfig, ChartWidgetSettings } from "../../chart/types";
import { ChartContainer } from "../../chart/ChartContainer";

function generateMockBars(symbol: string, _timeframe: string): BarData[] {
  const bars: BarData[] = [];
  const basePrice = symbol === "RELIANCE" ? 2950 : symbol === "TCS" ? 4200 : 1600;
  let currentPrice = basePrice;

  const dates = ["2026-01-05", "2026-01-06", "2026-01-07"];
  const times = [
    "09:15:00", "09:30:00", "10:00:00", "10:30:00", "11:00:00",
    "11:30:00", "12:00:00", "12:30:00", "13:00:00", "13:30:00",
    "14:00:00", "14:30:00", "15:00:00", "15:15:00", "15:30:00",
  ];

  let step = 0;
  for (const date of dates) {
    for (const time of times) {
      step += 1;
      const open = currentPrice;
      // Deterministic pseudo-historical oscillation without Math.random
      const change = Number((Math.sin(step * 0.45) * 6.5 + Math.cos(step * 0.15) * 3.2).toFixed(2));
      const close = Number((open + change).toFixed(2));
      const highOffset = Number((Math.abs(Math.sin(step * 0.8)) * 4.0 + 1.0).toFixed(2));
      const lowOffset = Number((Math.abs(Math.cos(step * 0.8)) * 4.0 + 1.0).toFixed(2));
      const high = Number((Math.max(open, close) + highOffset).toFixed(2));
      const low = Number((Math.min(open, close) - lowOffset).toFixed(2));
      const volume = 25000 + Math.floor(Math.abs(Math.sin(step * 0.5)) * 40000);

      bars.push({
        time: Math.floor(new Date(`${date}T${time}Z`).getTime() / 1000),
        open,
        high,
        low,
        close,
        volume,
      });
      currentPrice = close;
    }
  }

  return bars;
}

export const ChartWidget: React.FC<WidgetComponentProps<ChartWidgetSettings>> = ({
  settings,
  onUpdateSettings,
}) => {
  const [activeIndicators, setActiveIndicators] = useState<ChartIndicatorConfig[]>([
    {
      id: "sma-20",
      name: "SMA 20",
      type: "SMA",
      pane: "overlay",
      color: "#ffaa00",
      params: { period: 20 },
    },
    {
      id: "rsi-14",
      name: "RSI 14",
      type: "RSI",
      pane: "subpane",
      color: "#a855f7",
      params: { period: 14 },
    },
  ]);

  const [selectedTimeframe, setSelectedTimeframe] = useState<string>(settings.timeframe || "5m");

  const bars = useMemo(
    () => generateMockBars(settings.symbol || "RELIANCE", selectedTimeframe),
    [settings.symbol, selectedTimeframe]
  );

  const toggleIndicator = (ind: ChartIndicatorConfig) => {
    if (activeIndicators.some((i) => i.id === ind.id)) {
      setActiveIndicators(activeIndicators.filter((i) => i.id !== ind.id));
    } else {
      setActiveIndicators([...activeIndicators, ind]);
    }
  };

  const isIndActive = (id: string) => activeIndicators.some((i) => i.id === id);

  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column" }}>
      {/* Chart Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--spacing-1) var(--spacing-3)",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <span style={{ fontWeight: "bold", color: "var(--color-primary)" }}>
            {settings.symbol || "RELIANCE"}
          </span>

          <div style={{ display: "flex", gap: "2px", borderLeft: "1px solid var(--border-default)", paddingLeft: "var(--spacing-2)" }}>
            {["1m", "5m", "15m", "1h", "1d"].map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => {
                  setSelectedTimeframe(tf);
                  if (onUpdateSettings) onUpdateSettings({ timeframe: tf as any });
                }}
                style={{
                  padding: "2px 6px",
                  background: selectedTimeframe === tf ? "var(--bg-active)" : "transparent",
                  color: selectedTimeframe === tf ? "var(--color-primary)" : "var(--text-muted)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  fontWeight: selectedTimeframe === tf ? 600 : 400,
                  fontSize: "0.6875rem",
                }}
              >
                {tf}
              </button>
            ))}
          </div>

          <span
            style={{
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-elevated)",
              color: "var(--text-muted)",
              fontSize: "0.625rem",
              border: "1px solid var(--border-subtle)",
            }}
          >
            Sample Historical Data
          </span>
        </div>

        {/* Indicator Toggles */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            onClick={() =>
              toggleIndicator({
                id: "sma-20",
                name: "SMA 20",
                type: "SMA",
                pane: "overlay",
                color: "#ffaa00",
                params: { period: 20 },
              })
            }
            style={{
              padding: "2px 6px",
              background: isIndActive("sma-20") ? "rgba(255, 170, 0, 0.2)" : "transparent",
              color: isIndActive("sma-20") ? "#ffaa00" : "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "0.6875rem",
              fontWeight: 600,
            }}
          >
            SMA 20
          </button>

          <button
            type="button"
            onClick={() =>
              toggleIndicator({
                id: "ema-50",
                name: "EMA 50",
                type: "EMA",
                pane: "overlay",
                color: "#00d2ff",
                params: { period: 50 },
              })
            }
            style={{
              padding: "2px 6px",
              background: isIndActive("ema-50") ? "rgba(0, 210, 255, 0.2)" : "transparent",
              color: isIndActive("ema-50") ? "#00d2ff" : "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "0.6875rem",
              fontWeight: 600,
            }}
          >
            EMA 50
          </button>

          <button
            type="button"
            onClick={() =>
              toggleIndicator({
                id: "rsi-14",
                name: "RSI 14",
                type: "RSI",
                pane: "subpane",
                color: "#a855f7",
                params: { period: 14 },
              })
            }
            style={{
              padding: "2px 6px",
              background: isIndActive("rsi-14") ? "rgba(168, 85, 247, 0.2)" : "transparent",
              color: isIndActive("rsi-14") ? "#a855f7" : "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "0.6875rem",
              fontWeight: 600,
            }}
          >
            RSI 14
          </button>

          <button
            type="button"
            onClick={() =>
              toggleIndicator({
                id: "macd",
                name: "MACD",
                type: "MACD",
                pane: "subpane",
                color: "#00d2ff",
                params: { fast: 12, slow: 26, signal: 9 },
              })
            }
            style={{
              padding: "2px 6px",
              background: isIndActive("macd") ? "rgba(0, 210, 255, 0.2)" : "transparent",
              color: isIndActive("macd") ? "#00d2ff" : "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "0.6875rem",
              fontWeight: 600,
            }}
          >
            MACD
          </button>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div style={{ flex: 1, minHeight: "220px", position: "relative" }}>
        <ChartContainer
          bars={bars}
          indicators={activeIndicators}
          showSessionBreaks={settings.showSessionBreaks !== false}
          showVolume={settings.showVolume !== false}
        />
      </div>
    </div>
  );
};

export const chartDefinition: WidgetDefinition<ChartWidgetSettings> = {
  id: "chart",
  title: "Candlestick Chart",
  description: "Multi-pane candlestick chart with indicators and session breaks.",
  category: "chart",
  icon: "📈",
  defaultWidth: 500,
  defaultHeight: 380,
  schema: {
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
  component: ChartWidget,
};
