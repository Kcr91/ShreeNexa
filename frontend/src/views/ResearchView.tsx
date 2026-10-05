import React, { useEffect, useMemo, useState } from "react";

import { apiClient, ApiError } from "../api/client";

/**
 * Strategy Lab — configure and run a stock backtest against the warehouse and
 * review results. Wired to GET /api/v1/strategy/templates and
 * POST /api/v1/backtests/run (BacktestConfig -> BacktestResult).
 */

interface StrategyTemplate {
  name: string;
  timeframe?: string;
  strategy_type?: string;
  universe?: { type?: string; index_name?: string };
  [key: string]: unknown;
}

interface BacktestMetrics {
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  cagr_pct: number;
  total_pnl: number;
  total_costs: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  profit_factor: number;
}

interface EquityPoint {
  timestamp: string;
  equity: number;
}

interface Fill {
  fill_id: string;
  security_id: string;
  side: string;
  quantity: number;
  price: number;
  timestamp: string;
  brokerage: number;
  taxes: number;
  slippage: number;
}

interface BacktestResult {
  backtest_id: string;
  strategy_name: string;
  metrics: BacktestMetrics;
  trades: Fill[];
  equity_curve: EquityPoint[];
  engine_commit: string;
}

const inr = (n: number): string =>
  "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
const pct = (n: number): string => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
const toneColor = (n: number): string => (n >= 0 ? "var(--color-up)" : "var(--color-down)");

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
const labelStyle: React.CSSProperties = {
  fontSize: "var(--font-size-xs)",
  color: "var(--text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};
const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-primary)",
  border: "1px solid var(--border-default)",
  color: "var(--text-primary)",
  borderRadius: "var(--radius-md)",
  padding: "0.42rem 0.55rem",
  fontSize: "var(--font-size-sm)",
  fontFamily: "inherit",
  width: "100%",
};

const EquityChart: React.FC<{ points: EquityPoint[] }> = ({ points }) => {
  const geom = useMemo(() => {
    if (points.length < 2) return null;
    const vals = points.map((p) => p.equity);
    const min = Math.min(...vals) * 0.998;
    const max = Math.max(...vals) * 1.002;
    const W = 720;
    const H = 240;
    const PL = 64;
    const PR = 14;
    const PT = 12;
    const PB = 26;
    const x = (i: number): number => PL + (i / (points.length - 1)) * (W - PL - PR);
    const y = (v: number): number => PT + (1 - (v - min) / (max - min || 1)) * (H - PT - PB);
    let line = "";
    let area = `M ${x(0)} ${y(vals[0])} `;
    vals.forEach((v, i) => {
      line += (i ? "L" : "M") + x(i) + " " + y(v) + " ";
      area += `L ${x(i)} ${y(v)} `;
    });
    area += `L ${x(points.length - 1)} ${H - PB} L ${x(0)} ${H - PB} Z`;
    const ticks = [min, (min + max) / 2, max];
    const up = vals[vals.length - 1] >= vals[0];
    return { W, H, PL, PR, PB, x, y, line, area, ticks, up, last: vals.length - 1, lastVal: vals[vals.length - 1] };
  }, [points]);

  if (!geom) {
    return (
      <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)", padding: "var(--spacing-4)" }}>
        No equity points returned for this run.
      </div>
    );
  }
  const stroke = geom.up ? "var(--color-up)" : "var(--color-down)";
  return (
    <svg viewBox={`0 0 ${geom.W} ${geom.H}`} role="img" aria-label="Backtest equity curve" style={{ display: "block", width: "100%", height: "auto" }}>
      <defs>
        <linearGradient id="eqfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={stroke} stopOpacity="0.26" />
          <stop offset="1" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      {geom.ticks.map((t, i) => (
        <g key={i}>
          <line x1={geom.PL} y1={geom.y(t)} x2={geom.W - geom.PR} y2={geom.y(t)} stroke="var(--border-subtle)" strokeWidth="1" />
          <text x={geom.PL - 8} y={geom.y(t) + 4} textAnchor="end" fill="var(--text-muted)" fontSize="11" fontFamily="var(--font-family-mono)">
            {"₹" + (t / 100000).toFixed(2) + "L"}
          </text>
        </g>
      ))}
      <path d={geom.area} fill="url(#eqfill)" />
      <path d={geom.line} fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round" />
      <circle cx={geom.x(geom.last)} cy={geom.y(geom.lastVal)} r="3.5" fill={stroke} />
    </svg>
  );
};

const Tile: React.FC<{ k: string; v: string; tone?: string }> = ({ k, v, tone }) => (
  <div style={{ ...panelStyle, borderRadius: "var(--radius-md)", padding: "var(--spacing-3) var(--spacing-4)" }}>
    <div style={labelStyle}>{k}</div>
    <div style={{ fontSize: "var(--font-size-xl)", fontWeight: 700, marginTop: "0.25rem", color: tone, fontVariantNumeric: "tabular-nums" }}>{v}</div>
  </div>
);

export const ResearchView: React.FC = () => {
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [selected, setSelected] = useState(0);
  const [from, setFrom] = useState("2024-10-01");
  const [to, setTo] = useState("2025-09-30");
  const [capital, setCapital] = useState(1000000);
  const [slippage, setSlippage] = useState("percent");
  const [fillTiming, setFillTiming] = useState("NEXT_BAR_OPEN");

  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .request<StrategyTemplate[]>("/api/v1/strategy/templates")
      .then((tpls) => {
        if (!cancelled) setTemplates(tpls);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load strategy templates.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runBacktest = async (): Promise<void> => {
    const template = templates[selected];
    if (!template) return;
    setLoading(true);
    setError(null);
    try {
      const config = {
        strategy: template,
        start_date: `${from}T00:00:00Z`,
        end_date: `${to}T00:00:00Z`,
        initial_cash: capital,
        fill_timing: fillTiming,
        slippage_model: slippage,
        slippage_param: slippage === "percent" ? 0.0005 : slippage === "tick" ? 1 : 0,
      };
      const res = await apiClient.request<BacktestResult>("/api/v1/backtests/run", {
        method: "POST",
        body: JSON.stringify(config),
      });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "Backtest request failed.");
    } finally {
      setLoading(false);
    }
  };

  const m = result?.metrics;
  const noData = result != null && m != null && m.total_trades === 0;

  return (
    <div style={{ padding: "var(--spacing-5)", display: "flex", flexDirection: "column", gap: "var(--spacing-5)", maxWidth: "1180px" }}>
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: "bold", margin: "0 0 var(--spacing-1)" }}>Strategy Lab</h2>
        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Configure a run and execute it against the warehouse — wired to{" "}
          <code style={{ fontFamily: "var(--font-family-mono)" }}>POST /api/v1/backtests/run</code>. Records StrategyIR, data/manifest version, seed &amp; code commit per run.
        </p>
      </div>

      {error && (
        <div style={{ color: "var(--color-down)", background: "var(--color-down-bg)", border: "1px solid rgba(248,81,73,0.35)", borderRadius: "var(--radius-md)", padding: "var(--spacing-3)", fontSize: "var(--font-size-sm)" }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 300px) 1fr", gap: "var(--spacing-5)", alignItems: "start" }}>
        {/* Config */}
        <div style={panelStyle}>
          <div style={panelHeadStyle}>Backtest Configuration</div>
          <div style={{ padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
              <label style={labelStyle} htmlFor="sl-strat">Strategy</label>
              <select id="sl-strat" style={inputStyle} value={selected} onChange={(e) => setSelected(Number(e.target.value))}>
                {templates.length === 0 && <option>Loading templates…</option>}
                {templates.map((t, i) => (
                  <option key={t.name} value={i}>{t.name}</option>
                ))}
              </select>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
              <label style={labelStyle}>Universe</label>
              <input style={{ ...inputStyle, color: "var(--text-muted)" }} value={templates[selected]?.universe?.index_name ?? "—"} readOnly />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                <label style={labelStyle} htmlFor="sl-from">From</label>
                <input id="sl-from" type="date" style={inputStyle} value={from} onChange={(e) => setFrom(e.target.value)} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                <label style={labelStyle} htmlFor="sl-to">To</label>
                <input id="sl-to" type="date" style={inputStyle} value={to} onChange={(e) => setTo(e.target.value)} />
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
              <label style={labelStyle} htmlFor="sl-cap">Initial Capital (₹)</label>
              <input id="sl-cap" type="number" style={{ ...inputStyle, fontVariantNumeric: "tabular-nums" }} value={capital} min={1} onChange={(e) => setCapital(Number(e.target.value))} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                <label style={labelStyle} htmlFor="sl-slip">Slippage</label>
                <select id="sl-slip" style={inputStyle} value={slippage} onChange={(e) => setSlippage(e.target.value)}>
                  <option value="percent">Percent (0.05%)</option>
                  <option value="tick">Tick (1)</option>
                  <option value="none">None</option>
                </select>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                <label style={labelStyle} htmlFor="sl-fill">Fill Timing</label>
                <select id="sl-fill" style={inputStyle} value={fillTiming} onChange={(e) => setFillTiming(e.target.value)}>
                  <option value="NEXT_BAR_OPEN">Next Bar Open</option>
                  <option value="SIGNAL_BAR_CLOSE">Signal Bar Close</option>
                </select>
              </div>
            </div>
            <button
              onClick={runBacktest}
              disabled={loading || templates.length === 0}
              style={{ marginTop: "0.3rem", background: "var(--color-primary)", color: "var(--text-inverse)", fontWeight: 700, border: "none", borderRadius: "var(--radius-md)", padding: "0.55rem", fontSize: "var(--font-size-sm)", cursor: loading ? "default" : "pointer", opacity: loading || templates.length === 0 ? 0.6 : 1 }}
            >
              {loading ? "Running…" : "▶ Run Backtest"}
            </button>
          </div>
        </div>

        {/* Results */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-4)" }}>
          {!result && !loading && (
            <div style={{ ...panelStyle, padding: "var(--spacing-6)", color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
              Configure a strategy and date range on the left, then run a backtest to see metrics, the equity curve, and the trade log here.
            </div>
          )}

          {noData && (
            <div style={{ color: "var(--color-warning)", background: "var(--color-warning-bg)", border: "1px solid rgba(210,153,34,0.35)", borderRadius: "var(--radius-md)", padding: "var(--spacing-3)", fontSize: "var(--font-size-sm)" }}>
              The run executed (engine commit <code style={{ fontFamily: "var(--font-family-mono)" }}>{result?.engine_commit.slice(0, 10)}</code>) but found <b>0 bars</b> in the warehouse for this range, so there are no trades. Populate history via <b>Data Engine → Sync</b>, then re-run.
            </div>
          )}

          {m && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--spacing-3)" }}>
                <Tile k="Total Return" v={pct(m.total_return_pct)} tone={toneColor(m.total_return_pct)} />
                <Tile k="CAGR" v={pct(m.cagr_pct)} tone={toneColor(m.cagr_pct)} />
                <Tile k="Sharpe" v={m.sharpe_ratio.toFixed(2)} />
                <Tile k="Max Drawdown" v={pct(m.max_drawdown_pct)} tone="var(--color-down)" />
                <Tile k="Win Rate" v={`${m.win_rate_pct.toFixed(1)}%`} />
                <Tile k="Profit Factor" v={Number.isFinite(m.profit_factor) ? m.profit_factor.toFixed(2) : "—"} />
              </div>

              <div style={panelStyle}>
                <div style={{ padding: "var(--spacing-4)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.4rem" }}>
                    <span style={{ fontWeight: 600, fontSize: "var(--font-size-sm)" }}>Equity Curve</span>
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                      {inr(m.initial_capital)} → {inr(m.final_equity)} · {m.total_trades} trades
                    </span>
                  </div>
                  <EquityChart points={result?.equity_curve ?? []} />
                </div>
              </div>

              <div style={panelStyle}>
                <div style={panelHeadStyle}>
                  Trade Log <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>· {result?.trades.length ?? 0} fills</span>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
                    <thead>
                      <tr>
                        {["Security", "Side", "Qty", "Price", "Costs", "Time"].map((h, i) => (
                          <th key={h} style={{ textAlign: i >= 2 && i <= 4 ? "right" : "left", fontSize: "var(--font-size-xs)", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-default)" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(result?.trades ?? []).slice(0, 30).map((t) => (
                        <tr key={t.fill_id}>
                          <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", fontFamily: "var(--font-family-mono)" }}>{t.security_id}</td>
                          <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)" }}>
                            <span style={{ fontSize: "var(--font-size-xs)", fontWeight: 600, padding: "0.12rem 0.45rem", borderRadius: "var(--radius-sm)", background: t.side === "BUY" ? "var(--color-up-bg)" : "var(--color-down-bg)", color: t.side === "BUY" ? "var(--color-up)" : "var(--color-down)" }}>{t.side}</span>
                          </td>
                          <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{t.quantity.toLocaleString("en-IN")}</td>
                          <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", textAlign: "right", fontVariantNumeric: "tabular-nums", fontFamily: "var(--font-family-mono)" }}>{t.price.toFixed(2)}</td>
                          <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{inr(t.brokerage + t.taxes + t.slippage)}</td>
                          <td style={{ padding: "0.5rem 0.7rem", borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>{new Date(t.timestamp).toLocaleDateString("en-IN")}</td>
                        </tr>
                      ))}
                      {(result?.trades.length ?? 0) === 0 && (
                        <tr>
                          <td colSpan={6} style={{ padding: "var(--spacing-4)", color: "var(--text-muted)", textAlign: "center", fontSize: "var(--font-size-sm)" }}>No fills in this run.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
