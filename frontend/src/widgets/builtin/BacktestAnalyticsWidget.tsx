import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { AnalyticsWidgetSettings, BacktestReport } from "../../analytics/types";
import { generateMockBacktestReport, groupMonthlyReturns, getHeatmapCellColor } from "../../analytics/metrics";

export const BacktestAnalyticsWidget: React.FC<WidgetComponentProps<AnalyticsWidgetSettings>> = ({
  settings,
}) => {
  const [activeTab, setActiveTab] = useState<
    "SCORECARD" | "EQUITY_CURVE" | "UNDERWATER" | "MONTHLY_HEATMAP" | "TRADE_DISTRIBUTION"
  >(settings.defaultMetricView || "SCORECARD");

  const report: BacktestReport = useMemo(() => {
    return generateMockBacktestReport();
  }, []);

  const monthlyMatrix = useMemo(() => {
    return groupMonthlyReturns(report.monthlyReturns);
  }, [report.monthlyReturns]);

  const monthShortNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Header Summary Strip */}
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
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
          <div>
            <strong style={{ fontSize: "var(--font-size-sm)" }}>{report.strategyName}</strong>
            <span style={{ color: "var(--text-muted)", marginLeft: "6px" }}>({report.universe})</span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Net Profit:</span>
            <strong style={{ fontFamily: "var(--font-family-mono)", color: "var(--color-up)" }}>
              +₹{report.netProfit.toLocaleString()} (+{report.scorecard.cagr}%)
            </strong>
          </div>
        </div>

        {/* Strategy Scorecard Grade Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <span style={{ color: "var(--text-muted)" }}>Grade:</span>
          <span
            data-testid="strategy-grade-badge"
            style={{
              padding: "2px 8px",
              borderRadius: "4px",
              backgroundColor: "var(--color-up-bg)",
              color: "var(--color-up)",
              fontWeight: 800,
              fontSize: "var(--font-size-xs)",
            }}
          >
            GRADE {report.scorecard.overallGrade}
          </span>
        </div>
      </div>

      {/* Analytics Sub-View Tabs */}
      <div style={{ display: "flex", gap: "var(--spacing-1)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
        <button
          type="button"
          data-testid="analytics-tab-scorecard"
          onClick={() => setActiveTab("SCORECARD")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "SCORECARD" ? "var(--bg-active)" : "transparent",
            color: activeTab === "SCORECARD" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Tear Sheet
        </button>
        <button
          type="button"
          data-testid="analytics-tab-equity"
          onClick={() => setActiveTab("EQUITY_CURVE")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "EQUITY_CURVE" ? "var(--bg-active)" : "transparent",
            color: activeTab === "EQUITY_CURVE" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Equity Curve
        </button>
        <button
          type="button"
          data-testid="analytics-tab-underwater"
          onClick={() => setActiveTab("UNDERWATER")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "UNDERWATER" ? "var(--bg-active)" : "transparent",
            color: activeTab === "UNDERWATER" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Underwater DD
        </button>
        <button
          type="button"
          data-testid="analytics-tab-heatmap"
          onClick={() => setActiveTab("MONTHLY_HEATMAP")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "MONTHLY_HEATMAP" ? "var(--bg-active)" : "transparent",
            color: activeTab === "MONTHLY_HEATMAP" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Monthly Heatmap
        </button>
        <button
          type="button"
          data-testid="analytics-tab-distribution"
          onClick={() => setActiveTab("TRADE_DISTRIBUTION")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "TRADE_DISTRIBUTION" ? "var(--bg-active)" : "transparent",
            color: activeTab === "TRADE_DISTRIBUTION" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Trade Distribution
        </button>
      </div>

      {/* Main Tab Content */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {activeTab === "SCORECARD" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--spacing-2)" }}>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Sharpe Ratio</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)", color: "var(--color-up)" }}>
                {report.scorecard.sharpeRatio}
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Sortino Ratio</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)", color: "var(--color-up)" }}>
                {report.scorecard.sortinoRatio}
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>CAGR</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)", color: "var(--color-up)" }}>
                {report.scorecard.cagr}%
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Max Drawdown</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)", color: "var(--color-down)" }}>
                -{report.scorecard.maxDrawdownPct}%
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Win Rate</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)" }}>
                {report.scorecard.winRatePct}%
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Profit Factor</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)" }}>
                {report.scorecard.profitFactor}
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Calmar Ratio</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)" }}>
                {report.scorecard.calmarRatio}
              </strong>
            </div>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "var(--spacing-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Total Trades</div>
              <strong style={{ fontSize: "var(--font-size-md)", fontFamily: "var(--font-family-mono)" }}>
                {report.scorecard.totalTrades}
              </strong>
            </div>
          </div>
        )}

        {activeTab === "MONTHLY_HEATMAP" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.6875rem", textAlign: "center" }}>
            <thead>
              <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
                <th style={{ padding: "4px", textAlign: "left" }}>Year</th>
                {monthShortNames.map((m) => (
                  <th key={m} style={{ padding: "4px" }}>
                    {m}
                  </th>
                ))}
                <th style={{ padding: "4px", fontWeight: "bold" }}>Total</th>
              </tr>
            </thead>
            <tbody>
              {monthlyMatrix.years.map((y) => (
                <tr key={y} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "6px 4px", fontWeight: "bold", textAlign: "left" }}>{y}</td>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => {
                    const ret = monthlyMatrix.matrix[y]?.[m];
                    const bgColor = getHeatmapCellColor(ret);
                    return (
                      <td
                        key={m}
                        style={{
                          padding: "6px 2px",
                          backgroundColor: bgColor,
                          fontFamily: "var(--font-family-mono)",
                          fontWeight: 600,
                          borderRadius: "2px",
                        }}
                      >
                        {ret !== undefined ? `${ret > 0 ? "+" : ""}${ret}%` : "—"}
                      </td>
                    );
                  })}
                  <td
                    style={{
                      padding: "6px 4px",
                      fontFamily: "var(--font-family-mono)",
                      fontWeight: 700,
                      color: monthlyMatrix.yearlyTotals[y] >= 0 ? "var(--color-up)" : "var(--color-down)",
                    }}
                  >
                    {monthlyMatrix.yearlyTotals[y] >= 0 ? "+" : ""}
                    {monthlyMatrix.yearlyTotals[y]}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === "TRADE_DISTRIBUTION" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
            <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              Trade PnL Frequency Distribution (190 Trades)
            </span>
            {report.tradeDistribution.map((item) => (
              <div key={item.bin} style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", fontSize: "var(--font-size-xs)" }}>
                <span style={{ width: "90px", textAlign: "right", color: "var(--text-muted)" }}>{item.bin}</span>
                <div
                  style={{
                    flex: 1,
                    height: "18px",
                    backgroundColor: "var(--bg-surface)",
                    borderRadius: "2px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${(item.count / 65) * 100}%`,
                      height: "100%",
                      backgroundColor: item.isProfit ? "var(--color-up)" : "var(--color-down)",
                      borderRadius: "2px",
                    }}
                  />
                </div>
                <span style={{ width: "30px", fontFamily: "var(--font-family-mono)" }}>{item.count}</span>
              </div>
            ))}
          </div>
        )}

        {(activeTab === "EQUITY_CURVE" || activeTab === "UNDERWATER") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", height: "100%" }}>
            <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              {activeTab === "EQUITY_CURVE"
                ? "Cumulative Performance vs Benchmark (250 Bars)"
                : "Underwater Drawdown Profile (Peak-to-Trough)"}
            </div>
            <div
              data-testid={activeTab === "EQUITY_CURVE" ? "equity-curve-view" : "underwater-chart-view"}
              style={{
                flex: 1,
                minHeight: "180px",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-family-mono)",
                fontSize: "var(--font-size-sm)",
              }}
            >
              {activeTab === "EQUITY_CURVE" ? (
                <div style={{ textAlign: "center" }}>
                  <div style={{ color: "var(--color-up)", fontWeight: "bold" }}>
                    Final Strategy Equity: ₹{report.finalCapital.toLocaleString()}
                  </div>
                  <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)", marginTop: "4px" }}>
                    Benchmark Return: +14.2% | Strategy Return: +{report.scorecard.cagr}%
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: "center" }}>
                  <div style={{ color: "var(--color-down)", fontWeight: "bold" }}>
                    Maximum Drawdown: -{report.scorecard.maxDrawdownPct}%
                  </div>
                  <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)", marginTop: "4px" }}>
                    Max Duration: {report.scorecard.maxDrawdownDurationDays} Trading Days
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const backtestAnalyticsDefinition: WidgetDefinition<AnalyticsWidgetSettings> = {
  id: "backtest-analytics",
  title: "Backtest Analytics & Scorecard",
  description: "Institutional tear sheet, underwater drawdown, monthly return heatmap, and trade distribution.",
  category: "analytics",
  icon: "📊",
  defaultWidth: 520,
  defaultHeight: 400,
  schema: {
    fields: [
      {
        name: "defaultMetricView",
        label: "Default View",
        type: "select",
        default: "SCORECARD",
        options: [
          { label: "Tear Sheet Scorecard", value: "SCORECARD" },
          { label: "Equity Curve", value: "EQUITY_CURVE" },
          { label: "Underwater Drawdown", value: "UNDERWATER" },
          { label: "Monthly Heatmap", value: "MONTHLY_HEATMAP" },
          { label: "Trade Distribution", value: "TRADE_DISTRIBUTION" },
        ],
      },
      {
        name: "showBenchmark",
        label: "Show Benchmark Comparison",
        type: "boolean",
        default: true,
      },
    ],
  },
  component: BacktestAnalyticsWidget,
};
