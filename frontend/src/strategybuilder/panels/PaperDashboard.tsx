import React from "react";
import {
  StrategyDeployment,
  PaperPosition,
  PaperFill,
  PortfolioSummary,
  getPaperDeployment,
  getPaperPositions,
  getPaperFills,
  getPortfolioSummary,
  paperLifecycle,
} from "../paperDeployService";

interface Props {
  isOpen: boolean;
  deploymentId: string | null;
  accountId: string;
  onClose: () => void;
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0,0,0,0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: "16px",
};

const modalStyle: React.CSSProperties = {
  width: "min(960px, 100%)",
  maxHeight: "90vh",
  backgroundColor: "var(--bg-surface)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-md, 6px)",
  padding: "var(--spacing-3)",
  display: "flex",
  flexDirection: "column",
  gap: "var(--spacing-2)",
  overflow: "hidden",
};

const btnStyle: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: "0.6875rem",
  cursor: "pointer",
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
};

const stateColors: Record<StrategyDeployment["state"], string> = {
  CREATED: "#94a3b8",
  RUNNING: "var(--color-up)",
  PAUSED: "#eab308",
  STOPPED: "var(--color-down)",
  FAILED: "var(--color-down)",
};

export const PaperDashboard: React.FC<Props> = ({ isOpen, deploymentId, accountId, onClose }) => {
  const [deployment, setDeployment] = React.useState<StrategyDeployment | null>(null);
  const [positions, setPositions] = React.useState<PaperPosition[]>([]);
  const [fills, setFills] = React.useState<PaperFill[]>([]);
  const [summary, setSummary] = React.useState<PortfolioSummary | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!deploymentId) return;
    try {
      const [dep, pos, fls, sm] = await Promise.all([
        getPaperDeployment(deploymentId),
        getPaperPositions(accountId).catch(() => []),
        getPaperFills(accountId).catch(() => []),
        getPortfolioSummary(accountId).catch(() => null),
      ]);
      setDeployment(dep);
      setPositions(pos);
      setFills(fls);
      setSummary(sm);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load deployment");
    }
  }, [deploymentId, accountId]);

  React.useEffect(() => {
    if (!isOpen || !deploymentId) return;
    refresh();
    const id = setInterval(refresh, 7_000);
    return () => clearInterval(id);
  }, [isOpen, deploymentId, refresh]);

  if (!isOpen) return null;

  const act = async (op: "pause" | "resume" | "stop") => {
    if (!deploymentId) return;
    setBusy(true);
    try {
      const updated = await paperLifecycle(deploymentId, op);
      setDeployment(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${op}`);
    } finally {
      setBusy(false);
    }
  };

  const totalPnl = summary?.total_pnl ?? 0;
  const todayFills = fills.filter((f) => {
    const d = new Date(f.timestamp);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  });

  return (
    <div style={overlayStyle} data-testid="paper-dashboard" role="dialog" aria-label="Paper Trading Dashboard">
      <div style={modalStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <strong>{deployment?.strategy_name ?? "Paper Dashboard"}</strong>
            {deployment && (
              <span
                data-testid="deployment-state"
                style={{
                  padding: "1px 8px",
                  borderRadius: "999px",
                  backgroundColor: "var(--bg-active)",
                  color: stateColors[deployment.state],
                  fontSize: "0.625rem",
                  fontWeight: 700,
                }}
              >
                {deployment.state}
              </span>
            )}
          </div>
          <div style={{ display: "flex", gap: "6px" }}>
            {deployment?.state === "RUNNING" && (
              <button type="button" onClick={() => act("pause")} disabled={busy} style={btnStyle}>Pause</button>
            )}
            {deployment?.state === "PAUSED" && (
              <button type="button" onClick={() => act("resume")} disabled={busy} style={btnStyle}>Resume</button>
            )}
            {deployment?.state !== "STOPPED" && (
              <button type="button" onClick={() => act("stop")} disabled={busy} style={{ ...btnStyle, color: "var(--color-down)" }}>Stop</button>
            )}
            <button type="button" onClick={onClose} style={btnStyle} aria-label="Close">✕</button>
          </div>
        </div>

        {error && (
          <div data-testid="paper-dashboard-error" style={{ color: "var(--color-down)", fontSize: "0.6875rem" }}>
            {error}
          </div>
        )}

        {/* Summary cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "6px" }}>
          <SummaryCard label="Equity" value={summary ? `₹${summary.equity.toLocaleString("en-IN")}` : "—"} />
          <SummaryCard label="Total P&L" value={summary ? `₹${totalPnl.toLocaleString("en-IN")}` : "—"} color={totalPnl >= 0 ? "var(--color-up)" : "var(--color-down)"} />
          <SummaryCard label="Realized" value={summary ? `₹${summary.realized_pnl.toLocaleString("en-IN")}` : "—"} />
          <SummaryCard label="Unrealized" value={summary ? `₹${summary.unrealized_pnl.toLocaleString("en-IN")}` : "—"} />
          <SummaryCard label="Trades" value={String(fills.length)} />
          <SummaryCard label="Open Positions" value={String(positions.length)} />
        </div>

        {/* Open positions */}
        <div style={{ overflow: "auto", maxHeight: "180px", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.6875rem" }} data-testid="positions-table">
            <thead>
              <tr style={{ color: "var(--text-muted)", backgroundColor: "var(--bg-active)" }}>
                <th style={{ textAlign: "left", padding: "3px 6px" }}>Symbol</th>
                <th style={{ textAlign: "right", padding: "3px 6px" }}>Qty</th>
                <th style={{ textAlign: "right", padding: "3px 6px" }}>Avg Price</th>
                <th style={{ textAlign: "right", padding: "3px 6px" }}>Last</th>
                <th style={{ textAlign: "right", padding: "3px 6px" }}>Unrealized P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 && (
                <tr><td colSpan={5} style={{ padding: "6px", color: "var(--text-muted)" }}>No open positions.</td></tr>
              )}
              {positions.map((p) => (
                <tr key={`${p.security_id}:${p.exchange_segment}`}>
                  <td style={{ padding: "3px 6px" }}>{p.symbol || p.security_id}</td>
                  <td style={{ padding: "3px 6px", textAlign: "right" }}>{p.quantity}</td>
                  <td style={{ padding: "3px 6px", textAlign: "right" }}>{p.average_price.toFixed(2)}</td>
                  <td style={{ padding: "3px 6px", textAlign: "right" }}>{p.current_price.toFixed(2)}</td>
                  <td style={{ padding: "3px 6px", textAlign: "right", color: p.unrealized_pnl >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                    {p.unrealized_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Today's trades */}
        <div style={{ overflow: "auto", maxHeight: "180px", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.6875rem" }} data-testid="fills-table">
            <thead>
              <tr style={{ color: "var(--text-muted)", backgroundColor: "var(--bg-active)" }}>
                <th style={{ textAlign: "left", padding: "3px 6px" }}>Time</th>
                <th style={{ textAlign: "left", padding: "3px 6px" }}>Symbol</th>
                <th style={{ textAlign: "left", padding: "3px 6px" }}>Side</th>
                <th style={{ textAlign: "right", padding: "3px 6px" }}>Qty</th>
                <th style={{ textAlign: "right", padding: "3px 6px" }}>Price</th>
              </tr>
            </thead>
            <tbody>
              {todayFills.length === 0 && (
                <tr><td colSpan={5} style={{ padding: "6px", color: "var(--text-muted)" }}>No trades today.</td></tr>
              )}
              {todayFills.map((f) => (
                <tr key={f.fill_id}>
                  <td style={{ padding: "3px 6px" }}>{f.timestamp.slice(11, 19)}</td>
                  <td style={{ padding: "3px 6px" }}>{f.security_id}</td>
                  <td style={{ padding: "3px 6px", color: f.side === "BUY" ? "var(--color-up)" : "var(--color-down)" }}>{f.side}</td>
                  <td style={{ padding: "3px 6px", textAlign: "right" }}>{f.quantity}</td>
                  <td style={{ padding: "3px 6px", textAlign: "right" }}>{f.price.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
            Auto-refreshing every 7s · Paper mode only
          </span>
          <button
            type="button"
            disabled
            data-testid="btn-promote-live"
            title="Live trading activation requires Epic 12 authorization"
            style={{ ...btnStyle, opacity: 0.5, cursor: "not-allowed" }}
          >
            Promote to Live (requires Epic 12)
          </button>
        </div>
      </div>
    </div>
  );
};

const SummaryCard: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "6px 10px" }}>
    <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>{label}</div>
    <div style={{ fontSize: "0.875rem", fontWeight: 700, color: color || "var(--text-primary)" }}>{value}</div>
  </div>
);
