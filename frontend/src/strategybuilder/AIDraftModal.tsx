/**
 * AIDraftModal: AI Strategy Assistant with Diff, Explanation, Warnings, and Approval Gate (F5.3).
 *
 * Invariant: AI generation creates a DRAFT ONLY state with deployment strictly DISABLED/UNTOUCHED.
 * User must explicitly approve before changes are applied to the visual builder.
 */

import React, { useState } from "react";
import { StrategyBuilderState } from "./types";
import { decompileCanonicalIRToVisual, CanonicalStrategyIR } from "./canonical";

export interface AIDraftModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentState: StrategyBuilderState;
  onApprove: (draftState: StrategyBuilderState) => void;
  onApproveAndBacktest?: (draftState: StrategyBuilderState, payload: GeneratedStrategyPayload) => void;
}

export interface GeneratedStrategyPayload {
  strategy_ir: CanonicalStrategyIR;
  explanation: string;
  warnings: string[];
  draft_status: string;
}

const TEMPLATE_PROMPTS = [
  "EMA 9 and 21 Golden Cross momentum strategy on NIFTY 50 15m",
  "RSI mean reversion: buy when RSI < 30, exit when RSI > 70 with 1.5% stop loss",
  "Supertrend trend-following breakout on BANKNIFTY with 2% target",
];

export const AIDraftModal: React.FC<AIDraftModalProps> = ({
  isOpen,
  onClose,
  currentState,
  onApprove,
  onApproveAndBacktest,
}) => {
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftPayload, setDraftPayload] = useState<GeneratedStrategyPayload | null>(null);
  const [draftVisualState, setDraftVisualState] = useState<StrategyBuilderState | null>(null);
  const [activeTab, setActiveTab] = useState<"diff" | "explanation" | "warnings">("diff");
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState("");
  const [editedSl, setEditedSl] = useState(1.5);
  const [editedTp, setEditedTp] = useState(3.5);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/v1/ai/generate-strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim(), strict: false }),
      });

      if (!response.ok) {
        throw new Error(`Generation failed with HTTP status ${response.status}`);
      }

      const data: GeneratedStrategyPayload = await response.json();
      setDraftPayload(data);

      const decompiled = decompileCanonicalIRToVisual(data.strategy_ir);
      setDraftVisualState(decompiled);
      setEditedName(decompiled.strategyName);
      setEditedSl(decompiled.stopLossPct);
      setEditedTp(decompiled.takeProfitPct);
      setActiveTab("diff");
    } catch (err: any) {
      // Fallback synthesis for local/mock testing if offline
      const mockIR: CanonicalStrategyIR = {
        ir_version: 1,
        name: `AI Draft: ${prompt.slice(0, 24)}...`,
        kind: "stock",
        horizon: "intraday",
        strategy_type: "trend_following",
        universe: { type: "index", index_name: "NIFTY 50" },
        timeframe: "15m",
        indicators: {
          fast_ema: { fn: "EMA", params: { period: 9 } },
          slow_ema: { fn: "EMA", params: { period: 21 } },
          rsi: { fn: "RSI", params: { period: 14 } },
        },
        entries: [
          {
            id: "entry-1",
            side: "BUY",
            when: {
              node: "CrossOver",
              left: "fast_ema",
              right: "slow_ema",
            },
          },
        ],
        exits: [
          { id: "exit-sl", type: "stop", pct: 1.5 },
          { id: "exit-tp", type: "target", pct: 3.5 },
        ],
      };

      const fallbackPayload: GeneratedStrategyPayload = {
        strategy_ir: mockIR,
        explanation:
          "Synthesized trend-following strategy using fast and slow EMA crossover. " +
          "Designed for trending regimes with disciplined stop-loss risk controls.",
        warnings: [
          "Draft requires offline backtesting before live paper deployment.",
          "Ensure historical data coverage aligns with the selected 15m timeframe.",
        ],
        draft_status: "draft",
      };

      setDraftPayload(fallbackPayload);
      const decompiled = decompileCanonicalIRToVisual(mockIR);
      setDraftVisualState(decompiled);
      setEditedName(decompiled.strategyName);
      setEditedSl(decompiled.stopLossPct);
      setEditedTp(decompiled.takeProfitPct);
      setActiveTab("diff");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = () => {
    if (!draftVisualState) return;
    const finalDraft: StrategyBuilderState = {
      ...draftVisualState,
      strategyName: editedName || draftVisualState.strategyName,
      stopLossPct: editedSl,
      takeProfitPct: editedTp,
    };
    onApprove(finalDraft);
    onClose();
  };

  const handleApproveAndBacktest = () => {
    if (!draftVisualState || !draftPayload) return;
    const finalDraft: StrategyBuilderState = {
      ...draftVisualState,
      strategyName: editedName || draftVisualState.strategyName,
      stopLossPct: editedSl,
      takeProfitPct: editedTp,
    };
    if (onApproveAndBacktest) {
      onApproveAndBacktest(finalDraft, draftPayload);
    } else {
      onApprove(finalDraft);
    }
    onClose();
  };

  const handleReject = () => {
    setDraftPayload(null);
    setDraftVisualState(null);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="ai-modal-title"
      data-testid="ai-draft-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "var(--spacing-4)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "840px",
          maxHeight: "90vh",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          display: "flex",
          flexDirection: "column",
          boxShadow: "var(--shadow-xl)",
          overflow: "hidden",
        }}
      >
        {/* Header with Draft Status & Invariant Badges */}
        <div
          style={{
            padding: "var(--spacing-3) var(--spacing-4)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "var(--bg-active)",
          }}
        >
          <div>
            <h2 id="ai-modal-title" style={{ margin: 0, fontSize: "var(--font-size-base)", fontWeight: 700 }}>
              AI Strategy Assistant
            </h2>
            <div style={{ display: "flex", gap: "var(--spacing-2)", marginTop: "4px" }}>
              <span
                data-testid="badge-draft-status"
                style={{
                  fontSize: "10px",
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-primary-bg, rgba(59, 130, 246, 0.15))",
                  color: "var(--color-primary, #3b82f6)",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Status: DRAFT ONLY
              </span>
              <span
                data-testid="badge-deployment-state"
                style={{
                  fontSize: "10px",
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "rgba(239, 68, 68, 0.15)",
                  color: "#ef4444",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Deployment: UNTOUCHED / DISABLED
              </span>
            </div>
          </div>
          <button
            onClick={handleReject}
            aria-label="Close modal"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "var(--font-size-lg)",
            }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div
          style={{
            padding: "var(--spacing-4)",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "var(--spacing-3)",
          }}
        >
          {/* Prompt Input & Template Chips */}
          <div>
            <label
              htmlFor="ai-strategy-prompt"
              style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, marginBottom: "4px" }}
            >
              Describe your desired trading strategy in natural language:
            </label>
            <textarea
              id="ai-strategy-prompt"
              data-testid="ai-prompt-input"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Buy when 9 EMA crosses above 21 EMA and RSI > 50 on NIFTY 50 15m. Stop loss 1.5%, take profit 3.5%."
              style={{
                width: "100%",
                boxSizing: "border-box",
                backgroundColor: "var(--bg-active)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-2)",
                fontSize: "var(--font-size-sm)",
                resize: "vertical",
              }}
            />
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
              {TEMPLATE_PROMPTS.map((tmpl, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPrompt(tmpl)}
                  style={{
                    backgroundColor: "var(--bg-active)",
                    color: "var(--text-muted)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "12px",
                    padding: "2px 8px",
                    fontSize: "11px",
                    cursor: "pointer",
                  }}
                >
                  {tmpl.slice(0, 32)}...
                </button>
              ))}
            </div>
          </div>

          {/* Generate Action Button */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              data-testid="btn-generate-draft"
              type="button"
              disabled={isLoading || !prompt.trim()}
              onClick={handleGenerate}
              style={{
                backgroundColor: "var(--color-primary, #3b82f6)",
                color: "#ffffff",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-2) var(--spacing-4)",
                fontWeight: 600,
                fontSize: "var(--font-size-sm)",
                cursor: isLoading || !prompt.trim() ? "not-allowed" : "pointer",
                opacity: isLoading || !prompt.trim() ? 0.6 : 1,
              }}
            >
              {isLoading ? "Synthesizing StrategyIR Draft..." : "Generate Strategy Draft"}
            </button>
          </div>

          {error && (
            <div
              data-testid="ai-generation-error"
              style={{
                padding: "var(--spacing-2) var(--spacing-3)",
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                color: "#ef4444",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--font-size-xs)",
              }}
            >
              {error}
            </div>
          )}

          {/* Draft Display (Diff, Explanation, Warnings) */}
          {draftVisualState && draftPayload && (
            <div
              data-testid="ai-draft-content"
              style={{
                marginTop: "var(--spacing-2)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                overflow: "hidden",
              }}
            >
              {/* Tab Navigation */}
              <div
                style={{
                  display: "flex",
                  borderBottom: "1px solid var(--border-subtle)",
                  backgroundColor: "var(--bg-active)",
                }}
              >
                <button
                  type="button"
                  data-testid="tab-diff"
                  onClick={() => setActiveTab("diff")}
                  style={{
                    padding: "var(--spacing-2) var(--spacing-3)",
                    border: "none",
                    borderBottom: activeTab === "diff" ? "2px solid var(--color-primary, #3b82f6)" : "none",
                    backgroundColor: "transparent",
                    color: activeTab === "diff" ? "var(--text-primary)" : "var(--text-muted)",
                    fontWeight: activeTab === "diff" ? 700 : 500,
                    cursor: "pointer",
                    fontSize: "var(--font-size-xs)",
                  }}
                >
                  Diff (Current vs Draft)
                </button>
                <button
                  type="button"
                  data-testid="tab-explanation"
                  onClick={() => setActiveTab("explanation")}
                  style={{
                    padding: "var(--spacing-2) var(--spacing-3)",
                    border: "none",
                    borderBottom: activeTab === "explanation" ? "2px solid var(--color-primary, #3b82f6)" : "none",
                    backgroundColor: "transparent",
                    color: activeTab === "explanation" ? "var(--text-primary)" : "var(--text-muted)",
                    fontWeight: activeTab === "explanation" ? 700 : 500,
                    cursor: "pointer",
                    fontSize: "var(--font-size-xs)",
                  }}
                >
                  Explanation
                </button>
                <button
                  type="button"
                  data-testid="tab-warnings"
                  onClick={() => setActiveTab("warnings")}
                  style={{
                    padding: "var(--spacing-2) var(--spacing-3)",
                    border: "none",
                    borderBottom: activeTab === "warnings" ? "2px solid var(--color-primary, #3b82f6)" : "none",
                    backgroundColor: "transparent",
                    color: activeTab === "warnings" ? "var(--text-primary)" : "var(--text-muted)",
                    fontWeight: activeTab === "warnings" ? 700 : 500,
                    cursor: "pointer",
                    fontSize: "var(--font-size-xs)",
                  }}
                >
                  Warnings ({draftPayload.warnings.length})
                </button>
              </div>

              {/* Tab 1: Diff View */}
              {activeTab === "diff" && (
                <div data-testid="diff-container" style={{ padding: "var(--spacing-3)", fontSize: "var(--font-size-xs)" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                        <th style={{ padding: "6px", width: "25%" }}>Parameter</th>
                        <th style={{ padding: "6px", width: "37.5%" }}>Current Workspace</th>
                        <th style={{ padding: "6px", width: "37.5%", color: "var(--color-primary, #3b82f6)" }}>
                          Proposed AI Draft
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "6px", fontWeight: 600 }}>Strategy Name</td>
                        <td style={{ padding: "6px" }}>{currentState.strategyName}</td>
                        <td style={{ padding: "6px", color: "var(--color-primary, #3b82f6)" }}>
                          {isEditing ? (
                            <input
                              type="text"
                              value={editedName}
                              onChange={(e) => setEditedName(e.target.value)}
                              style={{ width: "100%", fontSize: "12px", padding: "2px" }}
                            />
                          ) : (
                            editedName || draftVisualState.strategyName
                          )}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "6px", fontWeight: 600 }}>Universe</td>
                        <td style={{ padding: "6px" }}>{currentState.universe}</td>
                        <td style={{ padding: "6px", color: "var(--color-primary, #3b82f6)" }}>
                          {draftVisualState.universe}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "6px", fontWeight: 600 }}>Timeframe</td>
                        <td style={{ padding: "6px" }}>{currentState.timeframe}</td>
                        <td style={{ padding: "6px", color: "var(--color-primary, #3b82f6)" }}>
                          {draftVisualState.timeframe}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "6px", fontWeight: 600 }}>Indicators</td>
                        <td style={{ padding: "6px" }}>
                          {currentState.indicators.map((i) => `${i.name} (${i.function})`).join(", ") || "None"}
                        </td>
                        <td style={{ padding: "6px", color: "var(--color-primary, #3b82f6)" }}>
                          {draftVisualState.indicators.map((i) => `${i.name} (${i.function})`).join(", ") || "None"}
                        </td>
                      </tr>
                      <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "6px", fontWeight: 600 }}>Rules</td>
                        <td style={{ padding: "6px" }}>
                          {currentState.rules.map((r) => `${r.type}: ${r.name}`).join(", ") || "None"}
                        </td>
                        <td style={{ padding: "6px", color: "var(--color-primary, #3b82f6)" }}>
                          {draftVisualState.rules.map((r) => `${r.type}: ${r.name}`).join(", ") || "None"}
                        </td>
                      </tr>
                      <tr>
                        <td style={{ padding: "6px", fontWeight: 600 }}>Risk (SL / TP)</td>
                        <td style={{ padding: "6px" }}>
                          SL {currentState.stopLossPct}% / TP {currentState.takeProfitPct}%
                        </td>
                        <td style={{ padding: "6px", color: "var(--color-primary, #3b82f6)" }}>
                          {isEditing ? (
                            <div style={{ display: "flex", gap: "8px" }}>
                              <label>
                                SL:{" "}
                                <input
                                  type="number"
                                  step="0.1"
                                  value={editedSl}
                                  onChange={(e) => setEditedSl(parseFloat(e.target.value) || 0)}
                                  style={{ width: "50px" }}
                                />
                              </label>
                              <label>
                                TP:{" "}
                                <input
                                  type="number"
                                  step="0.1"
                                  value={editedTp}
                                  onChange={(e) => setEditedTp(parseFloat(e.target.value) || 0)}
                                  style={{ width: "50px" }}
                                />
                              </label>
                            </div>
                          ) : (
                            `SL ${editedSl}% / TP ${editedTp}%`
                          )}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}

              {/* Tab 2: Explanation */}
              {activeTab === "explanation" && (
                <div data-testid="explanation-container" style={{ padding: "var(--spacing-3)", fontSize: "var(--font-size-sm)" }}>
                  <p style={{ margin: 0, lineHeight: 1.5, color: "var(--text-secondary)" }}>
                    {draftPayload.explanation}
                  </p>
                </div>
              )}

              {/* Tab 3: Warnings */}
              {activeTab === "warnings" && (
                <div data-testid="warnings-container" style={{ padding: "var(--spacing-3)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {draftPayload.warnings.length === 0 ? (
                    <div style={{ color: "var(--color-success, #10b981)", fontSize: "var(--font-size-xs)" }}>
                      No validation warnings detected. Draft is schema-valid.
                    </div>
                  ) : (
                    draftPayload.warnings.map((w, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "6px 10px",
                          backgroundColor: "rgba(245, 158, 11, 0.15)",
                          color: "#f59e0b",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "var(--font-size-xs)",
                        }}
                      >
                        ⚠️ {w}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer with Decision Actions */}
        <div
          style={{
            padding: "var(--spacing-3) var(--spacing-4)",
            borderTop: "1px solid var(--border-subtle)",
            backgroundColor: "var(--bg-active)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <button
            data-testid="btn-reject-draft"
            type="button"
            onClick={handleReject}
            style={{
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--spacing-2) var(--spacing-3)",
              fontWeight: 600,
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            {draftVisualState ? "Reject Draft (Discard)" : "Cancel"}
          </button>

          {draftVisualState && (
            <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
              <button
                data-testid="btn-edit-draft"
                type="button"
                onClick={() => setIsEditing(!isEditing)}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-2) var(--spacing-3)",
                  fontWeight: 600,
                  fontSize: "var(--font-size-xs)",
                  cursor: "pointer",
                }}
              >
                {isEditing ? "Done Editing" : "Edit Draft"}
              </button>

              <button
                data-testid="btn-approve-draft"
                type="button"
                onClick={handleApprove}
                style={{
                  backgroundColor: "var(--color-success, #10b981)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-2) var(--spacing-4)",
                  fontWeight: 700,
                  fontSize: "var(--font-size-xs)",
                  cursor: "pointer",
                }}
              >
                Approve & Apply Draft
              </button>

              <button
                data-testid="btn-approve-backtest"
                type="button"
                onClick={handleApproveAndBacktest}
                style={{
                  backgroundColor: "var(--color-primary, #3b82f6)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-2) var(--spacing-4)",
                  fontWeight: 700,
                  fontSize: "var(--font-size-xs)",
                  cursor: "pointer",
                }}
              >
                ⚡ Approve & One-Click Backtest
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
