import React from "react";
import { MarketplaceStrategy } from "./types";

interface TearSheetModalProps {
  strategy: MarketplaceStrategy;
  isOpen: boolean;
  onClose: () => void;
  onClone: (strategy: MarketplaceStrategy) => void;
}

export const TearSheetModal: React.FC<TearSheetModalProps> = ({
  strategy,
  isOpen,
  onClose,
  onClone,
}) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="tearsheet-modal-title"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 10000,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          width: "600px",
          maxWidth: "92vw",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.6)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "var(--spacing-3) var(--spacing-4)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
              <h2 id="tearsheet-modal-title" style={{ fontSize: "var(--font-size-md)", fontWeight: 700, margin: 0 }}>
                {strategy.title}
              </h2>
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-primary)",
                  color: "var(--text-inverse)",
                  fontSize: "0.625rem",
                  fontWeight: 700,
                }}
              >
                {strategy.assetClass}
              </span>
            </div>
            <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", marginTop: "2px" }}>
              By {strategy.author.name} ({strategy.author.handle}) • {strategy.timeframe} timeframe
            </div>
          </div>

          <button
            type="button"
            aria-label="Close modal"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "1.25rem",
            }}
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: "var(--spacing-4)", overflowY: "auto", display: "flex", flexDirection: "column", gap: "var(--spacing-4)" }}>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", margin: 0 }}>
            {strategy.description}
          </p>

          {/* Performance Tear Sheet Grid */}
          <div>
            <strong style={{ fontSize: "var(--font-size-xs)", textTransform: "uppercase", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              Audited Performance Scorecard
            </strong>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--spacing-2)" }}>
              <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>CAGR Return</span>
                <strong style={{ fontSize: "var(--font-size-md)", color: "var(--color-up)" }}>+{strategy.performance.cagrPct}%</strong>
              </div>
              <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Sharpe Ratio</span>
                <strong style={{ fontSize: "var(--font-size-md)", color: "var(--color-primary)" }}>{strategy.performance.sharpeRatio}</strong>
              </div>
              <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Max Drawdown</span>
                <strong style={{ fontSize: "var(--font-size-md)", color: "var(--color-down)" }}>-{strategy.performance.maxDrawdownPct}%</strong>
              </div>
              <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Win Rate</span>
                <strong style={{ fontSize: "var(--font-size-md)" }}>{strategy.performance.winRatePct}%</strong>
              </div>
              <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Profit Factor</span>
                <strong style={{ fontSize: "var(--font-size-md)" }}>{strategy.performance.profitFactor}</strong>
              </div>
              <div style={{ backgroundColor: "var(--bg-active)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Total Executed Trades</span>
                <strong style={{ fontSize: "var(--font-size-md)" }}>{strategy.performance.totalTrades}</strong>
              </div>
            </div>
          </div>

          {/* StrategyIR Rules Definition */}
          <div>
            <strong style={{ fontSize: "var(--font-size-xs)", textTransform: "uppercase", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              Strategy Logic Definition (StrategyIR)
            </strong>
            <pre
              data-testid="tearsheet-ir-code"
              style={{
                backgroundColor: "var(--bg-active)",
                padding: "var(--spacing-3)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.6875rem",
                fontFamily: "var(--font-family-mono)",
                color: "var(--text-secondary)",
                overflow: "auto",
                maxHeight: "180px",
                margin: 0,
              }}
            >
              {JSON.stringify(strategy.strategyIR, null, 2)}
            </pre>
          </div>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: "var(--spacing-3) var(--spacing-4)",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "flex-end",
            gap: "var(--spacing-2)",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "var(--spacing-2) var(--spacing-3)",
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Close
          </button>

          <button
            type="button"
            data-testid="tearsheet-clone-btn"
            onClick={() => {
              onClone(strategy);
              onClose();
            }}
            style={{
              padding: "var(--spacing-2) var(--spacing-4)",
              backgroundColor: "var(--color-primary)",
              color: "var(--text-inverse)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            ⚡ Clone Strategy to Workspace
          </button>
        </div>
      </div>
    </div>
  );
};
