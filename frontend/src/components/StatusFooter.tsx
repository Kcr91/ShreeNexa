import React from "react";
import { FooterClock } from "./FooterClock";

export const StatusFooter: React.FC = () => {
  return (
    <footer
      role="contentinfo"
      style={{
        height: "var(--footer-height)",
        backgroundColor: "var(--bg-secondary)",
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 var(--spacing-4)",
        fontSize: "var(--font-size-xs)",
        color: "var(--text-muted)",
        userSelect: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-4)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <span style={{ color: "var(--color-up)" }}>●</span>
          <span>API: 127.0.0.1:8000</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <span style={{ color: "var(--color-up)" }}>●</span>
          <span>Engine: Ready</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <span style={{ color: "var(--color-warning)" }}>●</span>
          <span>Feedd: Standby (0/5)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <span style={{ color: "var(--color-up)" }}>●</span>
          <span>Worker: Idle</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
        <span>Workspace: F:\ShreeNexa</span>
        <span>Environment: Paper / Dev Mode</span>
        <FooterClock />
        <span style={{ color: "var(--text-secondary)" }}>v1.1</span>
      </div>
    </footer>
  );
};
