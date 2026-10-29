import React from "react";
import {
  StrategyBuilderState,
  OptionConfig,
  OptionLegDef,
  ExpiryRule,
  ExpiryType,
  StrikeSelector,
  StrikeSelectorType,
} from "../types";

interface Props {
  state: StrategyBuilderState;
  onChange: (next: StrategyBuilderState) => void;
}

const UNDERLYINGS = [
  { symbol: "NIFTY", segment: "NSE_IDX" },
  { symbol: "BANKNIFTY", segment: "NSE_IDX" },
  { symbol: "FINNIFTY", segment: "NSE_IDX" },
  { symbol: "SENSEX", segment: "BSE_IDX" },
  { symbol: "RELIANCE", segment: "NSE_EQ" },
  { symbol: "TCS", segment: "NSE_EQ" },
  { symbol: "INFY", segment: "NSE_EQ" },
  { symbol: "HDFCBANK", segment: "NSE_EQ" },
  { symbol: "ICICIBANK", segment: "NSE_EQ" },
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
  gap: "var(--spacing-2)",
};

const sectionTitle: React.CSSProperties = {
  fontSize: "0.6875rem",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

function emptyConfig(): OptionConfig {
  return {
    underlyingSymbol: "NIFTY",
    underlyingSegment: "NSE_IDX",
    expiryRule: { type: "weekly", offset: 0 },
    legs: [],
  };
}

function strikeFactory(type: StrikeSelectorType): StrikeSelector {
  switch (type) {
    case "atm":
      return { type: "atm", offset: 0 };
    case "delta":
      return { type: "delta", targetDelta: 0.3 };
    case "premium":
      return { type: "premium", targetPremium: 100 };
    case "absolute":
      return { type: "absolute", absoluteStrike: 0 };
  }
}

function newLeg(seed: Partial<OptionLegDef> = {}, idx: number): OptionLegDef {
  return {
    id: seed.id || `leg-${idx}-${Date.now()}`,
    optionType: seed.optionType || "CE",
    strike: seed.strike || strikeFactory("atm"),
    side: seed.side || "BUY",
    lots: seed.lots ?? 1,
  };
}

const TEMPLATES: Array<{ label: string; make: () => OptionLegDef[] }> = [
  {
    label: "Long Call",
    make: () => [newLeg({ optionType: "CE", side: "BUY", strike: { type: "atm", offset: 0 } }, 1)],
  },
  {
    label: "Long Put",
    make: () => [newLeg({ optionType: "PE", side: "BUY", strike: { type: "atm", offset: 0 } }, 1)],
  },
  {
    label: "Short Straddle",
    make: () => [
      newLeg({ optionType: "CE", side: "SELL", strike: { type: "atm", offset: 0 } }, 1),
      newLeg({ optionType: "PE", side: "SELL", strike: { type: "atm", offset: 0 } }, 2),
    ],
  },
  {
    label: "Short Strangle",
    make: () => [
      newLeg({ optionType: "CE", side: "SELL", strike: { type: "atm", offset: 2 } }, 1),
      newLeg({ optionType: "PE", side: "SELL", strike: { type: "atm", offset: -2 } }, 2),
    ],
  },
  {
    label: "Bull Call Spread",
    make: () => [
      newLeg({ optionType: "CE", side: "BUY", strike: { type: "atm", offset: 0 } }, 1),
      newLeg({ optionType: "CE", side: "SELL", strike: { type: "atm", offset: 3 } }, 2),
    ],
  },
  {
    label: "Bear Put Spread",
    make: () => [
      newLeg({ optionType: "PE", side: "BUY", strike: { type: "atm", offset: 0 } }, 1),
      newLeg({ optionType: "PE", side: "SELL", strike: { type: "atm", offset: -3 } }, 2),
    ],
  },
  {
    label: "Iron Condor",
    make: () => [
      newLeg({ optionType: "PE", side: "SELL", strike: { type: "atm", offset: -2 } }, 1),
      newLeg({ optionType: "PE", side: "BUY", strike: { type: "atm", offset: -5 } }, 2),
      newLeg({ optionType: "CE", side: "SELL", strike: { type: "atm", offset: 2 } }, 3),
      newLeg({ optionType: "CE", side: "BUY", strike: { type: "atm", offset: 5 } }, 4),
    ],
  },
  {
    label: "Iron Butterfly",
    make: () => [
      newLeg({ optionType: "PE", side: "SELL", strike: { type: "atm", offset: 0 } }, 1),
      newLeg({ optionType: "PE", side: "BUY", strike: { type: "atm", offset: -3 } }, 2),
      newLeg({ optionType: "CE", side: "SELL", strike: { type: "atm", offset: 0 } }, 3),
      newLeg({ optionType: "CE", side: "BUY", strike: { type: "atm", offset: 3 } }, 4),
    ],
  },
];

export const OptionConfigPanel: React.FC<Props> = ({ state, onChange }) => {
  const cfg: OptionConfig = state.optionConfig ?? emptyConfig();

  const patchCfg = (p: Partial<OptionConfig>) =>
    onChange({ ...state, optionConfig: { ...cfg, ...p } });

  const patchExpiry = (p: Partial<ExpiryRule>) =>
    patchCfg({ expiryRule: { ...cfg.expiryRule, ...p } });

  const addLeg = () => patchCfg({ legs: [...cfg.legs, newLeg({}, cfg.legs.length + 1)] });

  const updateLeg = (id: string, p: Partial<OptionLegDef>) =>
    patchCfg({ legs: cfg.legs.map((l) => (l.id === id ? { ...l, ...p } : l)) });

  const removeLeg = (id: string) => patchCfg({ legs: cfg.legs.filter((l) => l.id !== id) });

  const applyTemplate = (make: () => OptionLegDef[]) => {
    patchCfg({ legs: make() });
  };

  const setUnderlying = (symbol: string) => {
    const match = UNDERLYINGS.find((u) => u.symbol === symbol);
    patchCfg({ underlyingSymbol: symbol, underlyingSegment: match?.segment ?? cfg.underlyingSegment });
  };

  const updateStrike = (legId: string, type: StrikeSelectorType) => {
    updateLeg(legId, { strike: strikeFactory(type) });
  };

  const updateStrikeField = (legId: string, patch: Partial<StrikeSelector>) => {
    const leg = cfg.legs.find((l) => l.id === legId);
    if (!leg) return;
    updateLeg(legId, { strike: { ...leg.strike, ...patch } as StrikeSelector });
  };

  // Rough payoff summary (text only). Uses offsets as rough strikes.
  const payoffSummary = React.useMemo(() => {
    if (cfg.legs.length === 0) return "Add at least one leg for a payoff summary.";
    const longs = cfg.legs.filter((l) => l.side === "BUY").length;
    const shorts = cfg.legs.filter((l) => l.side === "SELL").length;
    const hasNakedShort = cfg.legs.some(
      (l) => l.side === "SELL" && !cfg.legs.some((o) => o.side === "BUY" && o.optionType === l.optionType)
    );
    const maxProfit = hasNakedShort ? "limited to collected premium" : "defined";
    const maxLoss = hasNakedShort ? "Unlimited (naked short)" : "defined (spread)";
    return `${longs} long / ${shorts} short leg(s) · Max profit ${maxProfit} · Max loss ${maxLoss}`;
  }, [cfg.legs]);

  return (
    <div
      data-testid="option-config-panel"
      style={{ padding: "var(--spacing-2)", display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", height: "100%" }}
    >
      {/* Section 1: Underlying & Expiry */}
      <div style={sectionCard}>
        <div style={sectionTitle}>Underlying &amp; Expiry</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "6px" }}>
          <div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Underlying Symbol</div>
            <input
              list="underlyings-list"
              value={cfg.underlyingSymbol}
              onChange={(e) => setUnderlying(e.target.value)}
              style={{ ...inputStyle, width: "100%" }}
              aria-label="Underlying symbol"
            />
            <datalist id="underlyings-list">
              {UNDERLYINGS.map((u) => (
                <option key={u.symbol} value={u.symbol} />
              ))}
            </datalist>
          </div>
          <div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Segment</div>
            <input value={cfg.underlyingSegment} onChange={(e) => patchCfg({ underlyingSegment: e.target.value })} style={{ ...inputStyle, width: "100%" }} aria-label="Segment" />
          </div>
          <div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Expiry Type</div>
            <select
              value={cfg.expiryRule.type}
              onChange={(e) => patchExpiry({ type: e.target.value as ExpiryType })}
              style={{ ...inputStyle, width: "100%" }}
              aria-label="Expiry type"
            >
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="exact">Exact Date</option>
            </select>
          </div>
          <div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Offset (0 = nearest)</div>
            <input type="number" min={0} value={cfg.expiryRule.offset} onChange={(e) => patchExpiry({ offset: Number(e.target.value) })} style={{ ...inputStyle, width: "100%" }} aria-label="Expiry offset" />
          </div>
          {cfg.expiryRule.type === "exact" && (
            <div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Exact Date</div>
              <input type="date" value={cfg.expiryRule.exactDate ?? ""} onChange={(e) => patchExpiry({ exactDate: e.target.value })} style={{ ...inputStyle, width: "100%" }} aria-label="Exact expiry date" />
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          <button type="button" onClick={() => patchCfg({ expiryRule: { type: "weekly", offset: 0 } })} style={btnStyle}>Current Weekly</button>
          <button type="button" onClick={() => patchCfg({ expiryRule: { type: "weekly", offset: 1 } })} style={btnStyle}>Next Weekly</button>
          <button type="button" onClick={() => patchCfg({ expiryRule: { type: "monthly", offset: 0 } })} style={btnStyle}>Current Monthly</button>
        </div>
      </div>

      {/* Section 3: Templates (presented before legs for easy quick-fill) */}
      <div style={sectionCard}>
        <div style={sectionTitle}>Common Strategy Templates</div>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {TEMPLATES.map((t) => (
            <button
              key={t.label}
              type="button"
              data-testid={`template-${t.label.replace(/\s+/g, "-").toLowerCase()}`}
              onClick={() => applyTemplate(t.make)}
              style={btnStyle}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Section 2: Legs */}
      <div style={sectionCard}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={sectionTitle}>Option Legs ({cfg.legs.length})</div>
          <button type="button" onClick={addLeg} style={primaryBtn}>+ Leg</button>
        </div>

        {cfg.legs.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>No legs defined. Add one or pick a template above.</div>
        )}

        {cfg.legs.map((leg) => (
          <div key={leg.id} data-testid={`leg-${leg.id}`} style={{ ...sectionCard, borderStyle: "dashed" }}>
            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.6875rem", fontWeight: 700 }}>{leg.id}</span>
              <div style={{ display: "flex", gap: "6px" }}>
                {(["CE", "PE"] as const).map((t) => (
                  <label key={t} style={{ fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: "3px" }}>
                    <input type="radio" name={`type-${leg.id}`} checked={leg.optionType === t} onChange={() => updateLeg(leg.id, { optionType: t })} />
                    {t}
                  </label>
                ))}
              </div>
              <div style={{ display: "flex", gap: "6px" }}>
                {(["BUY", "SELL"] as const).map((s) => (
                  <label key={s} style={{ fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: "3px" }}>
                    <input type="radio" name={`side-${leg.id}`} checked={leg.side === s} onChange={() => updateLeg(leg.id, { side: s })} />
                    {s}
                  </label>
                ))}
              </div>
              <input type="number" min={1} value={leg.lots} onChange={(e) => updateLeg(leg.id, { lots: Number(e.target.value) })} style={{ ...inputStyle, width: "70px" }} aria-label={`Lots for ${leg.id}`} />
              <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>lots</span>
              <button type="button" onClick={() => removeLeg(leg.id)} style={{ ...btnStyle, color: "var(--color-down)", marginLeft: "auto" }} aria-label={`Remove ${leg.id}`}>✕</button>
            </div>

            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
              <select
                value={leg.strike.type}
                onChange={(e) => updateStrike(leg.id, e.target.value as StrikeSelectorType)}
                style={inputStyle}
                aria-label={`Strike method for ${leg.id}`}
              >
                <option value="atm">ATM ± Offset</option>
                <option value="delta">By Delta</option>
                <option value="premium">By Premium (₹)</option>
                <option value="absolute">Absolute Strike</option>
              </select>

              {leg.strike.type === "atm" && (
                <>
                  <input
                    type="number"
                    min={-10}
                    max={10}
                    value={leg.strike.offset ?? 0}
                    onChange={(e) => updateStrikeField(leg.id, { offset: Number(e.target.value) })}
                    style={{ ...inputStyle, width: "80px" }}
                    aria-label={`ATM offset for ${leg.id}`}
                  />
                  <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
                    {(() => {
                      const o = leg.strike.offset ?? 0;
                      if (o === 0) return "ATM";
                      const isCe = leg.optionType === "CE";
                      // CE positive offset = OTM; PE negative offset = OTM
                      const otm = (isCe && o > 0) || (!isCe && o < 0);
                      return `${Math.abs(o)} strike${Math.abs(o) === 1 ? "" : "s"} ${otm ? "OTM" : "ITM"}`;
                    })()}
                  </span>
                </>
              )}
              {leg.strike.type === "delta" && (
                <>
                  <input
                    type="number"
                    step={0.01}
                    min={0.01}
                    max={0.99}
                    value={leg.strike.targetDelta ?? 0.3}
                    onChange={(e) => updateStrikeField(leg.id, { targetDelta: Number(e.target.value) })}
                    style={{ ...inputStyle, width: "80px" }}
                    aria-label={`Delta for ${leg.id}`}
                  />
                  <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
                    0.50 ≈ ATM · 0.30 ≈ slight OTM · 0.70 ≈ slight ITM
                  </span>
                </>
              )}
              {leg.strike.type === "premium" && (
                <>
                  <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>₹</span>
                  <input
                    type="number"
                    step={0.5}
                    min={0.5}
                    value={leg.strike.targetPremium ?? 100}
                    onChange={(e) => updateStrikeField(leg.id, { targetPremium: Number(e.target.value) })}
                    style={{ ...inputStyle, width: "100px" }}
                    aria-label={`Premium for ${leg.id}`}
                  />
                </>
              )}
              {leg.strike.type === "absolute" && (
                <input
                  type="number"
                  step={0.05}
                  min={0}
                  value={leg.strike.absoluteStrike ?? 0}
                  onChange={(e) => updateStrikeField(leg.id, { absoluteStrike: Number(e.target.value) })}
                  style={{ ...inputStyle, width: "120px" }}
                  aria-label={`Absolute strike for ${leg.id}`}
                />
              )}
            </div>
          </div>
        ))}

        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", borderTop: "1px dashed var(--border-subtle)", paddingTop: "6px" }}>
          <strong style={{ color: "var(--text-primary)" }}>Payoff:</strong> {payoffSummary}
        </div>
      </div>
    </div>
  );
};
