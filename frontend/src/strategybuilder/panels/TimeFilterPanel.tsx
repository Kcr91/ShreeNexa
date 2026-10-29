import React from "react";
import { StrategyBuilderState, TimeFilter, TimeFilterMode } from "../types";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const MODE_LABELS: { value: TimeFilterMode; label: string }[] = [
  { value: "clock", label: "Clock Time" },
  { value: "from_open", label: "Minutes from Open" },
  { value: "to_close", label: "Minutes to Close" },
  { value: "dte", label: "Days to Expiry" },
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

const sectionTitle: React.CSSProperties = {
  fontSize: "0.6875rem",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

const PRESETS: Array<{ label: string; make: () => TimeFilter }> = [
  { label: "Skip first 15 min", make: () => ({ id: `tf-${Date.now()}`, mode: "from_open", fromMinutes: 15 }) },
  { label: "Exit before close", make: () => ({ id: `tf-${Date.now()}`, mode: "to_close", toMinutes: 15 }) },
  { label: "Regular hours only", make: () => ({ id: `tf-${Date.now()}`, mode: "clock", fromTime: "09:30", toTime: "15:15" }) },
  { label: "First hour only", make: () => ({ id: `tf-${Date.now()}`, mode: "clock", fromTime: "09:15", toTime: "10:15" }) },
];

export const TimeFilterPanel: React.FC<Props> = ({ state, onChange }) => {
  const addFilter = () => {
    const id = `tf-${Date.now()}`;
    onChange({
      ...state,
      timeFilters: [...state.timeFilters, { id, mode: "clock", fromTime: "09:30", toTime: "15:15" }],
    });
  };

  const addPreset = (make: () => TimeFilter) => {
    onChange({ ...state, timeFilters: [...state.timeFilters, make()] });
  };

  const update = (id: string, patch: Partial<TimeFilter>) => {
    onChange({
      ...state,
      timeFilters: state.timeFilters.map((f) => (f.id === id ? { ...f, ...patch } : f)),
    });
  };

  const remove = (id: string) => {
    onChange({ ...state, timeFilters: state.timeFilters.filter((f) => f.id !== id) });
  };

  return (
    <div
      data-testid="time-filter-panel"
      style={{ padding: "var(--spacing-2)", display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", height: "100%" }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
        <button type="button" onClick={addFilter} style={primaryBtn}>+ Time Filter</button>
        <span style={{ ...sectionTitle, marginLeft: "6px" }}>Presets:</span>
        {PRESETS.map((p) => (
          <button key={p.label} type="button" onClick={() => addPreset(p.make)} style={btnStyle}>{p.label}</button>
        ))}
      </div>

      {state.timeFilters.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>No time filters yet. Add one or use a preset.</div>
      )}

      {state.timeFilters.map((f) => (
        <div
          key={f.id}
          data-testid={`time-filter-${f.id}`}
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--spacing-2)",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <select
              value={f.mode}
              onChange={(e) => update(f.id, { mode: e.target.value as TimeFilterMode })}
              style={inputStyle}
              aria-label="Mode"
            >
              {MODE_LABELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <button type="button" onClick={() => remove(f.id)} style={{ ...btnStyle, color: "var(--color-down)" }} aria-label="Remove">✕</button>
          </div>

          {f.mode === "clock" && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>From</span>
              <input type="time" value={f.fromTime ?? ""} onChange={(e) => update(f.id, { fromTime: e.target.value })} style={inputStyle} aria-label="From time" />
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>To</span>
              <input type="time" value={f.toTime ?? ""} onChange={(e) => update(f.id, { toTime: e.target.value })} style={inputStyle} aria-label="To time" />
            </div>
          )}

          {f.mode === "from_open" && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>After</span>
              <input type="number" min={1} value={f.fromMinutes ?? ""} onChange={(e) => update(f.id, { fromMinutes: Number(e.target.value) })} style={{ ...inputStyle, width: "80px" }} aria-label="Minutes after open" />
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>minutes from open</span>
            </div>
          )}

          {f.mode === "to_close" && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Before</span>
              <input type="number" min={1} value={f.toMinutes ?? ""} onChange={(e) => update(f.id, { toMinutes: Number(e.target.value) })} style={{ ...inputStyle, width: "80px" }} aria-label="Minutes before close" />
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>minutes to close</span>
            </div>
          )}

          {f.mode === "dte" && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>DTE</span>
              <input type="number" min={0} value={f.dte ?? ""} onChange={(e) => update(f.id, { dte: Number(e.target.value) })} style={{ ...inputStyle, width: "80px" }} aria-label="DTE" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
