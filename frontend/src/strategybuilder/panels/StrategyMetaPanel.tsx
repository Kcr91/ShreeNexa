import React from "react";
import {
  StrategyBuilderState,
  StrategyKind,
  StrategyHorizon,
  StrategyType,
} from "../types";
import { INDEX_OPTIONS, TIMEFRAME_OPTIONS } from "../defaults";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const KINDS: { value: StrategyKind; label: string }[] = [
  { value: "stock", label: "Stock" },
  { value: "option", label: "Option" },
  { value: "futures", label: "Futures" },
  { value: "investing", label: "Investing" },
  { value: "composite", label: "Composite" },
];

const HORIZONS: { value: StrategyHorizon; label: string }[] = [
  { value: "intraday", label: "Intraday" },
  { value: "swing", label: "Swing" },
  { value: "positional", label: "Positional" },
  { value: "investing", label: "Investing" },
];

const TYPES: { value: StrategyType; label: string }[] = [
  { value: "trend_following", label: "Trend Following" },
  { value: "swing_trading", label: "Swing Trading" },
  { value: "mean_reversion", label: "Mean Reversion" },
  { value: "option_selling", label: "Option Selling" },
  { value: "other", label: "Other" },
];

type UniverseType = "static" | "index" | "watchlist" | "screener";

const SESSIONS: { value: string; label: string }[] = [
  { value: "regular", label: "Regular (09:15-15:30)" },
  { value: "pre_open", label: "Pre-open (09:00-09:15)" },
  { value: "extended", label: "Extended" },
  { value: "custom", label: "Custom" },
];

const cellStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  fontSize: "var(--font-size-xs)",
};

const labelStyle: React.CSSProperties = {
  color: "var(--text-muted)",
  fontSize: "0.6875rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
  padding: "4px 8px",
  fontSize: "var(--font-size-xs)",
};

export const StrategyMetaPanel: React.FC<Props> = ({ state, onChange }) => {
  const [universeType, setUniverseType] = React.useState<UniverseType>(
    state.kind === "option" ? "static" : "index"
  );
  const [staticList, setStaticList] = React.useState<string>("");
  const [session, setSession] = React.useState<string>("regular");
  const [sessionFrom, setSessionFrom] = React.useState<string>("09:15");
  const [sessionTo, setSessionTo] = React.useState<string>("15:30");

  const patch = (p: Partial<StrategyBuilderState>) => onChange({ ...state, ...p });

  return (
    <div
      data-testid="strategy-meta-panel"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "var(--spacing-3)",
        padding: "var(--spacing-2)",
      }}
    >
      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-strategy-name">Strategy Name</label>
        <input
          id="meta-strategy-name"
          aria-label="Strategy Name"
          type="text"
          value={state.strategyName}
          onChange={(e) => patch({ strategyName: e.target.value })}
          style={inputStyle}
        />
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-kind">Strategy Kind</label>
        <select
          id="meta-kind"
          value={state.kind}
          onChange={(e) => patch({ kind: e.target.value as StrategyKind })}
          style={inputStyle}
        >
          {KINDS.map((k) => (
            <option key={k.value} value={k.value}>{k.label}</option>
          ))}
        </select>
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-horizon">Horizon</label>
        <select
          id="meta-horizon"
          value={state.horizon}
          onChange={(e) => patch({ horizon: e.target.value as StrategyHorizon })}
          style={inputStyle}
        >
          {HORIZONS.map((h) => (
            <option key={h.value} value={h.value}>{h.label}</option>
          ))}
        </select>
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-type">Strategy Type</label>
        <select
          id="meta-type"
          value={state.strategyType}
          onChange={(e) => patch({ strategyType: e.target.value as StrategyType })}
          style={inputStyle}
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-universe-type">Universe Type</label>
        <select
          id="meta-universe-type"
          value={universeType}
          onChange={(e) => setUniverseType(e.target.value as UniverseType)}
          style={inputStyle}
        >
          <option value="static">Static (stock list)</option>
          <option value="index">Index</option>
          <option value="watchlist">Watchlist</option>
          <option value="screener">Screener</option>
        </select>
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-universe">Universe</label>
        {universeType === "index" && (
          <select
            id="meta-universe"
            aria-label="Universe"
            value={state.universe}
            onChange={(e) => patch({ universe: e.target.value })}
            style={inputStyle}
          >
            {INDEX_OPTIONS.map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
        )}
        {universeType === "static" && (
          <input
            id="meta-universe"
            aria-label="Universe"
            type="text"
            placeholder="RELIANCE, HDFCBANK, INFY"
            value={staticList || state.universe}
            onChange={(e) => {
              setStaticList(e.target.value);
              patch({ universe: e.target.value });
            }}
            style={inputStyle}
          />
        )}
        {universeType === "watchlist" && (
          <input
            id="meta-universe"
            aria-label="Universe"
            type="text"
            placeholder="Saved watchlist name"
            value={state.universe}
            onChange={(e) => patch({ universe: e.target.value })}
            style={inputStyle}
          />
        )}
        {universeType === "screener" && (
          <input
            id="meta-universe"
            aria-label="Universe"
            type="text"
            placeholder="Screener name or id"
            value={state.universe}
            onChange={(e) => patch({ universe: e.target.value })}
            style={inputStyle}
          />
        )}
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-timeframe">Timeframe</label>
        <select
          id="meta-timeframe"
          aria-label="Timeframe"
          value={state.timeframe}
          onChange={(e) => patch({ timeframe: e.target.value })}
          style={inputStyle}
        >
          {TIMEFRAME_OPTIONS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      <div style={cellStyle}>
        <label style={labelStyle} htmlFor="meta-session">Session</label>
        <select
          id="meta-session"
          value={session}
          onChange={(e) => setSession(e.target.value)}
          style={inputStyle}
        >
          {SESSIONS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
        {session === "custom" && (
          <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
            <input type="time" value={sessionFrom} onChange={(e) => setSessionFrom(e.target.value)} style={inputStyle} />
            <input type="time" value={sessionTo} onChange={(e) => setSessionTo(e.target.value)} style={inputStyle} />
          </div>
        )}
      </div>
    </div>
  );
};
