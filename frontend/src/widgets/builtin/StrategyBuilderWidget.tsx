import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  StrategyBuilderState,
  StrategyBuilderWidgetSettings,
  VectorBacktestResult,
} from "../../strategybuilder/types";
import {
  compileVisualStateToStrategyIR,
  validateStrategyBuilderState,
  runClientSideVectorBacktest,
} from "../../strategybuilder/compiler";
import { compileVisualToCanonicalIR } from "../../strategybuilder/canonical";
import { AIDraftModal } from "../../strategybuilder/AIDraftModal";
import { createDefaultStrategyState } from "../../strategybuilder/defaults";
import { StrategyMetaPanel } from "../../strategybuilder/panels/StrategyMetaPanel";
import { IndicatorPanel } from "../../strategybuilder/panels/IndicatorPanel";
import { ConditionBuilder } from "../../strategybuilder/panels/ConditionBuilder";
import { RiskSizingPanel } from "../../strategybuilder/panels/RiskSizingPanel";
import { TimeFilterPanel } from "../../strategybuilder/panels/TimeFilterPanel";
import { CandleConditionPanel } from "../../strategybuilder/panels/CandleConditionPanel";
import { BreakoutPanel } from "../../strategybuilder/panels/BreakoutPanel";
import { OptionConfigPanel } from "../../strategybuilder/panels/OptionConfigPanel";
import { runBacktest, BacktestResult } from "../../strategybuilder/backtestService";
import { ApiError } from "../../api/client";

type TabKey = "setup" | "indicators" | "options" | "conditions" | "risk" | "preview";

function tabsForKind(kind: string): { key: TabKey; label: string }[] {
  const base: { key: TabKey; label: string }[] = [
    { key: "setup", label: "Setup" },
    { key: "indicators", label: "Indicators" },
  ];
  if (kind === "option") base.push({ key: "options", label: "Options" });
  base.push(
    { key: "conditions", label: "Conditions" },
    { key: "risk", label: "Risk & Size" },
    { key: "preview", label: "Preview" }
  );
  return base;
}

const SEED_STATE: StrategyBuilderState = {
  ...createDefaultStrategyState(),
  strategyName: "EMA Golden Cross Momentum",
  indicators: [
    { id: "ind-1", name: "fast_ema", function: "ema", params: { period: 9, source: "close" } },
    { id: "ind-2", name: "slow_ema", function: "ema", params: { period: 21, source: "close" } },
    { id: "ind-3", name: "rsi_14", function: "rsi", params: { period: 14 } },
  ],
  rules: [
    {
      id: "rule-entry",
      name: "Long Entry Rule",
      type: "ENTRY_LONG",
      combinator: "AND",
      conditions: [
        { id: "cond-1", leftOperand: "fast_ema", operator: "CROSS_ABOVE", rightOperand: "slow_ema" },
        { id: "cond-2", leftOperand: "rsi_14", operator: "GREATER_THAN", rightOperand: "50" },
      ],
    },
    {
      id: "rule-exit",
      name: "Long Exit Rule",
      type: "EXIT_LONG",
      combinator: "OR",
      conditions: [
        { id: "cond-3", leftOperand: "fast_ema", operator: "CROSS_BELOW", rightOperand: "slow_ema" },
        { id: "cond-4", leftOperand: "rsi_14", operator: "LESS_THAN", rightOperand: "40" },
      ],
    },
  ],
  stopLossPct: 1.5,
  takeProfitPct: 3.5,
};

const EquitySparkline: React.FC<{ points: { timestamp: string; equity: number }[] }> = ({ points }) => {
  if (!points || points.length < 2) {
    return <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Not enough equity points for a curve.</div>;
  }
  const w = 420;
  const h = 60;
  const equities = points.map((p) => p.equity);
  const min = Math.min(...equities);
  const max = Math.max(...equities);
  const range = max - min || 1;
  const stepX = w / (points.length - 1);
  const path = equities
    .map((eq, i) => {
      const x = i * stepX;
      const y = h - ((eq - min) / range) * h;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const last = equities[equities.length - 1];
  const first = equities[0];
  const up = last >= first;
  return (
    <svg data-testid="equity-sparkline" viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: `${h}px` }} preserveAspectRatio="none">
      <path d={path} fill="none" stroke={up ? "var(--color-up)" : "var(--color-down)"} strokeWidth={1.5} />
    </svg>
  );
};

export const StrategyBuilderWidget: React.FC<
  WidgetComponentProps<StrategyBuilderWidgetSettings>
> = ({ settings }) => {
  const [state, setState] = useState<StrategyBuilderState>(() => ({
    ...SEED_STATE,
    universe: settings?.defaultUniverse || SEED_STATE.universe,
  }));
  const [activeTab, setActiveTab] = useState<TabKey>("setup");

  // If the user switches away from option kind while on the Options tab,
  // fall back to Setup so the user is not stranded on a hidden tab.
  React.useEffect(() => {
    if (activeTab === "options" && state.kind !== "option") {
      setActiveTab("setup");
    }
  }, [activeTab, state.kind]);
  const [conditionsSubTab, setConditionsSubTab] = useState<"rules" | "candles" | "time" | "breakout">("rules");
  const [backtestResult, setBacktestResult] = useState<VectorBacktestResult | null>(null);
  const [realBacktest, setRealBacktest] = useState<BacktestResult | null>(null);
  const [isBacktestLoading, setIsBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);

  // Backtest configuration (date range + initial capital)
  const today = new Date();
  const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
  const [backtestStart, setBacktestStart] = useState<string>(oneYearAgo.toISOString().slice(0, 10));
  const [backtestEnd, setBacktestEnd] = useState<string>(today.toISOString().slice(0, 10));
  const [initialCapital, setInitialCapital] = useState<number>(100_000);

  const validation = useMemo(() => validateStrategyBuilderState(state), [state]);

  const canonicalIR = useMemo(
    () => (validation.isValid ? compileVisualToCanonicalIR(state) : null),
    [state, validation.isValid]
  );

  const handleRunBacktest = async () => {
    if (!canonicalIR) return;
    setActiveTab("preview");
    setBacktestError(null);
    setIsBacktestLoading(true);
    try {
      const result = await runBacktest({
        strategyIR: canonicalIR,
        startDate: backtestStart,
        endDate: backtestEnd,
        initialCapital,
        slippagePct: state.slippagePct,
      });
      setRealBacktest(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setBacktestError("Backend not available. Please ensure the server is running.");
      } else if (err instanceof ApiError) {
        setBacktestError(err.message);
      } else {
        setBacktestError("Backtest failed. See console for details.");
      }
    } finally {
      setIsBacktestLoading(false);
    }
  };

  const applyRangePreset = (months: number) => {
    const end = new Date();
    const start = new Date(end.getFullYear(), end.getMonth() - months, end.getDate());
    setBacktestStart(start.toISOString().slice(0, 10));
    setBacktestEnd(end.toISOString().slice(0, 10));
  };

  const handleCopyIR = () => {
    if (!canonicalIR) return;
    navigator.clipboard?.writeText(JSON.stringify(canonicalIR, null, 2));
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        padding: "var(--spacing-2)",
        gap: "var(--spacing-2)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
          gap: "var(--spacing-2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", flex: 1, minWidth: 0 }}>
          <span
            style={{
              fontWeight: 700,
              fontSize: "var(--font-size-sm)",
              color: "var(--text-primary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {state.strategyName || "Untitled Strategy"}
          </span>
          <span
            data-testid="validation-status"
            style={{ fontSize: "10px", color: validation.isValid ? "#34d399" : "#f87171" }}
          >
            {validation.isValid ? "🟢 Valid AST" : "🔴 Invalid AST"}
          </span>
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
          <button
            type="button"
            data-testid="btn-ai-assistant"
            onClick={() => setIsAIModalOpen(true)}
            style={{
              padding: "var(--spacing-1) var(--spacing-3)",
              backgroundColor: "var(--bg-active)",
              color: "var(--color-primary, #3b82f6)",
              border: "1px solid var(--color-primary, #3b82f6)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            ✨ AI Assistant
          </button>

          <button
            type="button"
            onClick={handleRunBacktest}
            disabled={!validation.isValid}
            style={{
              padding: "var(--spacing-1) var(--spacing-3)",
              backgroundColor: validation.isValid ? "var(--color-primary)" : "var(--bg-active)",
              color: validation.isValid ? "var(--text-inverse)" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 700,
              cursor: validation.isValid ? "pointer" : "not-allowed",
            }}
          >
            ⚡ Run Vector Backtest
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="Strategy builder tabs"
        style={{
          display: "flex",
          gap: "4px",
          borderBottom: "1px solid var(--border-subtle)",
          flexWrap: "wrap",
        }}
      >
        {tabsForKind(state.kind).map((tab) => {
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              role="tab"
              aria-selected={active}
              data-testid={`tab-${tab.key}`}
              onClick={() => setActiveTab(tab.key)}
              style={{
                padding: "6px 14px",
                fontSize: "var(--font-size-xs)",
                fontWeight: active ? 700 : 500,
                color: active ? "var(--color-primary)" : "var(--text-muted)",
                background: "transparent",
                border: "none",
                borderBottom: active ? "2px solid var(--color-primary)" : "2px solid transparent",
                cursor: "pointer",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Active panel */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {activeTab === "setup" && <StrategyMetaPanel state={state} onChange={setState} />}
        {activeTab === "indicators" && <IndicatorPanel state={state} onChange={setState} />}
        {activeTab === "options" && state.kind === "option" && (
          <OptionConfigPanel state={state} onChange={setState} />
        )}
        {activeTab === "conditions" && (
          <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
            <div
              role="tablist"
              aria-label="Condition sub-tabs"
              style={{
                display: "flex",
                gap: "2px",
                padding: "4px var(--spacing-2) 0",
                borderBottom: "1px solid var(--border-subtle)",
              }}
            >
              {([
                { key: "rules", label: "Rules" },
                { key: "candles", label: "Candles" },
                { key: "time", label: "Time" },
                { key: "breakout", label: "Breakout" },
              ] as const).map((s) => {
                const active = conditionsSubTab === s.key;
                return (
                  <button
                    key={s.key}
                    role="tab"
                    aria-selected={active}
                    data-testid={`subtab-${s.key}`}
                    onClick={() => setConditionsSubTab(s.key)}
                    style={{
                      padding: "4px 10px",
                      fontSize: "0.6875rem",
                      fontWeight: active ? 700 : 500,
                      color: active ? "var(--color-primary)" : "var(--text-muted)",
                      background: "transparent",
                      border: "none",
                      borderBottom: active ? "2px solid var(--color-primary)" : "2px solid transparent",
                      cursor: "pointer",
                    }}
                  >
                    {s.label}
                  </button>
                );
              })}
            </div>
            <div style={{ flex: 1, overflow: "hidden" }}>
              {conditionsSubTab === "rules" && <ConditionBuilder state={state} onChange={setState} />}
              {conditionsSubTab === "candles" && <CandleConditionPanel state={state} onChange={setState} />}
              {conditionsSubTab === "time" && <TimeFilterPanel state={state} onChange={setState} />}
              {conditionsSubTab === "breakout" && <BreakoutPanel state={state} onChange={setState} />}
            </div>
          </div>
        )}
        {activeTab === "risk" && <RiskSizingPanel state={state} onChange={setState} />}
        {activeTab === "preview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", padding: "var(--spacing-2)", height: "100%", overflow: "hidden" }}>
            {/* Backtest configuration */}
            <div
              data-testid="backtest-config"
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-2)",
                fontSize: "0.6875rem",
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                alignItems: "center",
              }}
            >
              <label style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                Start
                <input type="date" value={backtestStart} onChange={(e) => setBacktestStart(e.target.value)} style={{ fontSize: "0.6875rem", padding: "2px 4px" }} aria-label="Backtest start date" />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                End
                <input type="date" value={backtestEnd} onChange={(e) => setBacktestEnd(e.target.value)} style={{ fontSize: "0.6875rem", padding: "2px 4px" }} aria-label="Backtest end date" />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                Capital ₹
                <input type="number" min={1000} step={1000} value={initialCapital} onChange={(e) => setInitialCapital(Number(e.target.value))} style={{ fontSize: "0.6875rem", padding: "2px 4px", width: "100px" }} aria-label="Initial capital" />
              </label>
              <div style={{ display: "flex", gap: "4px", marginLeft: "auto" }}>
                {[
                  { label: "1M", m: 1 },
                  { label: "3M", m: 3 },
                  { label: "6M", m: 6 },
                  { label: "1Y", m: 12 },
                  { label: "2Y", m: 24 },
                ].map((p) => (
                  <button key={p.label} type="button" onClick={() => applyRangePreset(p.m)} style={{ padding: "2px 6px", fontSize: "0.625rem", cursor: "pointer", backgroundColor: "var(--bg-active)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-sm)" }}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {isBacktestLoading && (
              <div data-testid="backtest-loading" style={{ padding: "var(--spacing-2)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                Running backtest…
              </div>
            )}

            {backtestError && (
              <div
                data-testid="backtest-error"
                style={{
                  padding: "var(--spacing-2)",
                  color: "var(--color-down)",
                  backgroundColor: "var(--color-down-bg)",
                  border: "1px solid var(--color-down)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.6875rem",
                }}
              >
                {backtestError}
              </div>
            )}

            {realBacktest && !isBacktestLoading && (
              <div
                data-testid="backtest-result-card"
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: `1px solid ${realBacktest.metrics.total_return_pct >= 0 ? "var(--color-up)" : "var(--color-down)"}`,
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-2)",
                  fontSize: "var(--font-size-xs)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                <strong style={{ color: realBacktest.metrics.total_return_pct >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                  {realBacktest.metrics.total_return_pct >= 0 ? "✓" : "✗"} Backtest Complete ({realBacktest.metrics.total_return_pct.toFixed(2)}%)
                </strong>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "4px", fontSize: "0.6875rem" }}>
                  <div>Win Rate: <strong>{realBacktest.metrics.win_rate_pct.toFixed(1)}%</strong></div>
                  <div>Trades: <strong>{realBacktest.metrics.total_trades}</strong></div>
                  <div>Sharpe: <strong>{realBacktest.metrics.sharpe_ratio.toFixed(2)}</strong></div>
                  <div>Max DD: <strong>-{realBacktest.metrics.max_drawdown_pct.toFixed(2)}%</strong></div>
                  <div>Profit Factor: <strong>{realBacktest.metrics.profit_factor.toFixed(2)}</strong></div>
                  <div>Final Equity: <strong>₹{realBacktest.metrics.final_equity.toLocaleString("en-IN")}</strong></div>
                </div>
                <EquitySparkline points={realBacktest.equity_curve} />
                {realBacktest.trades.length > 0 && (
                  <details style={{ fontSize: "0.6875rem" }}>
                    <summary style={{ cursor: "pointer" }}>Trades ({realBacktest.trades.length})</summary>
                    <div style={{ maxHeight: "160px", overflowY: "auto", marginTop: "4px" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.625rem" }}>
                        <thead>
                          <tr style={{ color: "var(--text-muted)" }}>
                            <th style={{ textAlign: "left" }}>Time</th>
                            <th style={{ textAlign: "left" }}>Sym</th>
                            <th style={{ textAlign: "left" }}>Side</th>
                            <th style={{ textAlign: "right" }}>Qty</th>
                            <th style={{ textAlign: "right" }}>Price</th>
                          </tr>
                        </thead>
                        <tbody>
                          {realBacktest.trades.slice(0, 100).map((t) => (
                            <tr key={t.fill_id}>
                              <td>{t.timestamp.slice(0, 16).replace("T", " ")}</td>
                              <td>{t.security_id}</td>
                              <td style={{ color: t.side === "BUY" ? "var(--color-up)" : "var(--color-down)" }}>{t.side}</td>
                              <td style={{ textAlign: "right" }}>{t.quantity}</td>
                              <td style={{ textAlign: "right" }}>{t.price.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}
              </div>
            )}

            {backtestResult && !realBacktest && !isBacktestLoading && (
              <div
                data-testid="backtest-result-card"
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--color-up)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-2)",
                  fontSize: "var(--font-size-xs)",
                }}
              >
                <strong style={{ color: "var(--color-up)", display: "block", marginBottom: "4px" }}>
                  ✓ Backtest Complete (+{backtestResult.netReturnPct}%)
                </strong>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px", fontSize: "0.6875rem" }}>
                  <div>Win Rate: <strong>{backtestResult.winRatePct}%</strong></div>
                  <div>Trades: <strong>{backtestResult.totalTrades}</strong></div>
                  <div>Sharpe: <strong>{backtestResult.sharpeRatio}</strong></div>
                  <div>Max DD: <strong>-{backtestResult.maxDrawdownPct}%</strong></div>
                </div>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ fontSize: "var(--font-size-xs)" }}>Canonical StrategyIR (AST)</strong>
              <div style={{ display: "flex", gap: "4px" }}>
                <span style={{ fontSize: "10px", color: validation.isValid ? "#34d399" : "#f87171" }}>
                  {validation.isValid ? "🟢 Valid AST" : "🔴 Invalid AST"}
                </span>
                <button
                  onClick={handleCopyIR}
                  style={{
                    fontSize: "10px",
                    padding: "1px 4px",
                    backgroundColor: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "2px",
                    cursor: "pointer",
                    color: "var(--text-primary)",
                  }}
                >
                  Copy IR
                </button>
              </div>
            </div>
            <pre
              data-testid="strategy-ir-preview"
              style={{
                flex: 1,
                backgroundColor: "var(--bg-active)",
                color: "var(--text-secondary)",
                padding: "var(--spacing-2)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.625rem",
                fontFamily: "var(--font-family-mono)",
                overflow: "auto",
                margin: 0,
              }}
            >
              {canonicalIR ? JSON.stringify(canonicalIR, null, 2) : "Invalid Strategy State"}
            </pre>
          </div>
        )}
      </div>

      <AIDraftModal
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
        currentState={state}
        onApprove={(draftState) => {
          setState(draftState);
          setIsAIModalOpen(false);
        }}
        onApproveAndBacktest={(draftState) => {
          setState(draftState);
          setIsAIModalOpen(false);
          const ir = compileVisualStateToStrategyIR(draftState);
          if (ir) {
            setBacktestResult(runClientSideVectorBacktest(ir));
          }
        }}
      />
    </div>
  );
};

export const strategyBuilderDefinition: WidgetDefinition<StrategyBuilderWidgetSettings> = {
  id: "strategy-builder",
  title: "Visual Strategy Builder",
  description: "Block-based StrategyIR rule composer and instant vector backtest runner.",
  category: "analytics",
  icon: "🧱",
  defaultWidth: 700,
  defaultHeight: 450,
  schema: {
    fields: [
      {
        name: "showJsonPreview",
        label: "Show StrategyIR Preview",
        type: "boolean",
        default: true,
      },
      {
        name: "defaultUniverse",
        label: "Default Universe",
        type: "string",
        default: "NIFTY 50",
      },
    ],
  },
  component: StrategyBuilderWidget,
};
