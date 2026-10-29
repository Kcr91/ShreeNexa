import React from "react";
import {
  StrategyBuilderState,
  BreakoutCondition,
  BreakoutLevelType,
} from "../types";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const LEVEL_TYPES: { value: BreakoutLevelType; label: string }[] = [
  { value: "prev_day_high", label: "Previous Day High" },
  { value: "prev_day_low", label: "Previous Day Low" },
  { value: "prev_day_close", label: "Previous Day Close" },
  { value: "opening_range_high", label: "Opening Range High (ORB)" },
  { value: "opening_range_low", label: "Opening Range Low (ORB)" },
  { value: "pivot", label: "Pivot Point" },
  { value: "support", label: "Support Level" },
  { value: "resistance", label: "Resistance Level" },
  { value: "custom_level", label: "Custom Level" },
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

const PRESETS: Array<{ label: string; make: () => BreakoutCondition }> = [
  {
    label: "ORB Breakout (15m) + Volume",
    make: () => ({
      id: `br-${Date.now()}`,
      levelType: "opening_range_high",
      direction: "above",
      orbMinutes: 15,
      volumeConfirmation: true,
      volumeMultiplier: 1.5,
    }),
  },
  {
    label: "Prev Day High Break",
    make: () => ({ id: `br-${Date.now()}`, levelType: "prev_day_high", direction: "above" }),
  },
  {
    label: "Prev Day Low Break",
    make: () => ({ id: `br-${Date.now()}`, levelType: "prev_day_low", direction: "below" }),
  },
];

// Non-type-level UI-only flag for the retest option; preserved on the object
// via a loosened cast so it survives round-trip through the compiler's _ui block.
type BreakoutConditionUI = BreakoutCondition & { waitForRetest?: boolean };

export const BreakoutPanel: React.FC<Props> = ({ state, onChange }) => {
  const addBlank = () => {
    const id = `br-${Date.now()}`;
    onChange({
      ...state,
      breakoutConditions: [
        ...state.breakoutConditions,
        { id, levelType: "prev_day_high", direction: "above" },
      ],
    });
  };

  const addPreset = (make: () => BreakoutCondition) => {
    onChange({ ...state, breakoutConditions: [...state.breakoutConditions, make()] });
  };

  const update = (id: string, patch: Partial<BreakoutConditionUI>) => {
    onChange({
      ...state,
      breakoutConditions: state.breakoutConditions.map((b) =>
        b.id === id ? { ...b, ...patch } : b
      ),
    });
  };

  const remove = (id: string) => {
    onChange({ ...state, breakoutConditions: state.breakoutConditions.filter((b) => b.id !== id) });
  };

  return (
    <div
      data-testid="breakout-panel"
      style={{ padding: "var(--spacing-2)", display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", height: "100%" }}
    >
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
        <button type="button" onClick={addBlank} style={primaryBtn}>+ Breakout</button>
        <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginLeft: "6px" }}>Presets:</span>
        {PRESETS.map((p) => (
          <button key={p.label} type="button" onClick={() => addPreset(p.make)} style={btnStyle}>{p.label}</button>
        ))}
      </div>

      {state.breakoutConditions.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>No breakout conditions yet.</div>
      )}

      {state.breakoutConditions.map((b) => {
        const ui = b as BreakoutConditionUI;
        return (
          <div key={b.id} data-testid={`breakout-${b.id}`} style={sectionCard}>
            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
              <select
                value={b.levelType}
                onChange={(e) => update(b.id, { levelType: e.target.value as BreakoutLevelType })}
                style={inputStyle}
                aria-label="Breakout level type"
              >
                {LEVEL_TYPES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
              <select
                value={b.direction}
                onChange={(e) => update(b.id, { direction: e.target.value as "above" | "below" })}
                style={inputStyle}
                aria-label="Breakout direction"
              >
                <option value="above">Break Above</option>
                <option value="below">Break Below</option>
              </select>
              <button type="button" onClick={() => remove(b.id)} style={{ ...btnStyle, color: "var(--color-down)" }} aria-label="Remove breakout">✕</button>
            </div>

            {(b.levelType === "opening_range_high" || b.levelType === "opening_range_low") && (
              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>ORB duration</span>
                <input
                  type="number"
                  min={1}
                  value={b.orbMinutes ?? 15}
                  onChange={(e) => update(b.id, { orbMinutes: Number(e.target.value) })}
                  style={{ ...inputStyle, width: "80px" }}
                  aria-label="ORB minutes"
                />
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>minutes</span>
                <div style={{ display: "flex", gap: "4px", marginLeft: "6px" }}>
                  {[5, 15, 30, 60].map((v) => (
                    <button key={v} type="button" onClick={() => update(b.id, { orbMinutes: v })} style={btnStyle}>{v}m</button>
                  ))}
                </div>
              </div>
            )}

            {(b.levelType === "custom_level" || b.levelType === "support" || b.levelType === "resistance") && (
              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Level price</span>
                <input
                  type="number"
                  step={0.05}
                  value={b.customValue ?? ""}
                  onChange={(e) => update(b.id, { customValue: Number(e.target.value) })}
                  style={{ ...inputStyle, flex: 1 }}
                  aria-label="Custom level value"
                />
              </div>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <label style={{ fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: "4px" }}>
                <input
                  type="checkbox"
                  checked={!!b.volumeConfirmation}
                  onChange={(e) => update(b.id, { volumeConfirmation: e.target.checked })}
                />
                Require volume confirmation
              </label>
              {b.volumeConfirmation && (
                <>
                  <input
                    type="number"
                    step={0.1}
                    min={1}
                    value={b.volumeMultiplier ?? 1.5}
                    onChange={(e) => update(b.id, { volumeMultiplier: Number(e.target.value) })}
                    style={{ ...inputStyle, width: "80px" }}
                    aria-label="Volume multiplier"
                  />
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>× avg volume</span>
                </>
              )}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <label style={{ fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: "4px" }}>
                <input
                  type="checkbox"
                  checked={!!ui.waitForRetest}
                  onChange={(e) => update(b.id, { waitForRetest: e.target.checked })}
                />
                Wait for retest after breakout
              </label>
            </div>
          </div>
        );
      })}
    </div>
  );
};
