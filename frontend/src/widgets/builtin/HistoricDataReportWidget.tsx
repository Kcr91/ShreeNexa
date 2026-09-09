import { useCallback, useEffect, useState } from "react";

import type { WidgetDefinition } from "../types";
import { builtinSchemas } from "./schemas";

export interface HistoricDataReportSettings {
  symbol?: string;
}

export interface ReportMonth {
  month: string;
  state: string;
  rows: number;
  suspect: boolean;
  reasons: string[];
  in_hours: number;
  out_of_hours: number;
  distinct_days: number;
  unexpected_dates: string[];
  attempts: number;
  last_error: string | null;
}

export interface ReportSeries {
  symbol: string;
  label: string;
  dataset: string;
  exchange_segment: string;
  interval: string;
  tier: number;
  downloaded_months: number;
  pending_months: number;
  failed_months: number;
  suspect_months: number;
  total_rows: number;
  first_month: string | null;
  last_month: string | null;
  months: ReportMonth[];
}

export interface ReportTotals {
  windows: number;
  bars: number;
  done: number;
  empty: number;
  pending: number;
  failed: number;
  suspect: number;
  settled: number;
  percent_complete: number;
}

/** Colour and label for a month cell. Downloaded-but-odd is deliberately distinct
 *  from both clean and missing: the data is there, it just needs a look. */
function monthStyle(m: ReportMonth): { bg: string; title: string } {
  if (m.state === "failed") {
    return { bg: "var(--negative, #ef4444)", title: m.last_error || "failed" };
  }
  if (m.state === "pending" || m.state === "running") {
    return { bg: "var(--border-subtle, #3f3f46)", title: "not downloaded yet" };
  }
  if (m.state === "empty") {
    return { bg: "var(--text-muted, #71717a)", title: "fetched, no bars returned" };
  }
  if (m.suspect) {
    return {
      bg: "var(--warning, #f59e0b)",
      title: `${m.rows.toLocaleString()} bars — ${m.reasons.join("; ")}`,
    };
  }
  return { bg: "var(--positive, #10b981)", title: `${m.rows.toLocaleString()} bars` };
}

export function HistoricDataReportWidget({
  settings,
}: {
  instanceId?: string;
  settings?: HistoricDataReportSettings;
}) {
  const [symbol, setSymbol] = useState(settings?.symbol ?? "");
  const [suspectOnly, setSuspectOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totals, setTotals] = useState<ReportTotals | null>(null);
  const [series, setSeries] = useState<ReportSeries[]>([]);
  const [selected, setSelected] = useState<ReportMonth | null>(null);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit_series: "200" });
      if (symbol.trim()) params.set("symbol", symbol.trim().toUpperCase());
      if (suspectOnly) params.set("suspect_only", "true");

      const res = await fetch(`/api/v1/historical/report?${params.toString()}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server responded with ${res.status}`);
      }
      const data = await res.json();
      setTotals(data.totals);
      setSeries(data.series || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load report");
      setTotals(null);
      setSeries([]);
    } finally {
      setLoading(false);
    }
  }, [symbol, suspectOnly]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const cell = (v: string | number) => (
    <span style={{ fontVariantNumeric: "tabular-nums" }}>{v}</span>
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "var(--bg-primary)",
        color: "var(--text-primary)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "var(--spacing-3) var(--spacing-4)",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          gap: "var(--spacing-3)",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "var(--font-size-md)" }}>Historic Data Report</h2>
        <input
          aria-label="Symbol filter"
          placeholder="All symbols"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          style={{
            backgroundColor: "var(--bg-secondary)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "3px",
            padding: "4px 8px",
            fontSize: "12px",
          }}
        />
        <button
          type="button"
          aria-pressed={suspectOnly}
          onClick={() => setSuspectOnly((v) => !v)}
          style={{
            backgroundColor: suspectOnly ? "var(--warning, #f59e0b)" : "var(--bg-secondary)",
            color: suspectOnly ? "#000" : "var(--text-muted)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "3px",
            padding: "4px 8px",
            fontSize: "12px",
            cursor: "pointer",
          }}
        >
          Needs review only
        </button>
        <button
          type="button"
          onClick={fetchReport}
          style={{
            backgroundColor: "var(--bg-secondary)",
            color: "var(--text-muted)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "3px",
            padding: "4px 8px",
            fontSize: "12px",
            cursor: "pointer",
          }}
        >
          Refresh
        </button>
      </div>

      {totals && (
        <div
          data-testid="report-totals"
          style={{
            display: "flex",
            gap: "var(--spacing-4)",
            padding: "var(--spacing-2) var(--spacing-4)",
            borderBottom: "1px solid var(--border-subtle)",
            fontSize: "12px",
            flexWrap: "wrap",
          }}
        >
          <span>
            Progress <strong>{cell(totals.percent_complete)}%</strong>
          </span>
          <span>
            Downloaded <strong>{cell(totals.settled)}</strong> / {cell(totals.windows)} months
          </span>
          <span>
            Bars <strong>{cell(totals.bars.toLocaleString())}</strong>
          </span>
          <span style={{ color: "var(--warning, #f59e0b)" }}>
            Needs review <strong>{cell(totals.suspect)}</strong>
          </span>
          <span style={{ color: "var(--negative, #ef4444)" }}>
            Failed <strong>{cell(totals.failed)}</strong>
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            Pending <strong>{cell(totals.pending)}</strong>
          </span>
        </div>
      )}

      {error && (
        <div style={{ padding: "var(--spacing-3)", color: "var(--negative, #ef4444)" }}>
          {error}
        </div>
      )}

      <div style={{ flex: 1, overflow: "auto", padding: "var(--spacing-3)" }}>
        {loading && <div style={{ color: "var(--text-muted)" }}>Loading report…</div>}

        {!loading && series.length === 0 && !error && (
          <div style={{ color: "var(--text-muted)", padding: "24px", textAlign: "center" }}>
            No backfill jobs have been queued yet. Once a backfill runs, every month it
            fetches is recorded here.
          </div>
        )}

        {series.map((s) => (
          <div key={`${s.label}-${s.dataset}`} style={{ marginBottom: "var(--spacing-4)" }}>
            <div
              style={{
                display: "flex",
                gap: "var(--spacing-3)",
                alignItems: "baseline",
                fontSize: "12px",
                marginBottom: "4px",
              }}
            >
              <strong style={{ fontSize: "13px" }}>{s.label}</strong>
              <span style={{ color: "var(--text-muted)" }}>
                {s.exchange_segment} · {s.dataset} · tier {s.tier}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                {s.downloaded_months}/{s.months.length} months ·{" "}
                {s.total_rows.toLocaleString()} bars
              </span>
              {s.suspect_months > 0 && (
                <span style={{ color: "var(--warning, #f59e0b)" }}>
                  {s.suspect_months} need review
                </span>
              )}
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "2px" }}>
              {s.months.map((m) => {
                const style = monthStyle(m);
                return (
                  <button
                    key={m.month}
                    type="button"
                    title={`${m.month}: ${style.title}`}
                    aria-label={`${s.label} ${m.month} ${m.state}${m.suspect ? " needs review" : ""}`}
                    onClick={() => setSelected(m)}
                    style={{
                      backgroundColor: style.bg,
                      border: "none",
                      borderRadius: "2px",
                      width: "34px",
                      height: "18px",
                      cursor: "pointer",
                      fontSize: "8px",
                      color: "#000",
                      opacity: m.state === "pending" ? 0.5 : 1,
                    }}
                  >
                    {m.month.slice(2)}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <div
          data-testid="month-detail"
          style={{
            borderTop: "1px solid var(--border-subtle)",
            padding: "var(--spacing-3) var(--spacing-4)",
            fontSize: "12px",
            backgroundColor: "var(--bg-secondary)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <strong>{selected.month}</strong>
            <button
              type="button"
              onClick={() => setSelected(null)}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
              }}
            >
              close
            </button>
          </div>
          <div style={{ color: "var(--text-muted)", marginTop: "4px" }}>
            state {selected.state} · {selected.rows.toLocaleString()} bars ·{" "}
            {selected.distinct_days} days · {selected.in_hours.toLocaleString()} in hours ·{" "}
            {selected.out_of_hours.toLocaleString()} outside
          </div>
          {selected.reasons.length > 0 && (
            <ul style={{ margin: "6px 0 0", paddingLeft: "18px", color: "var(--warning, #f59e0b)" }}>
              {selected.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {selected.unexpected_dates.length > 0 && (
            <div style={{ marginTop: "6px", color: "var(--text-muted)" }}>
              Dates not in our calendar: {selected.unexpected_dates.slice(0, 8).join(", ")}
              {selected.unexpected_dates.length > 8 ? " …" : ""}
            </div>
          )}
          {selected.last_error && (
            <div style={{ marginTop: "6px", color: "var(--negative, #ef4444)" }}>
              {selected.last_error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export const historicDataReportDefinition: WidgetDefinition<HistoricDataReportSettings> = {
  id: "historic-data-report",
  title: "Historic Data Report",
  description:
    "Month-by-month record of what has been downloaded for each series, what is still missing, and which months returned data that needs a closer look.",
  category: "analytics",
  icon: "🧾",
  defaultWidth: 900,
  defaultHeight: 560,
  schema: builtinSchemas["historic-data-report"],
  component: HistoricDataReportWidget,
};
