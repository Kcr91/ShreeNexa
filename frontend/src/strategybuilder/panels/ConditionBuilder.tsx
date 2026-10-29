import React from "react";
import {
  StrategyBuilderState,
  StrategyRuleBlock,
  RuleCondition,
  RuleOperator,
  RuleBlockType,
} from "../types";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const OPERATORS: { value: RuleOperator; label: string }[] = [
  { value: "CROSS_ABOVE", label: "crosses above" },
  { value: "CROSS_BELOW", label: "crosses below" },
  { value: "GREATER_THAN", label: ">" },
  { value: "LESS_THAN", label: "<" },
  { value: "GREATER_THAN_EQ", label: ">=" },
  { value: "LESS_THAN_EQ", label: "<=" },
  { value: "EQUALS", label: "==" },
  { value: "NOT_EQUALS", label: "!=" },
  { value: "BETWEEN", label: "between" },
  { value: "PCT_CHANGE_GT", label: "%Δ >" },
  { value: "PCT_CHANGE_LT", label: "%Δ <" },
];

const BAR_FIELDS = ["close", "open", "high", "low", "volume"];

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

export const ConditionBuilder: React.FC<Props> = ({ state, onChange }) => {
  const indicatorNames = state.indicators.map((i) => i.name);
  const operandOptions = [...indicatorNames, ...BAR_FIELDS];

  const updateRule = (ruleId: string, patch: Partial<StrategyRuleBlock>) => {
    onChange({
      ...state,
      rules: state.rules.map((r) => (r.id === ruleId ? { ...r, ...patch } : r)),
    });
  };

  const updateCondition = (ruleId: string, condId: string, patch: Partial<RuleCondition>) => {
    onChange({
      ...state,
      rules: state.rules.map((r) =>
        r.id === ruleId
          ? { ...r, conditions: r.conditions.map((c) => (c.id === condId ? { ...c, ...patch } : c)) }
          : r
      ),
    });
  };

  const addCondition = (ruleId: string) => {
    const now = Date.now();
    onChange({
      ...state,
      rules: state.rules.map((r) =>
        r.id === ruleId
          ? {
              ...r,
              conditions: [
                ...r.conditions,
                {
                  id: `cond-${now}`,
                  leftOperand: operandOptions[0] || "close",
                  operator: "GREATER_THAN",
                  rightOperand: operandOptions[1] || "0",
                },
              ],
            }
          : r
      ),
    });
  };

  const removeCondition = (ruleId: string, condId: string) => {
    onChange({
      ...state,
      rules: state.rules.map((r) =>
        r.id === ruleId
          ? { ...r, conditions: r.conditions.filter((c) => c.id !== condId) }
          : r
      ),
    });
  };

  const addRule = (type: RuleBlockType) => {
    const id = `rule-${Date.now()}`;
    onChange({
      ...state,
      rules: [
        ...state.rules,
        {
          id,
          name: type.replace("_", " ") + " Rule",
          type,
          combinator: "AND",
          conditions: [],
        },
      ],
    });
  };

  const removeRule = (ruleId: string) => {
    onChange({ ...state, rules: state.rules.filter((r) => r.id !== ruleId) });
  };

  return (
    <div
      data-testid="condition-builder"
      style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", padding: "var(--spacing-2)", overflowY: "auto", height: "100%" }}
    >
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        <button type="button" onClick={() => addRule("ENTRY_LONG")} style={primaryBtn}>+ Entry Long</button>
        <button type="button" onClick={() => addRule("ENTRY_SHORT")} style={primaryBtn}>+ Entry Short</button>
        <button type="button" onClick={() => addRule("EXIT_LONG")} style={btnStyle}>+ Exit Long</button>
        <button type="button" onClick={() => addRule("EXIT_SHORT")} style={btnStyle}>+ Exit Short</button>
      </div>

      {state.rules.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem", padding: "var(--spacing-2)" }}>
          No rules yet. Add an entry or exit rule to begin.
        </div>
      )}

      {state.rules.map((rule) => (
        <div
          key={rule.id}
          data-testid={`rule-block-${rule.id}`}
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--spacing-2)",
            fontSize: "var(--font-size-xs)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px", gap: "6px" }}>
            <input
              type="text"
              value={rule.name}
              onChange={(e) => updateRule(rule.id, { name: e.target.value })}
              style={{ ...inputStyle, flex: 1, fontWeight: 700 }}
            />
            <span
              style={{
                padding: "1px 6px",
                borderRadius: "3px",
                backgroundColor: rule.type.startsWith("ENTRY") ? "var(--color-up-bg)" : "var(--color-down-bg)",
                color: rule.type.startsWith("ENTRY") ? "var(--color-up)" : "var(--color-down)",
                fontWeight: 700,
                fontSize: "0.625rem",
              }}
            >
              {rule.type}
            </span>
            <select
              value={rule.combinator}
              onChange={(e) => updateRule(rule.id, { combinator: e.target.value as "AND" | "OR" })}
              style={inputStyle}
              aria-label={`Combinator for ${rule.name}`}
            >
              <option value="AND">AND</option>
              <option value="OR">OR</option>
            </select>
            <button type="button" onClick={() => removeRule(rule.id)} style={{ ...btnStyle, color: "var(--color-down)" }} aria-label={`Remove ${rule.name}`}>✕</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {rule.conditions.map((cond, idx) => (
              <div
                key={cond.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "0.6875rem",
                  backgroundColor: "var(--bg-active)",
                  padding: "4px 6px",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {idx > 0 && (
                  <span style={{ color: "var(--color-primary)", fontWeight: "bold", minWidth: "28px" }}>
                    {rule.combinator}
                  </span>
                )}
                <select
                  value={cond.leftOperand}
                  onChange={(e) => updateCondition(rule.id, cond.id, { leftOperand: e.target.value })}
                  style={inputStyle}
                  aria-label="Left operand"
                >
                  {operandOptions.map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
                <select
                  value={cond.operator}
                  onChange={(e) => updateCondition(rule.id, cond.id, { operator: e.target.value as RuleOperator })}
                  style={inputStyle}
                  aria-label="Operator"
                >
                  {OPERATORS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={cond.rightOperand}
                  onChange={(e) => updateCondition(rule.id, cond.id, { rightOperand: e.target.value })}
                  list={`operand-opts-${rule.id}`}
                  style={{ ...inputStyle, flex: 1 }}
                  aria-label="Right operand"
                />
                <datalist id={`operand-opts-${rule.id}`}>
                  {operandOptions.map((o) => (
                    <option key={o} value={o} />
                  ))}
                </datalist>
                {(cond.operator === "BETWEEN") && (
                  <input
                    type="text"
                    placeholder="upper"
                    value={cond.rightOperand2 || ""}
                    onChange={(e) => updateCondition(rule.id, cond.id, { rightOperand2: e.target.value })}
                    style={inputStyle}
                    aria-label="Right operand upper bound"
                  />
                )}
                {(cond.operator === "PCT_CHANGE_GT" || cond.operator === "PCT_CHANGE_LT") && (
                  <input
                    type="number"
                    placeholder="bars"
                    min={1}
                    value={cond.lookback ?? 1}
                    onChange={(e) => updateCondition(rule.id, cond.id, { lookback: Number(e.target.value) })}
                    style={{ ...inputStyle, width: "60px" }}
                    aria-label="Lookback bars"
                  />
                )}
                <button
                  type="button"
                  onClick={() => removeCondition(rule.id, cond.id)}
                  style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                  aria-label="Remove condition"
                >✕</button>
              </div>
            ))}
            <button type="button" onClick={() => addCondition(rule.id)} style={{ ...btnStyle, alignSelf: "flex-start" }}>
              + Condition
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
