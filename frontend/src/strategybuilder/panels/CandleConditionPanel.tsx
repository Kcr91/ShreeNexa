import React from "react";
import {
  StrategyBuilderState,
  CandleCondition,
  CandleConditionType,
  CandleColor,
  CandlePattern,
  RuleOperator,
} from "../types";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const CONDITION_TYPES: { value: CandleConditionType; label: string }[] = [
  { value: "color", label: "Candle Color" },
  { value: "pattern", label: "Candle Pattern" },
  { value: "body_size", label: "Body Size" },
  { value: "wick_ratio", label: "Wick Ratio" },
];

const COLORS: { value: CandleColor; label: string }[] = [
  { value: "green", label: "Green" },
  { value: "red", label: "Red" },
  { value: "doji", label: "Doji" },
];

const PATTERNS: { value: CandlePattern; label: string }[] = [
  { value: "bullish_engulfing", label: "Bullish Engulfing" },
  { value: "bearish_engulfing", label: "Bearish Engulfing" },
  { value: "hammer", label: "Hammer" },
  { value: "inverted_hammer", label: "Inverted Hammer" },
  { value: "morning_star", label: "Morning Star" },
  { value: "evening_star", label: "Evening Star" },
  { value: "doji", label: "Doji" },
  { value: "spinning_top", label: "Spinning Top" },
  { value: "marubozu", label: "Marubozu" },
  { value: "harami", label: "Harami" },
  { value: "piercing_line", label: "Piercing Line" },
  { value: "dark_cloud_cover", label: "Dark Cloud Cover" },
  { value: "three_white_soldiers", label: "Three White Soldiers" },
  { value: "three_black_crows", label: "Three Black Crows" },
];

const BAR_OFFSETS = [0, -1, -2, -3];

const SIMPLE_OPS: { value: RuleOperator; label: string }[] = [
  { value: "GREATER_THAN", label: ">" },
  { value: "LESS_THAN", label: "<" },
  { value: "GREATER_THAN_EQ", label: ">=" },
  { value: "LESS_THAN_EQ", label: "<=" },
];

const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
  padding: "3px 6px",
  fontSize: "0.6875rem",
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

const primaryBtn: React.CSSProperties = {
  ...btnStyle,
  backgroundColor: "var(--color-primary)",
  color: "var(--text-inverse)",
  border: "none",
  fontWeight: 700,
};

const sectionCard: React.CSSProperties = {
  backgroundColor: "var(--bg-surface)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--spacing-2)",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
};

const sectionTitle: React.CSSProperties = {
  fontSize: "0.6875rem",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

export const CandleConditionPanel: React.FC<Props> = ({ state, onChange }) => {
  const addCondition = (seed: Partial<CandleCondition> = {}) => {
    const id = `cc-${Date.now()}`;
    const base: CandleCondition = {
      id,
      type: "color",
      color: "green",
      barOffset: 0,
      dayReference: "current_day",
      ...seed,
    };
    onChange({ ...state, candleConditions: [...state.candleConditions, base] });
  };

  const update = (id: string, patch: Partial<CandleCondition>) => {
    onChange({
      ...state,
      candleConditions: state.candleConditions.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    });
  };

  const remove = (id: string) => {
    onChange({ ...state, candleConditions: state.candleConditions.filter((c) => c.id !== id) });
  };

  const prevDayShortcut = (color: CandleColor) =>
    addCondition({ type: "color", color, barOffset: -1, dayReference: "previous_day" });

  return (
    <div
      data-testid="candle-condition-panel"
      style={{ padding: "var(--spacing-2)", display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", height: "100%" }}
    >
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        <button type="button" onClick={() => addCondition()} style={primaryBtn}>+ Candle Condition</button>
      </div>

      {state.candleConditions.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>No candle conditions yet.</div>
      )}

      {state.candleConditions.map((c) => (
        <div key={c.id} data-testid={`candle-cond-${c.id}`} style={sectionCard}>
          <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
            <select value={c.type} onChange={(e) => update(c.id, { type: e.target.value as CandleConditionType })} style={inputStyle} aria-label="Candle condition type">
              {CONDITION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <select value={c.barOffset} onChange={(e) => update(c.id, { barOffset: Number(e.target.value) })} style={inputStyle} aria-label="Bar offset">
              {BAR_OFFSETS.map((b) => (
                <option key={b} value={b}>{b === 0 ? "Current" : `${b} bar${b === -1 ? "" : "s"} ago`}</option>
              ))}
            </select>
            <select value={c.dayReference ?? "current_day"} onChange={(e) => update(c.id, { dayReference: e.target.value as CandleCondition["dayReference"] })} style={inputStyle} aria-label="Day reference">
              <option value="current_day">Current Day</option>
              <option value="previous_day">Previous Day</option>
            </select>
            <button type="button" onClick={() => remove(c.id)} style={{ ...btnStyle, color: "var(--color-down)" }} aria-label="Remove candle condition">✕</button>
          </div>

          {c.type === "color" && (
            <div style={{ display: "flex", gap: "6px" }}>
              {COLORS.map((col) => (
                <label key={col.value} style={{ fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: "4px" }}>
                  <input
                    type="radio"
                    name={`color-${c.id}`}
                    value={col.value}
                    checked={c.color === col.value}
                    onChange={() => update(c.id, { color: col.value })}
                  />
                  {col.label}
                </label>
              ))}
            </div>
          )}

          {c.type === "pattern" && (
            <select value={c.pattern ?? ""} onChange={(e) => update(c.id, { pattern: e.target.value as CandlePattern })} style={inputStyle} aria-label="Candle pattern">
              <option value="">Select pattern...</option>
              {PATTERNS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          )}

          {(c.type === "body_size" || c.type === "wick_ratio") && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <select value={c.operator ?? "GREATER_THAN"} onChange={(e) => update(c.id, { operator: e.target.value as RuleOperator })} style={inputStyle} aria-label="Operator">
                {SIMPLE_OPS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <input
                type="number"
                step={0.1}
                value={c.value ?? ""}
                onChange={(e) => update(c.id, { value: Number(e.target.value) })}
                style={{ ...inputStyle, width: "100px" }}
                placeholder={c.type === "body_size" ? "% of range" : "ratio"}
                aria-label="Threshold"
              />
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                {c.type === "body_size" ? "% of total range" : "upper/lower wick ratio"}
              </span>
            </div>
          )}
        </div>
      ))}

      <div style={{ ...sectionCard, borderStyle: "dashed" }}>
        <div style={sectionTitle}>Previous-Day Shortcuts</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          <button type="button" onClick={() => prevDayShortcut("green")} style={btnStyle}>Prev day was Green</button>
          <button type="button" onClick={() => prevDayShortcut("red")} style={btnStyle}>Prev day was Red</button>
          <button type="button" onClick={() => prevDayShortcut("doji")} style={btnStyle}>Prev day was Doji</button>
        </div>
      </div>
    </div>
  );
};
