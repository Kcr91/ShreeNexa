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
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);

  const validation = useMemo(() => validateStrategyBuilderState(state), [state]);

  const compiledIR = useMemo(() => {
    if (!validation.isValid) return null;
    return compileVisualStateToStrategyIR(state);
  }, [state, validation.isValid]);

  const canonicalIR = useMemo(
    () => (validation.isValid ? compileVisualToCanonicalIR(state) : null),
    [state, validation.isValid]
  );

  const handleRunBacktest = () => {
    if (!compiledIR) return;
    setBacktestResult(runClientSideVectorBacktest(compiledIR));
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
            {backtestResult && (
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
