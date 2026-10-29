import React from "react";
import { IndicatorNode, StrategyBuilderState } from "../types";
import {
  INDICATOR_CATALOG,
  INDICATOR_CATEGORY_LABELS,
  IndicatorCatalogEntry,
} from "../defaults";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const sectionTitle: React.CSSProperties = {
  fontSize: "0.6875rem",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  letterSpacing: "0.04em",
};

const btnStyle: React.CSSProperties = {
  padding: "4px 8px",
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

const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
  padding: "4px 6px",
  fontSize: "0.6875rem",
  width: "100%",
};

export const IndicatorPanel: React.FC<Props> = ({ state, onChange }) => {
  const [search, setSearch] = React.useState("");
  const [selected, setSelected] = React.useState<IndicatorCatalogEntry | null>(null);
  const [params, setParams] = React.useState<Record<string, number | string>>({});
  const [name, setName] = React.useState("");

  React.useEffect(() => {
    if (selected) {
      setParams({ ...selected.defaultParams });
      const count = state.indicators.filter((i) => i.function === selected.fn).length + 1;
      setName(`${selected.fn}_${count}`);
    }
  }, [selected, state.indicators]);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return INDICATOR_CATALOG;
    return INDICATOR_CATALOG.filter(
      (c) => c.label.toLowerCase().includes(q) || c.fn.toLowerCase().includes(q)
    );
  }, [search]);

  const grouped = React.useMemo(() => {
    const g: Record<string, IndicatorCatalogEntry[]> = {};
    for (const entry of filtered) {
      (g[entry.category] ||= []).push(entry);
    }
    return g;
  }, [filtered]);

  const handleAdd = () => {
    if (!selected) return;
    const trimmed = name.trim() || selected.fn;
    const newInd: IndicatorNode = {
      id: `ind-${Date.now()}`,
      name: trimmed,
      function: selected.fn,
      params: { ...params },
    };
    onChange({ ...state, indicators: [...state.indicators, newInd] });
    setSelected(null);
  };

  const quickAddEma = () => {
    const count = state.indicators.filter((i) => i.function === "ema").length + 1;
    onChange({
      ...state,
      indicators: [
        ...state.indicators,
        { id: `ind-${Date.now()}`, name: `ema_${count}`, function: "ema", params: { period: 20, source: "close" } },
      ],
    });
  };

  const quickAddRsi = () => {
    const count = state.indicators.filter((i) => i.function === "rsi").length + 1;
    onChange({
      ...state,
      indicators: [
        ...state.indicators,
        { id: `ind-${Date.now()}`, name: `rsi_${count}`, function: "rsi", params: { period: 14 } },
      ],
    });
  };

  const removeIndicator = (id: string) => {
    onChange({ ...state, indicators: state.indicators.filter((i) => i.id !== id) });
  };

  return (
    <div
      data-testid="indicator-panel"
      style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-3)", padding: "var(--spacing-2)", height: "100%", overflow: "hidden" }}
    >
      {/* Left: catalog */}
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflow: "hidden" }}>
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <input
            aria-label="Search indicators"
            type="text"
            placeholder="Search indicators..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ ...inputStyle, flex: 1 }}
          />
          <button type="button" onClick={quickAddEma} style={btnStyle}>+EMA</button>
          <button type="button" onClick={quickAddRsi} style={btnStyle}>+RSI</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
          {Object.entries(grouped).map(([cat, entries]) => (
            <div key={cat}>
              <div style={sectionTitle}>{INDICATOR_CATEGORY_LABELS[cat as IndicatorCatalogEntry["category"]]}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                {entries.map((entry) => (
                  <button
                    key={entry.fn}
                    type="button"
                    data-testid={`indicator-catalog-${entry.fn}`}
                    onClick={() => setSelected(entry)}
                    style={{
                      ...btnStyle,
                      borderColor: selected?.fn === entry.fn ? "var(--color-primary)" : "var(--border-default)",
                    }}
                  >
                    {entry.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {selected && (
          <div
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
            <div style={{ fontSize: "var(--font-size-xs)", fontWeight: 700 }}>Configure {selected.label}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
              <div>
                <div style={sectionTitle}>Name</div>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
              </div>
              {selected.paramFields.map((pf) => (
                <div key={pf.key}>
                  <div style={sectionTitle}>{pf.label}</div>
                  <input
                    type={pf.type}
                    min={pf.min}
                    max={pf.max}
                    step={pf.step}
                    value={params[pf.key] ?? ""}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        [pf.key]: pf.type === "number" ? Number(e.target.value) : e.target.value,
                      }))
                    }
                    style={inputStyle}
                  />
                </div>
              ))}
            </div>
            <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
              <button type="button" onClick={() => setSelected(null)} style={btnStyle}>Cancel</button>
              <button type="button" onClick={handleAdd} style={primaryBtn}>Add Indicator</button>
            </div>
          </div>
        )}
      </div>

      {/* Right: added indicators */}
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflow: "hidden" }}>
        <div style={sectionTitle}>Added Indicators ({state.indicators.length})</div>
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
          {state.indicators.length === 0 && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>No indicators yet. Pick one from the catalog.</div>
          )}
          {state.indicators.map((ind) => (
            <div
              key={ind.id}
              data-testid={`indicator-card-${ind.name}`}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-2)",
                fontSize: "0.6875rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <strong style={{ color: "var(--color-primary)" }}>{ind.name}</strong>
                <div style={{ color: "var(--text-muted)" }}>
                  {ind.function}({JSON.stringify(ind.params)})
                </div>
              </div>
              <button
                type="button"
                onClick={() => removeIndicator(ind.id)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                aria-label={`Remove ${ind.name}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
