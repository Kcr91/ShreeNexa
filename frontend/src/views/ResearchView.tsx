import React from "react";

export const ResearchView: React.FC = () => {
  return (
    <div style={{ padding: "var(--spacing-6)", display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginBottom: "var(--spacing-1)" }}>
          Strategy Research Lab
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          StrategyIR visual configuration, multi-asset backtest runner, Monte Carlo, and Walk-Forward Analysis.
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
        <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: 600, marginBottom: "var(--spacing-3)" }}>
          Execution Engine Core Available
        </h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", lineHeight: "1.6" }}>
          The backend backtester supports Stock, Multi-Leg Options, Continuous Futures, and Capital-Allocated Portfolio runners with Indian regulatory cost modeling (STT, GST, Stamp Duty, SEBI turnover) and Next-Bar Open deterministic execution.
        </p>
      </div>
    </div>
  );
};
