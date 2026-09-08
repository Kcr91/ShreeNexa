import React, { useState, useEffect, useCallback } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { builtinSchemas } from "./schemas";

export interface HistoricDataSettings {
  defaultSymbol?: string;
  defaultTimeframe?: string;
  defaultSegment?: string;
}

export interface BarRecordItem {
  timestamp: string;
  symbol: string;
  exchange_segment: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  open_interest: number;
}

export interface SummaryStats {
  total_bars: number;
  first_timestamp?: string | null;
  last_timestamp?: string | null;
  high?: number | null;
  low?: number | null;
  total_volume?: number;
}

const POPULAR_SCRIPS = [
  "RELIANCE",
  "TCS",
  "HDFCBANK",
  "INFY",
  "ICICIBANK",
  "SBIN",
  "BHARTIARTL",
  "ITC",
  "NIFTY 50",
  "BANKNIFTY",
];

const TIMEFRAMES = [
  { id: "1m", label: "1 min" },
  { id: "3m", label: "3 min" },
  { id: "5m", label: "5 min" },
  { id: "15m", label: "15 min" },
  { id: "30m", label: "30 min" },
  { id: "60m", label: "1 hour" },
  { id: "1d", label: "Daily" },
  { id: "1w", label: "Weekly" },
];

const DATE_PRESETS = [
  { label: "1 Day", days: 1 },
  { label: "1 Week", days: 7 },
  { label: "1 Month", days: 30 },
  { label: "3 Months", days: 90 },
  { label: "6 Months", days: 180 },
  { label: "1 Year", days: 365 },
];

function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export const HistoricDataWidget: React.FC<WidgetComponentProps<HistoricDataSettings>> = ({
  settings,
}) => {
  const [symbol, setSymbol] = useState(settings?.defaultSymbol || "RELIANCE");
  const [segment, setSegment] = useState(settings?.defaultSegment || "NSE_EQ");
  const [timeframe, setTimeframe] = useState(settings?.defaultTimeframe || "1d");

  // Date range
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return formatDate(d);
  });
  const [endDate, setEndDate] = useState(() => formatDate(new Date()));

  // Query state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>("warehouse");
  const [summary, setSummary] = useState<SummaryStats | null>(null);
  const [bars, setBars] = useState<BarRecordItem[]>([]);
  const [copied, setCopied] = useState(false);

  // Apply preset date range
  const handlePresetSelect = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    setEndDate(formatDate(end));
    setStartDate(formatDate(start));
  };

  // Fetch preview bars
  const fetchBars = useCallback(async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams({
        symbol: symbol.trim().toUpperCase(),
        exchange_segment: segment,
        timeframe,
        start_time: startDate,
        end_time: endDate,
        limit: "500",
      });

      const res = await fetch(`/api/v1/historical/bars?${queryParams.toString()}`);
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server responded with ${res.status}`);
      }

      const data = await res.json();
      setBars(data.bars || []);
      setSummary(data.summary || null);
      setDataSource(data.data_source || "warehouse");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load historical bars";
      setError(msg);
      setBars([]);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [symbol, segment, timeframe, startDate, endDate]);

  // Initial load
  useEffect(() => {
    fetchBars();
  }, [fetchBars]);

  // CSV direct download handler
  const handleDownloadCsv = () => {
    if (!symbol.trim()) return;
    const queryParams = new URLSearchParams({
      symbol: symbol.trim().toUpperCase(),
      exchange_segment: segment,
      timeframe,
      start_time: startDate,
      end_time: endDate,
    });

    const exportUrl = `/api/v1/historical/export?${queryParams.toString()}`;
    const link = document.createElement("a");
    link.href = exportUrl;
    link.setAttribute("download", "");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Copy CSV to clipboard
  const handleCopyCsv = () => {
    if (bars.length === 0) return;
    const header = "timestamp,symbol,open,high,low,close,volume,open_interest\n";
    const rows = bars
      .map(
        (b) =>
          `${b.timestamp},${b.symbol},${b.open.toFixed(2)},${b.high.toFixed(2)},${b.low.toFixed(2)},${b.close.toFixed(2)},${b.volume},${b.open_interest}`
      )
      .join("\n");
    navigator.clipboard.writeText(header + rows);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        backgroundColor: "var(--bg-primary)",
        color: "var(--text-primary)",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
        overflow: "hidden",
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          padding: "var(--spacing-3) var(--spacing-4)",
          backgroundColor: "var(--bg-secondary)",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--spacing-2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "36px",
              height: "36px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "rgba(16, 185, 129, 0.15)",
              color: "#10b981",
              fontSize: "18px",
            }}
          >
            📥
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
              <h2 style={{ fontSize: "var(--font-size-base)", fontWeight: 600, margin: 0 }}>
                Historic Data Download
              </h2>
              <span
                style={{
                  fontSize: "10px",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  backgroundColor: "rgba(16, 185, 129, 0.2)",
                  color: "#10b981",
                  fontWeight: 600,
                  textTransform: "uppercase",
                }}
              >
                CSV Export
              </span>
            </div>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              Query, preview, and download historical OHLCV data from DuckDB Parquet warehouse
            </p>
          </div>
        </div>

        {/* Database Telemetry Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "var(--font-size-xs)",
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-muted)",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: dataSource === "warehouse" ? "#10b981" : "#f59e0b",
              }}
            />
            {dataSource === "warehouse" ? "DuckDB Parquet: Connected" : "Local Engine: Simulated"}
          </span>
        </div>
      </div>

      {/* Main Configuration Controls */}
      <div
        style={{
          padding: "var(--spacing-3) var(--spacing-4)",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          gap: "var(--spacing-3)",
        }}
      >
        {/* Row 1: Symbol Search & Popular Chips */}
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "var(--spacing-3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
            <label
              htmlFor="historic-symbol-input"
              style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontWeight: 500 }}
            >
              Script / Symbol:
            </label>
            <input
              id="historic-symbol-input"
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. RELIANCE, NIFTY 50"
              style={{
                backgroundColor: "var(--bg-primary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
                fontSize: "var(--font-size-xs)",
                fontWeight: 600,
                width: "140px",
                textTransform: "uppercase",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
            <label
              htmlFor="historic-segment-select"
              style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontWeight: 500 }}
            >
              Segment:
            </label>
            <select
              id="historic-segment-select"
              value={segment}
              onChange={(e) => setSegment(e.target.value)}
              style={{
                backgroundColor: "var(--bg-primary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 8px",
                fontSize: "var(--font-size-xs)",
              }}
            >
              <option value="NSE_EQ">NSE Equity (Cash)</option>
              <option value="NSE_FNO">NSE F&amp;O</option>
              <option value="IDX_I">Indices</option>
              <option value="BSE_EQ">BSE Equity</option>
            </select>
          </div>

          {/* Quick Script Chips */}
          <div style={{ display: "flex", alignItems: "center", gap: "4px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Popular:</span>
            {POPULAR_SCRIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => setSymbol(chip)}
                style={{
                  backgroundColor: symbol === chip ? "var(--accent-primary, #2563eb)" : "var(--bg-primary)",
                  color: symbol === chip ? "#ffffff" : "var(--text-muted)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "12px",
                  padding: "2px 8px",
                  fontSize: "11px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {chip}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Timeframe & Date Range Controls */}
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", justifyContent: "space-between", gap: "var(--spacing-3)" }}>
          {/* Timeframe Buttons */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
            <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontWeight: 500 }}>
              Timeframe:
            </span>
            <div
              style={{
                display: "inline-flex",
                backgroundColor: "var(--bg-primary)",
                borderRadius: "var(--radius-sm)",
                padding: "2px",
                border: "1px solid var(--border-default)",
              }}
            >
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf.id}
                  type="button"
                  onClick={() => setTimeframe(tf.id)}
                  style={{
                    backgroundColor: timeframe === tf.id ? "var(--accent-primary, #3b82f6)" : "transparent",
                    color: timeframe === tf.id ? "#ffffff" : "var(--text-secondary)",
                    border: "none",
                    borderRadius: "3px",
                    padding: "4px 8px",
                    fontSize: "var(--font-size-xs)",
                    fontWeight: timeframe === tf.id ? 600 : 400,
                    cursor: "pointer",
                  }}
                >
                  {tf.label}
                </button>
              ))}
            </div>
          </div>

          {/* Date Range Interval */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", flexWrap: "wrap" }}>
            <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontWeight: 500 }}>
              Interval:
            </span>
            <div style={{ display: "inline-flex", gap: "3px" }}>
              {DATE_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => handlePresetSelect(preset.days)}
                  style={{
                    backgroundColor: "var(--bg-primary)",
                    color: "var(--text-muted)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "3px",
                    padding: "3px 6px",
                    fontSize: "11px",
                    cursor: "pointer",
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <input
                type="date"
                aria-label="Start Date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{
                  backgroundColor: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "4px 6px",
                  fontSize: "var(--font-size-xs)",
                }}
              />
              <span style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>to</span>
              <input
                type="date"
                aria-label="End Date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{
                  backgroundColor: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "4px 6px",
                  fontSize: "var(--font-size-xs)",
                }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", marginLeft: "var(--spacing-2)" }}>
              <button
                type="button"
                onClick={fetchBars}
                disabled={loading}
                style={{
                  backgroundColor: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 12px",
                  fontSize: "var(--font-size-xs)",
                  fontWeight: 600,
                  cursor: loading ? "wait" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                {loading ? "Loading..." : "Preview Data"}
              </button>

              <button
                type="button"
                onClick={handleDownloadCsv}
                style={{
                  backgroundColor: "#10b981",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 14px",
                  fontSize: "var(--font-size-xs)",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                }}
              >
                <span>💾</span>
                <span>Download CSV</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Scorecard Cards */}
      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: "var(--spacing-2)",
            padding: "var(--spacing-2) var(--spacing-4)",
            backgroundColor: "var(--bg-secondary)",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <div
            style={{
              padding: "6px 10px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Total Bars</div>
            <div style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "var(--text-primary)" }}>
              {summary.total_bars.toLocaleString()}
            </div>
          </div>

          <div
            style={{
              padding: "6px 10px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Highest High</div>
            <div style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "#10b981" }}>
              {summary.high ? `₹${summary.high.toFixed(2)}` : "—"}
            </div>
          </div>

          <div
            style={{
              padding: "6px 10px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Lowest Low</div>
            <div style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "#ef4444" }}>
              {summary.low ? `₹${summary.low.toFixed(2)}` : "—"}
            </div>
          </div>

          <div
            style={{
              padding: "6px 10px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>Total Traded Volume</div>
            <div style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "var(--text-primary)" }}>
              {summary.total_volume ? (summary.total_volume / 1000000).toFixed(2) + "M" : "0"}
            </div>
          </div>

          <div
            style={{
              padding: "6px 10px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
            }}
          >
            <button
              type="button"
              onClick={handleCopyCsv}
              disabled={bars.length === 0}
              style={{
                backgroundColor: "transparent",
                color: copied ? "#10b981" : "var(--text-muted)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                fontSize: "11px",
                cursor: "pointer",
              }}
            >
              {copied ? "✓ Copied CSV" : "📋 Copy CSV"}
            </button>
          </div>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div
          style={{
            margin: "var(--spacing-3) var(--spacing-4)",
            padding: "var(--spacing-2) var(--spacing-3)",
            backgroundColor: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-sm)",
            color: "#ef4444",
            fontSize: "var(--font-size-xs)",
          }}
        >
          <strong>Error querying data:</strong> {error}
        </div>
      )}

      {/* Data Preview Table */}
      <div style={{ flex: 1, overflowY: "auto", position: "relative" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "12px",
            fontFamily: "var(--font-mono, monospace)",
          }}
        >
          <thead
            style={{
              position: "sticky",
              top: 0,
              backgroundColor: "var(--bg-secondary)",
              borderBottom: "1px solid var(--border-default)",
              zIndex: 2,
            }}
          >
            <tr>
              <th style={{ padding: "8px 12px", textAlign: "left", color: "var(--text-muted)", fontWeight: 600 }}>Timestamp</th>
              <th style={{ padding: "8px 12px", textAlign: "left", color: "var(--text-muted)", fontWeight: 600 }}>Symbol</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>Open</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>High</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>Low</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>Close</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>Change</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>Volume</th>
              <th style={{ padding: "8px 12px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>OI</th>
            </tr>
          </thead>
          <tbody>
            {bars.length === 0 && !loading && (
              <tr>
                <td colSpan={9} style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                  No historical data found for the selected scrip and date range. Click &quot;Preview Data&quot; or check symbols.
                </td>
              </tr>
            )}
            {bars.map((bar, index) => {
              const isUp = bar.close >= bar.open;
              const chg = bar.open > 0 ? ((bar.close - bar.open) / bar.open) * 100 : 0;
              const formattedTime = bar.timestamp.replace("T", " ").replace("Z", "");

              return (
                <tr
                  key={`${bar.timestamp}-${index}`}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    backgroundColor: index % 2 === 0 ? "transparent" : "rgba(255,255,255,0.015)",
                  }}
                >
                  <td style={{ padding: "6px 12px", color: "var(--text-secondary)" }}>{formattedTime}</td>
                  <td style={{ padding: "6px 12px", fontWeight: 600, color: "var(--text-primary)" }}>{bar.symbol}</td>
                  <td style={{ padding: "6px 12px", textAlign: "right" }}>₹{bar.open.toFixed(2)}</td>
                  <td style={{ padding: "6px 12px", textAlign: "right", color: "#10b981" }}>₹{bar.high.toFixed(2)}</td>
                  <td style={{ padding: "6px 12px", textAlign: "right", color: "#ef4444" }}>₹{bar.low.toFixed(2)}</td>
                  <td style={{ padding: "6px 12px", textAlign: "right", fontWeight: 600, color: isUp ? "#10b981" : "#ef4444" }}>
                    ₹{bar.close.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px 12px", textAlign: "right", color: isUp ? "#10b981" : "#ef4444" }}>
                    {chg >= 0 ? "+" : ""}
                    {chg.toFixed(2)}%
                  </td>
                  <td style={{ padding: "6px 12px", textAlign: "right", color: "var(--text-secondary)" }}>
                    {bar.volume.toLocaleString()}
                  </td>
                  <td style={{ padding: "6px 12px", textAlign: "right", color: "var(--text-muted)" }}>
                    {bar.open_interest.toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const historicDataDefinition: WidgetDefinition<HistoricDataSettings> = {
  id: "historic-data",
  title: "Historic Data Download",
  description:
    "Query, preview, and download historical OHLCV bar data for any script, timeframe, and date interval in CSV format.",
  category: "analytics",
  icon: "📥",
  defaultWidth: 780,
  defaultHeight: 520,
  schema: builtinSchemas["historic-data"],
  component: HistoricDataWidget,
};
