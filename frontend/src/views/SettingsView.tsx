import React from "react";
import { useAuth } from "../auth/AuthContext";

export const SettingsView: React.FC = () => {
  const { user } = useAuth();

  return (
    <div style={{ padding: "var(--spacing-6)", display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", marginBottom: "var(--spacing-1)" }}>
          Terminal Settings & Integrations
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Manage local developer authentication, Dhan feed rate limits, and system parameters.
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
        <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: 600, marginBottom: "var(--spacing-4)" }}>
          Active Session Information
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "var(--spacing-3)", fontSize: "var(--font-size-sm)" }}>
          <div style={{ color: "var(--text-muted)" }}>Authenticated User:</div>
          <div style={{ fontWeight: 600 }}>{user.username}</div>

          <div style={{ color: "var(--text-muted)" }}>Role:</div>
          <div>{user.role}</div>

          <div style={{ color: "var(--text-muted)" }}>Dhan Client ID:</div>
          <div style={{ fontFamily: "var(--font-family-mono)" }}>{user.dhanClientId}</div>

          <div style={{ color: "var(--text-muted)" }}>Execution Mode:</div>
          <div>Paper / Backtest Only (Live gated behind Epic 12)</div>
        </div>
      </div>
    </div>
  );
};
