import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  StrategyBuilderState,
  StrategyBuilderWidgetSettings,
  IndicatorNode,
  VectorBacktestResult,
} from "../../strategybuilder/types";
import {
  compileVisualStateToStrategyIR,
  validateStrategyBuilderState,
  runClientSideVectorBacktest,
} from "../../strategybuilder/compiler";

const DEFAULT_STATE: StrategyBuilderState = {
  strategyName: "EMA Golden Cross Momentum",
  universe: "NIFTY 50",
  timeframe: "15m",
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
    ...DEFAULT_STATE,
    universe: settings?.defaultUniverse || DEFAULT_STATE.universe,
  }));
  const [backtestResult, setBacktestResult] = useState<VectorBacktestResult | null>(null);

  const validation = useMemo(() => {
    return validateStrategyBuilderState(state);
  }, [state]);

  const compiledIR = useMemo(() => {
    if (!validation.isValid) return null;
    return compileVisualStateToStrategyIR(state);
  }, [state, validation.isValid]);

  const handleAddIndicator = (fn: "ema" | "sma" | "rsi" | "macd") => {
    const count = state.indicators.filter((i) => i.function === fn).length + 1;
    const newInd: IndicatorNode = {
      id: `ind-${Date.now()}`,
      name: `${fn}_${count}`,
      function: fn,
      params: fn === "rsi" ? { period: 14 } : { period: 20, source: "close" },
    };
    setState((prev) => ({ ...prev, indicators: [...prev.indicators, newInd] }));
  };

  const handleRemoveIndicator = (id: string) => {
    setState((prev) => ({
      ...prev,
      indicators: prev.indicators.filter((i) => i.id !== id),
    }));
  };

  const handleRunBacktest = () => {
    if (!compiledIR) return;
    const res = runClientSideVectorBacktest(compiledIR);
    setBacktestResult(res);
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Header & Strategy Meta Strip */}
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
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <input
            aria-label="Strategy Name"
            type="text"
            value={state.strategyName}
            onChange={(e) => setState({ ...state, strategyName: e.target.value })}
            style={{
              fontWeight: 700,
              fontSize: "var(--font-size-sm)",
              backgroundColor: "var(--bg-active)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "2px 6px",
            }}
          />

          <select
            aria-label="Universe"
            value={state.universe}
            onChange={(e) => setState({ ...state, universe: e.target.value })}
            style={{
              backgroundColor: "var(--bg-active)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "2px 6px",
            }}
          >
            <option value="NIFTY 50">NIFTY 50</option>
            <option value="BANKNIFTY">BANKNIFTY</option>
            <option value="NIFTY IT">NIFTY IT</option>
          </select>

          <select
            aria-label="Timeframe"
            value={state.timeframe}
            onChange={(e) => setState({ ...state, timeframe: e.target.value })}
            style={{
              backgroundColor: "var(--bg-active)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "2px 6px",
            }}
          >
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="1d">1d</option>
          </select>
        </div>

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

      {/* Main 3-Column Layout */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "220px 1fr 280px", gap: "var(--spacing-2)", overflow: "hidden" }}>
        {/* Left Column: Indicator Pipeline */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", borderRight: "1px solid var(--border-subtle)", paddingRight: "var(--spacing-2)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: "var(--font-size-xs)" }}>Indicators</strong>
            <div style={{ display: "flex", gap: "2px" }}>
              <button
                type="button"
                onClick={() => handleAddIndicator("ema")}
                style={{ padding: "1px 4px", fontSize: "0.625rem", cursor: "pointer" }}
              >
                +EMA
              </button>
              <button
                type="button"
                onClick={() => handleAddIndicator("rsi")}
                style={{ padding: "1px 4px", fontSize: "0.625rem", cursor: "pointer" }}
              >
                +RSI
              </button>
            </div>
          </div>

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
                onClick={() => handleRemoveIndicator(ind.id)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Center Column: Rule Blocks */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", padding: "0 var(--spacing-1)" }}>
          <strong style={{ fontSize: "var(--font-size-xs)" }}>Logic Rule Blocks</strong>
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <strong>{rule.name}</strong>
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
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {rule.conditions.map((cond, cIdx) => (
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
                      fontFamily: "var(--font-family-mono)",
                    }}
                  >
                    {cIdx > 0 && <span style={{ color: "var(--color-primary)", fontWeight: "bold" }}>{rule.combinator}</span>}
                    <span>{cond.leftOperand}</span>
                    <strong style={{ color: "var(--color-up)" }}>{cond.operator}</strong>
                    <span>{cond.rightOperand}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Risk Control Sliders */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--spacing-2)",
              fontSize: "var(--font-size-xs)",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <div>
              <span style={{ color: "var(--text-muted)" }}>Stop Loss: </span>
              <strong>{state.stopLossPct}%</strong>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)" }}>Take Profit: </span>
              <strong>{state.takeProfitPct}%</strong>
            </div>
          </div>
        </div>

        {/* Right Column: IR JSON Preview & Backtest Results */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflowY: "auto", borderLeft: "1px solid var(--border-subtle)", paddingLeft: "var(--spacing-2)" }}>
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

          <strong style={{ fontSize: "var(--font-size-xs)" }}>StrategyIR JSON Schema</strong>
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
            {compiledIR ? JSON.stringify(compiledIR, null, 2) : "Invalid Strategy State"}
          </pre>
        </div>
      </div>
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
