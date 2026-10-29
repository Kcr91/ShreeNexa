import React from "react";
import {
  StrategyBuilderState,
  SizingType,
  ExitType,
  ExitRuleConfig,
  SizingConfig,
  RiskConfig,
} from "../types";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
  padding: "4px 6px",
  fontSize: "0.6875rem",
  width: "100%",
};

const btnStyle: React.CSSProperties = {
  padding: "3px 8px",
  fontSize: "0.6875rem",
  cursor: "pointer",
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
};

const sectionCard: React.CSSProperties = {
  backgroundColor: "var(--bg-surface)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--spacing-2)",
  display: "flex",
  flexDirection: "column",
  gap: "var(--spacing-2)",
};

const sectionTitle: React.CSSProperties = {
  fontSize: "0.6875rem",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

const labelStyle: React.CSSProperties = {
  color: "var(--text-muted)",
  fontSize: "0.625rem",
  textTransform: "uppercase",
  letterSpacing: "0.03em",
};

const SIZING_TYPES: { value: SizingType; label: string }[] = [
  { value: "fixed_qty", label: "Fixed Qty" },
  { value: "fixed_value", label: "Fixed Value (₹)" },
  { value: "pct_capital", label: "% Capital" },
  { value: "risk_pct", label: "Risk %" },
  { value: "lots", label: "Lots" },
  { value: "kelly_fraction", label: "Kelly Fraction" },
];

const EXIT_TYPES: { value: ExitType; label: string }[] = [
  { value: "target", label: "Target" },
  { value: "stop", label: "Stop Loss" },
  { value: "trailing_stop", label: "Trailing Stop" },
  { value: "time", label: "Time Exit" },
  { value: "signal", label: "Signal Exit" },
];

export const RiskSizingPanel: React.FC<Props> = ({ state, onChange }) => {
  const [slippageMode, setSlippageMode] = React.useState<"pct" | "points">(
    state.slippagePoints !== undefined ? "points" : "pct"
  );
  const [newWindow, setNewWindow] = React.useState<string>("");

  const patchSizing = (p: Partial<SizingConfig>) =>
    onChange({ ...state, sizing: { ...state.sizing, ...p } });

  const patchRisk = (p: Partial<RiskConfig>) =>
    onChange({ ...state, risk: { ...state.risk, ...p } });

  const addExit = () => {
    const id = `exit-${Date.now()}`;
    onChange({
      ...state,
      exits: [...state.exits, { id, type: "target", pct: 2.0 }],
    });
  };

  const updateExit = (id: string, p: Partial<ExitRuleConfig>) => {
    onChange({
      ...state,
      exits: state.exits.map((e) => (e.id === id ? { ...e, ...p } : e)),
    });
  };

  const removeExit = (id: string) => {
    onChange({ ...state, exits: state.exits.filter((e) => e.id !== id) });
  };

  const addNoTradeWindow = () => {
    const w = newWindow.trim();
    if (!w) return;
    patchRisk({ noTradeWindows: [...state.risk.noTradeWindows, w] });
    setNewWindow("");
  };

  const removeWindow = (idx: number) => {
    patchRisk({ noTradeWindows: state.risk.noTradeWindows.filter((_, i) => i !== idx) });
  };

  return (
    <div
      data-testid="risk-sizing-panel"
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--spacing-2)", padding: "var(--spacing-2)", overflowY: "auto", height: "100%" }}
    >
      {/* Sizing */}
      <div style={sectionCard}>
        <div style={sectionTitle}>Position Sizing</div>
        <div>
          <div style={labelStyle}>Sizing Model</div>
          <select
            aria-label="Sizing type"
            value={state.sizing.type}
            onChange={(e) => patchSizing({ type: e.target.value as SizingType })}
            style={inputStyle}
          >
            {SIZING_TYPES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {state.sizing.type === "fixed_qty" && (
          <div>
            <div style={labelStyle}>Quantity</div>
            <input type="number" min={1} value={state.sizing.qty ?? ""} onChange={(e) => patchSizing({ qty: Number(e.target.value) })} style={inputStyle} />
          </div>
        )}
        {state.sizing.type === "fixed_value" && (
          <div>
            <div style={labelStyle}>Value (₹)</div>
            <input type="number" min={0} value={state.sizing.value ?? ""} onChange={(e) => patchSizing({ value: Number(e.target.value) })} style={inputStyle} />
          </div>
        )}
        {state.sizing.type === "pct_capital" && (
          <div>
            <div style={labelStyle}>% of Capital ({state.sizing.pct ?? 100})</div>
            <input type="range" min={1} max={100} value={state.sizing.pct ?? 100} onChange={(e) => patchSizing({ pct: Number(e.target.value) })} style={{ width: "100%" }} />
          </div>
        )}
        {state.sizing.type === "risk_pct" && (
          <>
            <div>
              <div style={labelStyle}>Risk %</div>
              <input type="number" step={0.1} min={0.1} max={100} value={state.sizing.riskPct ?? ""} onChange={(e) => patchSizing({ riskPct: Number(e.target.value) })} style={inputStyle} />
            </div>
            <div>
              <div style={labelStyle}>Stop Reference (exit id)</div>
              <input type="text" value={state.sizing.stopRef ?? ""} onChange={(e) => patchSizing({ stopRef: e.target.value })} style={inputStyle} />
            </div>
          </>
        )}
        {state.sizing.type === "lots" && (
          <div>
            <div style={labelStyle}>Lots</div>
            <input type="number" min={1} value={state.sizing.lots ?? ""} onChange={(e) => patchSizing({ lots: Number(e.target.value) })} style={inputStyle} />
          </div>
        )}
        {state.sizing.type === "kelly_fraction" && (
          <div>
            <div style={labelStyle}>Kelly Cap ({((state.sizing.kellyCap ?? 0.25) * 100).toFixed(0)}%)</div>
            <input type="range" min={0.01} max={1} step={0.01} value={state.sizing.kellyCap ?? 0.25} onChange={(e) => patchSizing({ kellyCap: Number(e.target.value) })} style={{ width: "100%" }} />
          </div>
        )}
      </div>

      {/* Exits */}
      <div style={sectionCard}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={sectionTitle}>Exit Rules ({state.exits.length})</div>
          <button type="button" onClick={addExit} style={btnStyle}>+ Exit</button>
        </div>
        {state.exits.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>No exit rules yet.</div>
        )}
        {state.exits.map((e) => (
          <div key={e.id} data-testid={`exit-row-${e.id}`} style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
            <select value={e.type} onChange={(ev) => updateExit(e.id, { type: ev.target.value as ExitType })} style={{ ...inputStyle, flex: "0 0 100px" }} aria-label="Exit type">
              {EXIT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            {(e.type === "target" || e.type === "stop") && (
              <input type="number" step={0.1} min={0.1} placeholder="%" value={e.pct ?? ""} onChange={(ev) => updateExit(e.id, { pct: Number(ev.target.value) })} style={{ ...inputStyle, flex: 1 }} aria-label="Exit percentage" />
            )}
            {e.type === "trailing_stop" && (
              <input type="number" step={0.1} min={0.1} placeholder="trailing %" value={e.trailingPct ?? ""} onChange={(ev) => updateExit(e.id, { trailingPct: Number(ev.target.value) })} style={{ ...inputStyle, flex: 1 }} aria-label="Trailing percentage" />
            )}
            {e.type === "time" && (
              <input type="time" value={e.timeExit ?? ""} onChange={(ev) => updateExit(e.id, { timeExit: ev.target.value })} style={{ ...inputStyle, flex: 1 }} aria-label="Time exit" />
            )}
            {e.type === "signal" && (
              <input type="text" placeholder="rule id" value={e.signalRuleId ?? ""} onChange={(ev) => updateExit(e.id, { signalRuleId: ev.target.value })} style={{ ...inputStyle, flex: 1 }} aria-label="Signal rule id" />
            )}
            <button type="button" onClick={() => removeExit(e.id)} style={{ ...btnStyle, color: "var(--color-down)" }} aria-label="Remove exit">✕</button>
          </div>
        ))}
      </div>

      {/* Risk */}
      <div style={sectionCard}>
        <div style={sectionTitle}>Risk Limits</div>
        <div>
          <div style={labelStyle}>Max Positions</div>
          <input type="number" min={1} value={state.risk.maxPositions} onChange={(e) => patchRisk({ maxPositions: Number(e.target.value) })} style={inputStyle} />
        </div>
        <div>
          <div style={labelStyle}>Max Daily Loss %</div>
          <input type="number" step={0.1} min={0.1} max={100} value={state.risk.maxDailyLossPct ?? ""} onChange={(e) => patchRisk({ maxDailyLossPct: e.target.value ? Number(e.target.value) : undefined })} style={inputStyle} />
        </div>
        <div>
          <div style={labelStyle}>Max Daily Loss ₹</div>
          <input type="number" min={0} value={state.risk.maxDailyLossAbs ?? ""} onChange={(e) => patchRisk({ maxDailyLossAbs: e.target.value ? Number(e.target.value) : undefined })} style={inputStyle} />
        </div>
        <div>
          <div style={labelStyle}>Max Position Value %</div>
          <input type="number" step={0.1} min={0.1} max={100} value={state.risk.maxPositionValuePct ?? ""} onChange={(e) => patchRisk({ maxPositionValuePct: e.target.value ? Number(e.target.value) : undefined })} style={inputStyle} />
        </div>
        <div>
          <div style={labelStyle}>Max Trades per Day</div>
          <input type="number" min={1} value={state.risk.maxTradesPerDay ?? ""} onChange={(e) => patchRisk({ maxTradesPerDay: e.target.value ? Number(e.target.value) : undefined })} style={inputStyle} />
        </div>
        <div>
          <div style={labelStyle}>No-Trade Windows</div>
          <div style={{ display: "flex", gap: "6px" }}>
            <input type="text" placeholder="09:15-09:20" value={newWindow} onChange={(e) => setNewWindow(e.target.value)} style={{ ...inputStyle, flex: 1 }} />
            <button type="button" onClick={addNoTradeWindow} style={btnStyle}>Add</button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "3px", marginTop: "4px" }}>
            {state.risk.noTradeWindows.map((w, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.6875rem", padding: "2px 6px", backgroundColor: "var(--bg-active)", borderRadius: "var(--radius-sm)" }}>
                <span>{w}</span>
                <button type="button" onClick={() => removeWindow(i)} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }} aria-label={`Remove window ${w}`}>✕</button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Slippage */}
      <div style={sectionCard}>
        <div style={sectionTitle}>Slippage</div>
        <div style={{ display: "flex", gap: "6px" }}>
          <button type="button" onClick={() => { setSlippageMode("pct"); onChange({ ...state, slippagePoints: undefined }); }} style={{ ...btnStyle, borderColor: slippageMode === "pct" ? "var(--color-primary)" : "var(--border-default)" }}>
            Percentage
          </button>
          <button type="button" onClick={() => { setSlippageMode("points"); onChange({ ...state, slippagePct: undefined }); }} style={{ ...btnStyle, borderColor: slippageMode === "points" ? "var(--color-primary)" : "var(--border-default)" }}>
            Points
          </button>
        </div>
        <div>
          <div style={labelStyle}>{slippageMode === "pct" ? "Slippage %" : "Slippage Points"}</div>
          {slippageMode === "pct" ? (
            <input type="number" step={0.01} min={0} value={state.slippagePct ?? ""} onChange={(e) => onChange({ ...state, slippagePct: e.target.value ? Number(e.target.value) : undefined })} style={inputStyle} />
          ) : (
            <input type="number" step={0.1} min={0} value={state.slippagePoints ?? ""} onChange={(e) => onChange({ ...state, slippagePoints: e.target.value ? Number(e.target.value) : undefined })} style={inputStyle} />
          )}
        </div>
      </div>
    </div>
  );
};
