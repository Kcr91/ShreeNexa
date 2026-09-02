import React from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";

export interface WatchlistSettings {
  universeName: string;
  refreshIntervalSec: number;
}

const mockSymbols = [
  { symbol: "RELIANCE", ltp: 2980.50, changePct: 1.25 },
  { symbol: "TCS", ltp: 4210.00, changePct: -0.45 },
  { symbol: "HDFCBANK", ltp: 1640.20, changePct: 0.80 },
  { symbol: "INFY", ltp: 1890.10, changePct: -1.10 },
  { symbol: "ICICIBANK", ltp: 1215.30, changePct: 1.65 },
];

export const WatchlistWidget: React.FC<WidgetComponentProps<WatchlistSettings>> = ({
  settings,
}) => {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
          color: "var(--text-muted)",
          fontWeight: "bold",
        }}
      >
        <span>Universe: {settings.universeName || "NIFTY 50"}</span>
        <span>{mockSymbols.length} Symbols</span>
      </div>

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {mockSymbols.map((item) => {
          const isUp = item.changePct >= 0;
          return (
            <div
              key={item.symbol}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "var(--spacing-2) var(--spacing-3)",
                borderBottom: "1px solid var(--border-subtle)",
                fontSize: "var(--font-size-sm)",
              }}
            >
              <span style={{ fontWeight: 600 }}>{item.symbol}</span>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
                <span style={{ fontFamily: "var(--font-family-mono)" }}>₹{item.ltp.toFixed(2)}</span>
                <span
                  style={{
                    fontFamily: "var(--font-family-mono)",
                    fontSize: "var(--font-size-xs)",
                    padding: "2px 6px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: isUp ? "var(--color-up-bg)" : "var(--color-down-bg)",
                    color: isUp ? "var(--color-up)" : "var(--color-down)",
                    fontWeight: 600,
                  }}
                >
                  {isUp ? "+" : ""}{item.changePct.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const watchlistDefinition: WidgetDefinition<WatchlistSettings> = {
  id: "watchlist",
  title: "Market Watchlist",
  description: "Live symbol quotes and percentage changes.",
  category: "watchlist",
  icon: "📋",
  defaultWidth: 320,
  defaultHeight: 360,
  schema: {
    fields: [
      {
        name: "universeName",
        label: "Universe Name",
        type: "select",
        default: "NIFTY 50",
        options: [
          { label: "NIFTY 50", value: "NIFTY 50" },
          { label: "NIFTY BANK", value: "NIFTY BANK" },
          { label: "NIFTY IT", value: "NIFTY IT" },
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
  component: WatchlistWidget,
};
