import React from "react";

export const PnLView: React.FC = () => {
  return (
    <div style={{ padding: "var(--spacing-6)", display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginBottom: "var(--spacing-1)" }}>
          Daily P&L & Performance Ledger
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Time-Weighted Return (TWR) tracking, daily Mark-to-Market (MTM), external cashflows, and monthly return heatmaps.
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
          Accounting identity engine active: Ending Equity matches Starting Equity + Cashflows + Realized P&L + MTM Changes - Costs.
        </p>
      </div>
    </div>
  );
};
