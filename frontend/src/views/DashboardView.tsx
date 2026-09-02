import React from "react";

export const DashboardView: React.FC = () => {
  return (
    <div style={{ padding: "var(--spacing-6)", display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginBottom: "var(--spacing-1)" }}>
          Executive Dashboard
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Real-time terminal telemetry, active universe monitor, and quick launch pad.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "var(--spacing-4)",
        }}
      >
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: "var(--spacing-4)",
          }}
        >
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)", textTransform: "uppercase" }}>
            Active Strategies
          </div>
          <div style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginTop: "var(--spacing-2)" }}>
            3 Backtests Ready
          </div>
          <div style={{ color: "var(--color-up)", fontSize: "var(--font-size-xs)", marginTop: "var(--spacing-1)" }}>
            Engine Status: Normal
          </div>
        </div>

        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: "var(--spacing-4)",
          }}
        >
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)", textTransform: "uppercase" }}>
            Warehouse Partitions
          </div>
          <div style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginTop: "var(--spacing-2)" }}>
            DuckDB / Parquet
          </div>
          <div style={{ color: "var(--color-info)", fontSize: "var(--font-size-xs)", marginTop: "var(--spacing-1)" }}>
            Immutable store active
          </div>
        </div>

        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: "var(--spacing-4)",
          }}
        >
          <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)", textTransform: "uppercase" }}>
            Market Connectivity
          </div>
          <div style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginTop: "var(--spacing-2)" }}>
            Dhan HQ API
          </div>
          <div style={{ color: "var(--color-up)", fontSize: "var(--font-size-xs)", marginTop: "var(--spacing-1)" }}>
            Rate limiter configured
          </div>
        </div>
      </div>
    </div>
  );
};
