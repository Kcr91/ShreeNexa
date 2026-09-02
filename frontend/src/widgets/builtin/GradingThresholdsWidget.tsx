import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  GradingConfig,
  GradingThresholdsWidgetSettings,
  HorizonGradingConfig,
  HorizonProfile,
  ScorecardSummary,
} from "../../grading/types";
import {
  DEFAULT_GRADING_CONFIG,
  evaluateScorecard,
  markScorecardsStale,
  regradeScorecards,
  SAMPLE_STRATEGIES,
} from "../../grading/engine";
import { validateHorizonConfig } from "../../grading/validator";

export const GradingThresholdsWidget: React.FC<
  WidgetComponentProps<GradingThresholdsWidgetSettings>
> = ({ settings }) => {
  const [activeConfig, setActiveConfig] = useState<GradingConfig>(DEFAULT_GRADING_CONFIG);
  const [selectedHorizon, setSelectedHorizon] = useState<HorizonProfile>(
    settings?.defaultHorizon || "POSITIONAL"
  );
  const [draftThresholds, setDraftThresholds] = useState<HorizonGradingConfig>(
    DEFAULT_GRADING_CONFIG.horizons.POSITIONAL
  );
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>(
    SAMPLE_STRATEGIES[0].id
  );

  // Scorecards state
  const [scorecards, setScorecards] = useState<ScorecardSummary[]>(() => {
    return SAMPLE_STRATEGIES.map((strat) =>
      evaluateScorecard(
        strat.id,
        strat.name,
        strat.horizon,
        strat.metricValues,
        DEFAULT_GRADING_CONFIG
      )
    );
  });

  const [notification, setNotification] = useState<string | null>(null);

  // Sync draft thresholds when switching horizon
  const handleSelectHorizon = (horizon: HorizonProfile) => {
    setSelectedHorizon(horizon);
    setDraftThresholds(activeConfig.horizons[horizon]);
  };

  // Validation
  const validationErrors = useMemo(() => {
    return validateHorizonConfig(draftThresholds);
  }, [draftThresholds]);

  const isValid = validationErrors.length === 0;

  // Selected strategy for live preview
  const selectedStrategy =
    SAMPLE_STRATEGIES.find((s) => s.id === selectedStrategyId) ||
    SAMPLE_STRATEGIES[0];

  // Active scorecard for this strategy
  const activeScorecard = scorecards.find(
    (sc) => sc.strategyId === selectedStrategy.id
  );

  // Live draft preview scorecard
  const previewScorecard = useMemo(() => {
    return evaluateScorecard(
      selectedStrategy.id,
      selectedStrategy.name,
      selectedHorizon,
      selectedStrategy.metricValues,
      activeConfig,
      draftThresholds
    );
  }, [selectedStrategy, selectedHorizon, activeConfig, draftThresholds]);

  const handleThresholdChange = (
    metricKey: string,
    field: "excellent" | "good" | "acceptable" | "poor" | "weight",
    val: number
  ) => {
    setDraftThresholds((prev) => {
      const band = prev.thresholds[metricKey];
      if (!band) return prev;
      return {
        ...prev,
        thresholds: {
          ...prev.thresholds,
          [metricKey]: {
            ...band,
            [field]: val,
          },
        },
      };
    });
  };

  const handleSaveConfig = () => {
    if (!isValid) return;

    // Increment config version (e.g. v1.0 -> v1.1)
    const currentVerNum = parseFloat(activeConfig.version.replace("v", ""));
    const newVersion = `v${(currentVerNum + 0.1).toFixed(1)}`;

    const newConfig: GradingConfig = {
      version: newVersion,
      updatedAt: new Date().toISOString(),
      horizons: {
        ...activeConfig.horizons,
        [selectedHorizon]: draftThresholds,
      },
    };

    setActiveConfig(newConfig);

    // Strict invariant: Mark existing scorecards as STALE!
    const updatedScorecards = markScorecardsStale(scorecards, newVersion);
    setScorecards(updatedScorecards);

    setNotification(
      `Saved ${newVersion}. Historical scorecards marked STALE. Click "Re-Grade Scorecards" to re-evaluate.`
    );
  };

  const handleRegrade = () => {
    const updated = regradeScorecards(scorecards, activeConfig);
    setScorecards(updated);
    setNotification(
      `All scorecards re-graded to active config ${activeConfig.version}. Status is now CURRENT.`
    );
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        padding: "var(--spacing-2)",
        gap: "var(--spacing-2)",
        fontSize: "var(--font-size-xs)",
      }}
    >
      {/* Top Banner and Actions */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <span style={{ color: "var(--text-muted)" }}>Horizon:</span>
          {(["INTRADAY", "SWING", "POSITIONAL", "INVESTMENT"] as const).map((h) => (
            <button
              key={h}
              type="button"
              data-testid={`horizon-tab-${h.toLowerCase()}`}
              onClick={() => handleSelectHorizon(h)}
              style={{
                padding: "3px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor:
                  selectedHorizon === h ? "var(--color-primary)" : "transparent",
                color: selectedHorizon === h ? "#fff" : "var(--text-primary)",
                border: "1px solid var(--border-default)",
                cursor: "pointer",
              }}
            >
              {h}
            </button>
          ))}
          <span
            data-testid="config-version-tag"
            style={{
              padding: "2px 6px",
              borderRadius: "4px",
              backgroundColor: "rgba(24, 144, 255, 0.2)",
              color: "#1890ff",
              fontWeight: 600,
            }}
          >
            {activeConfig.version}
          </span>
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
          <button
            type="button"
            data-testid="btn-save-thresholds"
            disabled={!isValid}
            onClick={handleSaveConfig}
            style={{
              padding: "4px 10px",
              backgroundColor: isValid ? "var(--color-up)" : "var(--border-default)",
              color: "#fff",
              border: "none",
              borderRadius: "var(--radius-sm)",
              cursor: isValid ? "pointer" : "not-allowed",
              fontWeight: 600,
            }}
          >
            💾 Save Thresholds
          </button>
          <button
            type="button"
            data-testid="btn-regrade-scorecards"
            onClick={handleRegrade}
            style={{
              padding: "4px 10px",
              backgroundColor: "var(--color-primary)",
              color: "#fff",
              border: "none",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            ⚡ Re-Grade Scorecards
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          data-testid="notification-banner"
          style={{
            backgroundColor: "rgba(38, 166, 154, 0.1)",
            border: "1px solid rgba(38, 166, 154, 0.3)",
            padding: "6px 10px",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-up)",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>{notification}</span>
          <button
            type="button"
            onClick={() => setNotification(null)}
            style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Validation Error Banner */}
      {validationErrors.length > 0 && (
        <div
          data-testid="validation-error-banner"
          style={{
            backgroundColor: "rgba(239, 83, 80, 0.1)",
            border: "1px solid rgba(239, 83, 80, 0.3)",
            padding: "6px 10px",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-down)",
          }}
        >
          <strong>⚠️ Validation Error:</strong>
          <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
            {validationErrors.map((err, i) => (
              <li key={i}>{err.message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Main Grid: Thresholds Editor (Left) & Live Scorecard Preview (Right) */}
      <div style={{ flex: 1, display: "flex", gap: "var(--spacing-2)", overflow: "hidden" }}>
        {/* Left: Threshold Bands Editor */}
        <div
          style={{
            flex: 3,
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--spacing-3)",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "var(--spacing-2)",
          }}
        >
          <strong>Metric Threshold Bands ({selectedHorizon})</strong>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
            {Object.entries(draftThresholds.thresholds).map(([key, band]) => (
              <div
                key={key}
                style={{
                  backgroundColor: "var(--bg-active)",
                  padding: "var(--spacing-2)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong>{band.label}</strong>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Weight:</span>
                    <input
                      type="number"
                      aria-label={`${band.label} Weight`}
                      value={band.weight}
                      onChange={(e) =>
                        handleThresholdChange(key, "weight", parseFloat(e.target.value) || 0)
                      }
                      style={{
                        width: "50px",
                        padding: "2px 4px",
                        backgroundColor: "var(--bg-surface)",
                        border: "1px solid var(--border-default)",
                        color: "var(--text-primary)",
                        borderRadius: "var(--radius-sm)",
                        textAlign: "right",
                      }}
                    />
                    <span>%</span>
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(4, 1fr)",
                    gap: "var(--spacing-2)",
                    marginTop: "6px",
                  }}
                >
                  {(["excellent", "good", "acceptable", "poor"] as const).map((gradeKey) => (
                    <div key={gradeKey}>
                      <span style={{ textTransform: "capitalize", color: "var(--text-muted)", fontSize: "0.6875rem" }}>
                        {gradeKey}:
                      </span>
                      <input
                        type="number"
                        step="0.1"
                        aria-label={`${band.label} ${gradeKey}`}
                        value={band[gradeKey]}
                        onChange={(e) =>
                          handleThresholdChange(key, gradeKey, parseFloat(e.target.value) || 0)
                        }
                        style={{
                          width: "100%",
                          padding: "3px 4px",
                          backgroundColor: "var(--bg-surface)",
                          border: "1px solid var(--border-default)",
                          color: "var(--text-primary)",
                          borderRadius: "var(--radius-sm)",
                          marginTop: "2px",
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Live Preview & Scorecards */}
        <div
          style={{
            flex: 2,
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--spacing-3)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--spacing-2)",
            overflowY: "auto",
          }}
        >
          <strong>Live Preview Before Save</strong>
          <select
            value={selectedStrategyId}
            onChange={(e) => setSelectedStrategyId(e.target.value)}
            style={{
              padding: "4px",
              backgroundColor: "var(--bg-active)",
              border: "1px solid var(--border-default)",
              color: "var(--text-primary)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {SAMPLE_STRATEGIES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.horizon})
              </option>
            ))}
          </select>

          {/* Side-by-side active vs preview comparison */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-2)", marginTop: "4px" }}>
            {/* Active Card */}
            <div
              style={{
                backgroundColor: "var(--bg-active)",
                padding: "8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>Active ({activeConfig.version})</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, margin: "4px 0" }}>
                {activeScorecard?.overallGrade || "N/A"}
              </div>
              <div>Score: {activeScorecard?.overallScore || 0} pts</div>
              <div>Verdict: {activeScorecard?.verdict || "N/A"}</div>
              <div style={{ marginTop: "4px" }}>
                <span
                  data-testid="active-scorecard-status"
                  style={{
                    padding: "1px 6px",
                    borderRadius: "4px",
                    fontSize: "0.625rem",
                    backgroundColor:
                      activeScorecard?.status === "CURRENT"
                        ? "rgba(38, 166, 154, 0.2)"
                        : "rgba(250, 173, 20, 0.2)",
                    color:
                      activeScorecard?.status === "CURRENT"
                        ? "var(--color-up)"
                        : "#faad14",
                  }}
                >
                  {activeScorecard?.status || "CURRENT"}
                </span>
              </div>
            </div>

            {/* Preview Card */}
            <div
              style={{
                backgroundColor: "var(--bg-active)",
                padding: "8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-primary)",
              }}
            >
              <div style={{ color: "var(--color-primary)", fontSize: "0.6875rem", fontWeight: 600 }}>Draft Preview</div>
              <div
                data-testid="preview-grade"
                style={{ fontSize: "1.125rem", fontWeight: 700, margin: "4px 0", color: "var(--color-primary)" }}
              >
                {previewScorecard.overallGrade}
              </div>
              <div data-testid="preview-score">Score: {previewScorecard.overallScore} pts</div>
              <div>Verdict: {previewScorecard.verdict}</div>
              <div style={{ marginTop: "4px", fontSize: "0.625rem", color: "var(--text-muted)" }}>
                Δ vs Active: {(previewScorecard.overallScore - (activeScorecard?.overallScore || 0)).toFixed(1)} pts
              </div>
            </div>
          </div>

          <strong style={{ marginTop: "6px" }}>Historical Scorecards Ledger</strong>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {scorecards.map((sc) => (
              <div
                key={sc.strategyId}
                style={{
                  backgroundColor: "var(--bg-active)",
                  padding: "4px 6px",
                  borderRadius: "var(--radius-sm)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: "0.6875rem",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{sc.strategyName}</div>
                  <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)" }}>
                    {sc.horizon} • {sc.configVersion}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <strong>{sc.overallGrade}</strong> ({sc.overallScore} pts)
                  <div>
                    <span
                      style={{
                        padding: "1px 4px",
                        borderRadius: "3px",
                        fontSize: "0.5625rem",
                        backgroundColor:
                          sc.status === "CURRENT"
                            ? "rgba(38, 166, 154, 0.2)"
                            : "rgba(250, 173, 20, 0.2)",
                        color: sc.status === "CURRENT" ? "var(--color-up)" : "#faad14",
                      }}
                    >
                      {sc.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export const gradingThresholdsDefinition: WidgetDefinition<GradingThresholdsWidgetSettings> = {
  id: "grading-thresholds",
  title: "Grading Thresholds",
  description: "Configurable metric grading bands, live preview before save, stale scorecard tracking, and explicit re-grade.",
  category: "analytics",
  icon: "⚖️",
  defaultWidth: 700,
  defaultHeight: 460,
  schema: {
    fields: [
      {
        name: "defaultHorizon",
        label: "Default Horizon Profile",
        type: "string",
        default: "POSITIONAL",
      },
    ],
  },
  component: GradingThresholdsWidget,
};
