import React from "react";

export const ScreenerView: React.FC = () => {
  return (
    <div style={{ padding: "var(--spacing-6)", display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginBottom: "var(--spacing-1)" }}>
          Point-in-Time Screener
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Scan NIFTY 50, NIFTY 500, and F&O universes with historical point-in-time membership and survivorship-bias protection.
        </p>
      </div>

      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          padding: "var(--spacing-6)",
        }}
      >
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)" }}>
          Screener persistence and scheduling engine ready. Screen results route directly to watchlists and backtest universes.
        </p>
      </div>
    </div>
  );
};
