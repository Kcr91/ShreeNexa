import React, { useEffect, useState } from "react";

import { apiClient, ApiError } from "../api/client";

/**
 * Point-in-Time Screener — pick (or create) a saved screener, run it across the
 * F&O universe, and review matches. Wired to GET/POST /api/v1/screener/configs
 * and POST /api/v1/screener/run/{config_id}.
 */

interface ScreenerConfig {
  id: number;
  name: string;
  description: string | null;
  universe_filter: string;
  condition_tree: Record<string, unknown>;
  is_strategy_mode: boolean;
}

interface MatchedStock {
  symbol: string;
  display_name: string | null;
  segments: string[];
  last_close: number;
  change_pct: number;
  volume: number;
  conditions_met: string[];
}

interface ScreenerRun {
  run_id: number | null;
  config_name: string;
  universe: string;
  total_scanned: number;
  total_matched: number;
  duration_ms: number;
  results: MatchedStock[];
}

const panelStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-surface)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
};
const panelHeadStyle: React.CSSProperties = {
  padding: "var(--spacing-3) var(--spacing-4)",
  borderBottom: "1px solid var(--border-subtle)",
  fontWeight: 600,
  fontSize: "var(--font-size-sm)",
};
const chipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "0.4rem",
  background: "var(--bg-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-full)",
  padding: "0.3rem 0.65rem",
  fontSize: "var(--font-size-xs)",
  color: "var(--text-secondary)",
};

const SAMPLE_CONFIG = {
  name: "Open=High Sector Losers",
  description: "Top-2 loser sectors, open == high, RSI(14) < 40 at market open.",
  universe_filter: "NIFTY50",
  condition_tree: {
    logic: "AND",
    conditions: [
      { indicator: "RSI", timeframe: "daily", operator: "<", value: 40, period: 14 },
    ],
  },
  is_strategy_mode: false,
};

export const ScreenerView: React.FC = () => {
  const [configs, setConfigs] = useState<ScreenerConfig[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [run, setRun] = useState<ScreenerRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConfigs = async (): Promise<ScreenerConfig[]> => {
    const list = await apiClient.request<ScreenerConfig[]>("/api/v1/screener/configs");
    setConfigs(list);
    if (list.length > 0 && selectedId === null) setSelectedId(list[0].id);
    return list;
  };

  useEffect(() => {
    let cancelled = false;
    apiClient
      .request<ScreenerConfig[]>("/api/v1/screener/configs")
      .then((list) => {
        if (cancelled) return;
        setConfigs(list);
        if (list.length > 0) setSelectedId(list[0].id);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load saved screeners.");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createSample = async (): Promise<void> => {
    setCreating(true);
    setError(null);
    try {
      const created = await apiClient.request<ScreenerConfig>("/api/v1/screener/configs", {
        method: "POST",
        body: JSON.stringify(SAMPLE_CONFIG),
      });
      await loadConfigs();
      setSelectedId(created.id);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "Could not create a sample screener.");
    } finally {
      setCreating(false);
    }
  };

  const runScan = async (): Promise<void> => {
    if (selectedId === null) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.request<ScreenerRun>(`/api/v1/screener/run/${selectedId}`, {
        method: "POST",
      });
      setRun(res);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "Screener run failed.");
    } finally {
      setLoading(false);
    }
  };

  const selected = configs.find((c) => c.id === selectedId) ?? null;
  const conditions = Array.isArray(selected?.condition_tree?.conditions)
    ? (selected!.condition_tree.conditions as Array<Record<string, unknown>>)
    : [];

  return (
    <div style={{ padding: "var(--spacing-5)", display: "flex", flexDirection: "column", gap: "var(--spacing-5)", maxWidth: "1180px" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", margin: "0 0 var(--spacing-1)" }}>Point-in-Time Screener</h2>
        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Scan the F&amp;O universe at a historical timestamp with no survivorship bias — wired to{" "}
          <code style={{ fontFamily: "var(--font-family-mono)" }}>/api/v1/screener/*</code>.
        </p>
      </div>

      {error && (
        <div style={{ color: "var(--color-down)", background: "var(--color-down-bg)", border: "1px solid rgba(248,81,73,0.35)", borderRadius: "var(--radius-md)", padding: "var(--spacing-3)", fontSize: "var(--font-size-sm)" }}>
          {error}
        </div>
      )}

      <div style={panelStyle}>
        <div style={panelHeadStyle}>Scan Criteria</div>
        <div style={{ padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
          {configs.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)", alignItems: "flex-start" }}>
              <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>No saved screeners yet. Create a sample to try a scan.</div>
              <button onClick={createSample} disabled={creating} style={{ background: "var(--color-primary)", color: "var(--text-inverse)", fontWeight: 700, border: "none", borderRadius: "var(--radius-md)", padding: "0.5rem 1.1rem", fontSize: "var(--font-size-sm)", cursor: "pointer", opacity: creating ? 0.6 : 1 }}>
                {creating ? "Creating…" : "+ Create sample screener"}
              </button>
            </div>
          ) : (
            <>
              <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
                <select value={selectedId ?? ""} onChange={(e) => { setSelectedId(Number(e.target.value)); setRun(null); }} style={{ backgroundColor: "var(--bg-primary)", border: "1px solid var(--border-default)", color: "var(--text-primary)", borderRadius: "var(--radius-md)", padding: "0.42rem 0.55rem", fontSize: "var(--font-size-sm)", minWidth: "240px" }}>
                  {configs.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <button onClick={createSample} disabled={creating} style={{ background: "transparent", border: "1px solid var(--border-default)", color: "var(--text-secondary)", borderRadius: "var(--radius-md)", padding: "0.4rem 0.7rem", fontSize: "var(--font-size-xs)", cursor: "pointer" }}>+ Sample</button>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                <span style={chipStyle}>Universe: <b style={{ color: "var(--text-primary)" }}>{selected?.universe_filter}</b></span>
                {conditions.length === 0 && <span style={chipStyle}>No conditions defined</span>}
                {conditions.map((c, i) => (
                  <span key={i} style={{ ...chipStyle, borderColor: "rgba(88,166,255,0.45)", background: "var(--color-primary-bg)", color: "var(--text-primary)" }}>
                    {String(c.indicator ?? "?")}({String(c.period ?? "")}) {String(c.operator ?? "")} {String(c.value ?? "")}
                  </span>
                ))}
              </div>

              <div>
                <button onClick={runScan} disabled={loading || selectedId === null} style={{ background: "var(--color-up)", color: "var(--text-inverse)", fontWeight: 700, border: "none", borderRadius: "var(--radius-md)", padding: "0.5rem 1.1rem", fontSize: "var(--font-size-sm)", cursor: "pointer", opacity: loading ? 0.6 : 1 }}>
                  {loading ? "Scanning…" : "▶ Run Scan"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {run && (
        <div style={panelStyle}>
          <div style={panelHeadStyle}>
            Matches{" "}
            <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
              · {run.total_matched} of {run.total_scanned} scanned · {run.duration_ms} ms
            </span>
          </div>
          {run.results.length === 0 ? (
            <div style={{ padding: "var(--spacing-5)", color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
              Scan completed in {run.duration_ms} ms but matched 0 symbols. In this environment the warehouse has no 1-minute history yet — populate it via <b>Data Engine → Sync</b> to get live matches.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
                <thead>
                  <tr>
                    {["Symbol", "Segments", "% Chg", "LTP", "Volume", "Conditions Met"].map((h, i) => (
                      <th key={h} style={{ textAlign: i >= 2 && i <= 4 ? "right" : "left", fontSize: "var(--font-size-xs)", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-default)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {run.results.map((s) => (
                    <tr key={s.symbol}>
                      <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", fontFamily: "var(--font-family-mono)" }}>{s.symbol}</td>
                      <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>{s.segments.join(", ") || "—"}</td>
                      <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", textAlign: "right", fontVariantNumeric: "tabular-nums", color: s.change_pct >= 0 ? "var(--color-up)" : "var(--color-down)" }}>{s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(2)}%</td>
                      <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", textAlign: "right", fontVariantNumeric: "tabular-nums", fontFamily: "var(--font-family-mono)" }}>{s.last_close.toFixed(2)}</td>
                      <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{s.volume.toLocaleString("en-IN")}</td>
                      <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>{s.conditions_met.join(", ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
