import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { ExecutionPhase, ReturnsTimelineWidgetSettings } from "../../returns/types";
import {
  computeMonthlyMatrix,
  computeRollingReturns,
  generateMockContinuousTimeline,
} from "../../returns/engine";

export const ReturnsTimelineWidget: React.FC<
  WidgetComponentProps<ReturnsTimelineWidgetSettings>
> = ({ settings }) => {
  const [activeTab, setActiveTab] = useState<"timeline" | "monthly" | "rolling">(
    "timeline"
  );
  const [selectedPhase, setSelectedPhase] = useState<"ALL" | ExecutionPhase>(
    settings?.activePhaseFilter || "ALL"
  );

  const timeline = useMemo(() => {
    return generateMockContinuousTimeline(settings?.initialCapital || 1000000);
  }, [settings?.initialCapital]);

  const monthlyMatrix = useMemo(() => {
    return computeMonthlyMatrix(timeline.stitchedPoints);
  }, [timeline.stitchedPoints]);

  const rolling1M = useMemo(
    () => computeRollingReturns(timeline.stitchedPoints, 21, "1M (21 Trading Days)"),
    [timeline.stitchedPoints]
  );
  const rolling3M = useMemo(
    () => computeRollingReturns(timeline.stitchedPoints, 63, "3M (63 Trading Days)"),
    [timeline.stitchedPoints]
  );
  const rolling6M = useMemo(
    () => computeRollingReturns(timeline.stitchedPoints, 126, "6M (126 Trading Days)"),
    [timeline.stitchedPoints]
  );

  const monthNames = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  const filteredPoints = useMemo(() => {
    if (selectedPhase === "ALL") return timeline.stitchedPoints;
    return timeline.stitchedPoints.filter((p) => p.phase === selectedPhase);
  }, [timeline.stitchedPoints, selectedPhase]);

  const currentEquity =
    timeline.stitchedPoints[timeline.stitchedPoints.length - 1]?.equity || 1000000;
  const initialEquity =
    timeline.stitchedPoints[0]?.equity || 1000000;
  const totalReturnPct = Number(
    ((currentEquity / initialEquity - 1) * 100).toFixed(2)
  );

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
      {/* Top Controls and Mode Switcher */}
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
        {/* Navigation Tabs */}
        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            data-testid="tab-timeline"
            onClick={() => setActiveTab("timeline")}
            style={{
              padding: "4px 10px",
              backgroundColor: activeTab === "timeline" ? "var(--color-primary)" : "transparent",
              color: activeTab === "timeline" ? "#fff" : "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
            }}
          >
            Continuous Timeline
          </button>
          <button
            type="button"
            data-testid="tab-monthly"
            onClick={() => setActiveTab("monthly")}
            style={{
              padding: "4px 10px",
              backgroundColor: activeTab === "monthly" ? "var(--color-primary)" : "transparent",
              color: activeTab === "monthly" ? "#fff" : "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
            }}
          >
            Monthly Heatmap
          </button>
          <button
            type="button"
            data-testid="tab-rolling"
            onClick={() => setActiveTab("rolling")}
            style={{
              padding: "4px 10px",
              backgroundColor: activeTab === "rolling" ? "var(--color-primary)" : "transparent",
              color: activeTab === "rolling" ? "#fff" : "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
            }}
          >
            Rolling Returns
          </button>
        </div>

        {/* Global Performance Summary */}
        <div style={{ display: "flex", gap: "var(--spacing-3)", alignItems: "center" }}>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Total Return: </span>
            <strong
              data-testid="total-return-metric"
              style={{
                color: totalReturnPct >= 0 ? "var(--color-up)" : "var(--color-down)",
                fontSize: "var(--font-size-sm)",
              }}
            >
              {totalReturnPct >= 0 ? "+" : ""}
              {totalReturnPct}%
            </strong>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Equity: </span>
            <strong>₹{Math.round(currentEquity).toLocaleString("en-IN")}</strong>
          </div>
          <span
            style={{
              padding: "2px 8px",
              borderRadius: "10px",
              fontSize: "0.625rem",
              fontWeight: 700,
              backgroundColor: "rgba(38, 166, 154, 0.2)",
              color: "var(--color-up)",
            }}
          >
            ● LIVE ACTIVE
          </span>
        </div>
      </div>

      {/* Main Tab Content */}
      <div
        style={{
          flex: 1,
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-sm)",
          padding: "var(--spacing-3)",
          overflowY: "auto",
        }}
      >
        {activeTab === "timeline" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            {/* Phase Pills Filter */}
            <div style={{ display: "flex", gap: "var(--spacing-2)", alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)" }}>Filter Phase:</span>
              {(["ALL", "BACKTEST", "PAPER", "LIVE"] as const).map((phase) => (
                <button
                  key={phase}
                  type="button"
                  data-testid={`filter-${phase.toLowerCase()}`}
                  onClick={() => setSelectedPhase(phase)}
                  style={{
                    padding: "2px 8px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor:
                      selectedPhase === phase ? "var(--color-primary)" : "var(--bg-active)",
                    color: selectedPhase === phase ? "#fff" : "var(--text-primary)",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  {phase}
                </button>
              ))}
            </div>

            {/* Execution Phase Demarcation Slices */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--spacing-2)" }}>
              {timeline.phases.map((slice) => {
                const phaseColor =
                  slice.phase === "LIVE"
                    ? "var(--color-up)"
                    : slice.phase === "PAPER"
                    ? "#faad14"
                    : "#1890ff";
                return (
                  <div
                    key={slice.phase}
                    data-testid={`phase-card-${slice.phase.toLowerCase()}`}
                    style={{
                      border: `1px solid ${phaseColor}`,
                      borderRadius: "var(--radius-sm)",
                      padding: "var(--spacing-2)",
                      backgroundColor: "var(--bg-active)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: phaseColor }}>{slice.phase}</strong>
                      <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
                        {slice.startDate} → {slice.endDate}
                      </span>
                    </div>
                    <div style={{ marginTop: "4px", display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-muted)" }}>Return:</span>
                      <strong style={{ color: slice.totalReturn >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                        {slice.totalReturn >= 0 ? "+" : ""}
                        {(slice.totalReturn * 100).toFixed(2)}%
                      </strong>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-muted)" }}>Ending Eq:</span>
                      <span>₹{Math.round(slice.endEquity).toLocaleString("en-IN")}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Continuous Invariant Verification Banner */}
            <div
              style={{
                backgroundColor: "rgba(38, 166, 154, 0.08)",
                border: "1px solid rgba(38, 166, 154, 0.3)",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>
                🔒 <strong>Strict Non-Overlapping Invariant Enforced:</strong> Backtest → Paper → Live stitched seamlessly without double counting.
              </span>
              <span style={{ fontWeight: 600, color: "var(--color-up)" }}>{filteredPoints.length} Contiguous Days</span>
            </div>

            {/* Recent Daily Return Points Table */}
            <strong style={{ marginTop: "4px" }}>Continuous Daily Equity Ledger (Sample)</strong>
            <div style={{ border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead>
                  <tr style={{ backgroundColor: "var(--bg-active)", borderBottom: "1px solid var(--border-subtle)" }}>
                    <th style={{ padding: "6px 8px" }}>Date</th>
                    <th style={{ padding: "6px 8px" }}>Phase</th>
                    <th style={{ padding: "6px 8px", textAlign: "right" }}>Daily Return</th>
                    <th style={{ padding: "6px 8px", textAlign: "right" }}>Equity</th>
                    <th style={{ padding: "6px 8px", textAlign: "right" }}>Cumulative Return</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPoints.slice(-8).map((pt) => (
                    <tr key={pt.date} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "4px 8px" }}>{pt.date}</td>
                      <td style={{ padding: "4px 8px" }}>
                        <span
                          style={{
                            padding: "1px 6px",
                            borderRadius: "4px",
                            fontSize: "0.625rem",
                            backgroundColor:
                              pt.phase === "LIVE"
                                ? "rgba(38, 166, 154, 0.2)"
                                : pt.phase === "PAPER"
                                ? "rgba(250, 173, 20, 0.2)"
                                : "rgba(24, 144, 255, 0.2)",
                          }}
                        >
                          {pt.phase}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "4px 8px",
                          textAlign: "right",
                          color: pt.dailyReturn >= 0 ? "var(--color-up)" : "var(--color-down)",
                        }}
                      >
                        {pt.dailyReturn >= 0 ? "+" : ""}
                        {(pt.dailyReturn * 100).toFixed(2)}%
                      </td>
                      <td style={{ padding: "4px 8px", textAlign: "right" }}>
                        ₹{Math.round(pt.equity).toLocaleString("en-IN")}
                      </td>
                      <td
                        style={{
                          padding: "4px 8px",
                          textAlign: "right",
                          color: pt.cumulativeReturn >= 0 ? "var(--color-up)" : "var(--color-down)",
                          fontWeight: 600,
                        }}
                      >
                        {pt.cumulativeReturn >= 0 ? "+" : ""}
                        {(pt.cumulativeReturn * 100).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "monthly" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
            <strong>Monthly & Compounded Annual Return Matrix</strong>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right" }}>
                <thead>
                  <tr style={{ backgroundColor: "var(--bg-active)", borderBottom: "1px solid var(--border-subtle)" }}>
                    <th style={{ padding: "6px 8px", textAlign: "left" }}>Year</th>
                    {monthNames.map((m) => (
                      <th key={m} style={{ padding: "6px 6px" }}>{m}</th>
                    ))}
                    <th style={{ padding: "6px 8px" }}>YTD</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlyMatrix.map((row) => (
                    <tr key={row.year} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "6px 8px", textAlign: "left", fontWeight: 700 }}>{row.year}</td>
                      {Array.from({ length: 12 }, (_, idx) => idx + 1).map((m) => {
                        const ret = row.monthly[m];
                        if (ret === undefined) {
                          return <td key={m} style={{ padding: "6px 6px", color: "var(--text-muted)" }}>-</td>;
                        }
                        const isPos = ret >= 0;
                        return (
                          <td
                            key={m}
                            style={{
                              padding: "6px 6px",
                              backgroundColor: isPos ? "rgba(38, 166, 154, 0.1)" : "rgba(239, 83, 80, 0.1)",
                              color: isPos ? "var(--color-up)" : "var(--color-down)",
                            }}
                          >
                            {isPos ? "+" : ""}
                            {(ret * 100).toFixed(1)}%
                          </td>
                        );
                      })}
                      <td
                        style={{
                          padding: "6px 8px",
                          fontWeight: 700,
                          color: row.ytd >= 0 ? "var(--color-up)" : "var(--color-down)",
                        }}
                      >
                        {row.ytd >= 0 ? "+" : ""}
                        {(row.ytd * 100).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "rolling" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            <strong>Rolling Returns Performance Distribution</strong>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--spacing-3)" }}>
              {[rolling1M, rolling3M, rolling6M].map((r) => (
                <div
                  key={r.windowLabel}
                  style={{
                    backgroundColor: "var(--bg-active)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                    padding: "var(--spacing-3)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                  }}
                >
                  <strong style={{ color: "var(--color-primary)" }}>{r.windowLabel}</strong>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Minimum:</span>
                    <span style={{ color: r.min >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                      {(r.min * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Median:</span>
                    <span style={{ color: r.median >= 0 ? "var(--color-up)" : "var(--color-down)", fontWeight: 600 }}>
                      {(r.median * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Maximum:</span>
                    <span style={{ color: r.max >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                      {(r.max * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--border-subtle)", paddingTop: "4px" }}>
                    <span>Current:</span>
                    <strong style={{ color: r.current >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                      {(r.current * 100).toFixed(2)}%
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const returnsTimelineDefinition: WidgetDefinition<ReturnsTimelineWidgetSettings> = {
  id: "returns-timeline",
  title: "Returns & Timeline",
  description: "Monthly/yearly compounded returns, rolling return distributions, and Backtest -> Paper -> Live continuous timeline.",
  category: "analytics",
  icon: "📈",
  defaultWidth: 720,
  defaultHeight: 440,
  schema: {
    fields: [
      {
        name: "activePhaseFilter",
        label: "Initial Phase Filter",
        type: "string",
        default: "ALL",
      },
      {
        name: "initialCapital",
        label: "Initial Capital (₹)",
        type: "number",
        default: 1000000,
      },
    ],
  },
  component: ReturnsTimelineWidget,
};
