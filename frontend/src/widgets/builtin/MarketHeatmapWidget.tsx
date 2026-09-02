import React, { useState, useEffect, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  IndexHeatmapItem,
  ConstituentHeatmapItem,
  MarketBreadth,
} from "../../heatmap/types";
import {
  calculateMarketBreadth,
  handleMissingWeights,
  getHeatmapTileColor,
} from "../../heatmap/engine";

export interface HeatmapSettings {
  defaultMode?: "INDICES" | "CONSTITUENTS";
  defaultIndexName?: string;
}

const DEFAULT_INDICES: IndexHeatmapItem[] = [
  {
    indexName: "NIFTY 50",
    sector: "Large Cap Benchmark",
    weight: 25.0,
    changePct: 0.85,
    ltp: 25250.0,
    advances: 32,
    declines: 16,
    unchanged: 2,
    futuresBasis: 42.5,
    oiChangePct: 2.8,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY BANK",
    sector: "Banking",
    weight: 20.0,
    changePct: 1.40,
    ltp: 52150.0,
    advances: 9,
    declines: 3,
    unchanged: 0,
    futuresBasis: 65.0,
    oiChangePct: 4.1,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY IT",
    sector: "Information Technology",
    weight: 15.0,
    changePct: -0.65,
    ltp: 41800.0,
    advances: 3,
    declines: 7,
    unchanged: 0,
    futuresBasis: -15.0,
    oiChangePct: -1.2,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY AUTO",
    sector: "Automotive",
    weight: 10.0,
    changePct: 1.85,
    ltp: 26400.0,
    advances: 11,
    declines: 4,
    unchanged: 0,
    futuresBasis: 30.0,
    oiChangePct: 3.5,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY PHARMA",
    sector: "Pharmaceuticals",
    weight: 8.0,
    changePct: 0.35,
    ltp: 22900.0,
    advances: 12,
    declines: 8,
    unchanged: 0,
    futuresBasis: 12.0,
    oiChangePct: 0.8,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY FMCG",
    sector: "FMCG",
    weight: 8.0,
    changePct: -0.40,
    ltp: 58300.0,
    advances: 5,
    declines: 10,
    unchanged: 0,
    futuresBasis: -5.0,
    oiChangePct: -0.5,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY METAL",
    sector: "Metals & Mining",
    weight: 7.0,
    changePct: 2.45,
    ltp: 9650.0,
    advances: 12,
    declines: 3,
    unchanged: 0,
    futuresBasis: 25.0,
    oiChangePct: 5.2,
    weightingSource: "OFFICIAL_NSE",
  },
  {
    indexName: "NIFTY ENERGY",
    sector: "Energy",
    weight: 7.0,
    changePct: 0.75,
    ltp: 39100.0,
    advances: 6,
    declines: 4,
    unchanged: 0,
    futuresBasis: 18.0,
    oiChangePct: 1.5,
    weightingSource: "OFFICIAL_NSE",
  },
];

const RAW_MOCK_CONSTITUENTS: Record<string, Parameters<typeof handleMissingWeights>[0]> = {
  "NIFTY 50": [
    { symbol: "RELIANCE", sector: "Energy", weight: 9.8, changePct: 1.25, ltp: 2980.5, volume: 4250000 },
    { symbol: "HDFCBANK", sector: "Banking", weight: 8.5, changePct: 0.80, ltp: 1640.2, volume: 6800000 },
    { symbol: "ICICIBANK", sector: "Banking", weight: 7.9, changePct: 1.65, ltp: 1215.3, volume: 5400000 },
    { symbol: "INFY", sector: "IT", weight: 5.6, changePct: -1.10, ltp: 1890.1, volume: 3100000 },
    { symbol: "TCS", sector: "IT", weight: 4.2, changePct: -0.45, ltp: 4210.0, volume: 1850000 },
    { symbol: "LT", sector: "Infrastructure", weight: 3.8, changePct: 1.15, ltp: 3650.0, volume: 1200000 },
    { symbol: "BHARTIARTL", sector: "Telecom", weight: 3.5, changePct: 0.90, ltp: 1540.0, volume: 2900000 },
    { symbol: "SBIN", sector: "Banking", weight: 3.1, changePct: 1.05, ltp: 815.4, volume: 7600000 },
    // Missing weights to test deterministic assignment and visible labelling
    { symbol: "TATASTEEL", sector: "Metals", weight: null, changePct: 2.85, ltp: 154.8, volume: 12400000 },
    { symbol: "MARUTI", sector: "Automotive", weight: null, changePct: 1.40, ltp: 12450.0, volume: 650000 },
  ],
  "NIFTY BANK": [
    { symbol: "HDFCBANK", sector: "Banking", weight: 29.4, changePct: 0.80, ltp: 1640.2, volume: 6800000 },
    { symbol: "ICICIBANK", sector: "Banking", weight: 24.1, changePct: 1.65, ltp: 1215.3, volume: 5400000 },
    { symbol: "SBIN", sector: "Banking", weight: 11.2, changePct: 1.15, ltp: 815.4, volume: 7600000 },
    { symbol: "AXISBANK", sector: "Banking", weight: 10.5, changePct: -0.25, ltp: 1180.0, volume: 3800000 },
    { symbol: "KOTAKBANK", sector: "Banking", weight: 9.8, changePct: 0.40, ltp: 1790.0, volume: 2100000 },
    { symbol: "INDUSINDBK", sector: "Banking", weight: 5.2, changePct: 1.80, ltp: 1420.0, volume: 1900000 },
    { symbol: "BANKBARODA", sector: "Banking", weight: null, changePct: 2.10, ltp: 245.0, volume: 8500000 },
  ],
  "NIFTY IT": [
    { symbol: "TCS", sector: "IT", weight: 28.5, changePct: -0.45, ltp: 4210.0, volume: 1850000 },
    { symbol: "INFY", sector: "IT", weight: 26.2, changePct: -1.10, ltp: 1890.1, volume: 3100000 },
    { symbol: "HCLTECH", sector: "IT", weight: 12.8, changePct: 0.75, ltp: 1780.4, volume: 1400000 },
    { symbol: "WIPRO", sector: "IT", weight: 8.5, changePct: 0.35, ltp: 540.2, volume: 2200000 },
    { symbol: "LTIM", sector: "IT", weight: 7.2, changePct: -1.30, ltp: 5120.0, volume: 750000 },
    { symbol: "TECHM", sector: "IT", weight: null, changePct: 0.90, ltp: 1610.0, volume: 1100000 },
  ],
};

export const MarketHeatmapWidget: React.FC<WidgetComponentProps<HeatmapSettings>> = ({
  settings,
}) => {
  const [viewMode, setViewMode] = useState<"INDICES" | "CONSTITUENTS">(
    settings.defaultMode || "INDICES"
  );
  const [selectedIndex, setSelectedIndex] = useState<string>(
    settings.defaultIndexName || "NIFTY 50"
  );

  const [indices, setIndices] = useState<IndexHeatmapItem[]>(DEFAULT_INDICES);
  const [constituentData, setConstituentData] = useState<{
    cellTotalWeight: number;
    constituents: ConstituentHeatmapItem[];
  }>(() => handleMissingWeights(RAW_MOCK_CONSTITUENTS["NIFTY 50"] || []));

  useEffect(() => {
    // Try fetching from backend API if running
    fetch("/api/v1/heatmap/indices")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setIndices(
            data.map((d) => ({
              indexName: d.index_name,
              sector: d.sector,
              weight: d.weight,
              changePct: d.change_pct,
              ltp: d.ltp,
              advances: d.advances,
              declines: d.declines,
              unchanged: d.unchanged,
              futuresBasis: d.futures_basis,
              oiChangePct: d.oi_change_pct,
              weightingSource: d.weighting_source,
            }))
          );
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const raw = RAW_MOCK_CONSTITUENTS[selectedIndex] || RAW_MOCK_CONSTITUENTS["NIFTY 50"];
    setConstituentData(handleMissingWeights(raw));
  }, [selectedIndex]);

  // Compute active market breadth
  const activeBreadth: MarketBreadth = useMemo(() => {
    if (viewMode === "INDICES") {
      return calculateMarketBreadth(indices);
    }
    return calculateMarketBreadth(constituentData.constituents);
  }, [viewMode, indices, constituentData]);

  const handleIndexClick = (indexName: string) => {
    setSelectedIndex(indexName);
    setViewMode("CONSTITUENTS");
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--bg-surface)",
        color: "var(--text-primary)",
        fontSize: "var(--font-size-sm)",
      }}
    >
      {/* 1. Control Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "var(--spacing-2)",
          padding: "var(--spacing-2)",
          backgroundColor: "var(--bg-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            onClick={() => setViewMode("INDICES")}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: viewMode === "INDICES" ? "var(--color-brand)" : "transparent",
              color: viewMode === "INDICES" ? "#fff" : "var(--text-muted)",
              fontWeight: 600,
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Sectoral Indices
          </button>
          <button
            type="button"
            onClick={() => setViewMode("CONSTITUENTS")}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: viewMode === "CONSTITUENTS" ? "var(--color-brand)" : "transparent",
              color: viewMode === "CONSTITUENTS" ? "#fff" : "var(--text-muted)",
              fontWeight: 600,
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Constituents Drill-In
          </button>
        </div>

        {viewMode === "CONSTITUENTS" && (
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
            <label style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              Index:
            </label>
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              style={{
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "var(--bg-input)",
                color: "var(--text-primary)",
                fontSize: "var(--font-size-xs)",
                fontWeight: 600,
              }}
            >
              {DEFAULT_INDICES.map((idx) => (
                <option key={idx.indexName} value={idx.indexName}>
                  {idx.indexName}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 2. Sentiment & Market Breadth Bar */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "var(--spacing-2)",
          padding: "var(--spacing-1) var(--spacing-2)",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Breadth:</span>
          <span
            style={{
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-up-bg)",
              color: "var(--color-up)",
              fontWeight: 700,
            }}
          >
            ▲ {activeBreadth.advances} Adv
          </span>
          <span
            style={{
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-down-bg)",
              color: "var(--color-down)",
              fontWeight: 700,
            }}
          >
            ▼ {activeBreadth.declines} Dec
          </span>
          <span
            style={{
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-elevated)",
              color: "var(--text-muted)",
            }}
          >
            ● {activeBreadth.unchanged} Unch
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            A/D: <strong>{activeBreadth.advanceDeclineRatio.toFixed(2)}</strong>
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <span style={{ color: "var(--text-muted)" }}>
            Above Prev Close: <strong>{activeBreadth.pctAbovePrevClose}%</strong>
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            Weighted:{" "}
            <strong
              style={{
                color:
                  activeBreadth.weightedBreadth >= 0
                    ? "var(--color-up)"
                    : "var(--color-down)",
              }}
            >
              {activeBreadth.weightedBreadth >= 0 ? "+" : ""}
              {activeBreadth.weightedBreadth.toFixed(2)}%
            </strong>
          </span>
          <span
            style={{
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor:
                activeBreadth.sentimentPosture.includes("Bullish")
                  ? "var(--color-up-bg)"
                  : activeBreadth.sentimentPosture.includes("Bearish")
                  ? "var(--color-down-bg)"
                  : "var(--bg-elevated)",
              color:
                activeBreadth.sentimentPosture.includes("Bullish")
                  ? "var(--color-up)"
                  : activeBreadth.sentimentPosture.includes("Bearish")
                  ? "var(--color-down)"
                  : "var(--text-primary)",
              fontWeight: 700,
            }}
          >
            {activeBreadth.sentimentPosture}
          </span>
        </div>
      </div>

      {/* 3. Heatmap Matrix */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "var(--spacing-2)",
          display: "flex",
          flexWrap: "wrap",
          alignContent: "flex-start",
          gap: "var(--spacing-1)",
        }}
      >
        {viewMode === "INDICES" ? (
          // Index Level View
          indices.map((item) => {
            const isUp = item.changePct >= 0;
            const bgColor = getHeatmapTileColor(item.changePct);
            const basisStr =
              item.futuresBasis >= 0 ? `+${item.futuresBasis}` : `${item.futuresBasis}`;

            return (
              <div
                key={item.indexName}
                onClick={() => handleIndexClick(item.indexName)}
                style={{
                  flexGrow: item.weight,
                  flexBasis: `${Math.max(120, item.weight * 12)}px`,
                  minHeight: "95px",
                  padding: "var(--spacing-2)",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: bgColor,
                  color: "#fff",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  transition: "transform 0.15s ease, box-shadow 0.15s ease",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                }}
                title={`Click to drill down into ${item.indexName} constituents`}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontWeight: 700, fontSize: "var(--font-size-sm)" }}>
                    {item.indexName}
                  </span>
                  <span style={{ fontSize: "11px", opacity: 0.9 }}>
                    Wt: {item.weight}%
                  </span>
                </div>

                <div style={{ textAlign: "center", margin: "4px 0" }}>
                  <div
                    style={{
                      fontFamily: "var(--font-family-mono)",
                      fontSize: "var(--font-size-lg)",
                      fontWeight: 800,
                      textShadow: "0 1px 2px rgba(0,0,0,0.5)",
                    }}
                  >
                    {isUp ? "+" : ""}
                    {item.changePct.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: "10px", opacity: 0.85, fontFamily: "var(--font-family-mono)" }}>
                    ₹{item.ltp.toLocaleString("en-IN")}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "10px",
                    opacity: 0.85,
                    borderTop: "1px solid rgba(255, 255, 255, 0.15)",
                    paddingTop: "3px",
                  }}
                >
                  <span>Basis: {basisStr}</span>
                  <span>OI: {item.oiChangePct >= 0 ? "+" : ""}{item.oiChangePct}%</span>
                  <span>{item.advances}A / {item.declines}D</span>
                </div>
              </div>
            );
          })
        ) : (
          // Constituent Drill-In View
          constituentData.constituents.map((item) => {
            const isUp = item.changePct >= 0;
            const bgColor = getHeatmapTileColor(item.changePct);

            return (
              <div
                key={item.symbol}
                style={{
                  flexGrow: item.weight,
                  flexBasis: `${Math.max(100, item.weight * 14)}px`,
                  minHeight: "85px",
                  padding: "var(--spacing-2)",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: bgColor,
                  color: "#fff",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ fontWeight: 700, fontSize: "var(--font-size-sm)" }}>
                    {item.symbol}
                  </span>
                  <span style={{ fontSize: "11px", opacity: 0.9 }}>
                    {item.weight}%
                  </span>
                </div>

                <div style={{ textAlign: "center", margin: "2px 0" }}>
                  <div
                    style={{
                      fontFamily: "var(--font-family-mono)",
                      fontSize: "var(--font-size-md)",
                      fontWeight: 800,
                      textShadow: "0 1px 2px rgba(0,0,0,0.5)",
                    }}
                  >
                    {isUp ? "+" : ""}
                    {item.changePct.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: "10px", opacity: 0.85, fontFamily: "var(--font-family-mono)" }}>
                    ₹{item.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "9px",
                    borderTop: "1px solid rgba(255, 255, 255, 0.15)",
                    paddingTop: "2px",
                  }}
                >
                  <span style={{ opacity: 0.85 }}>{item.sector}</span>
                  {item.isWeightFallback ? (
                    <span
                      style={{
                        backgroundColor: "rgba(245, 158, 11, 0.8)",
                        color: "#000",
                        padding: "1px 3px",
                        borderRadius: "2px",
                        fontWeight: 700,
                      }}
                      title="Missing Weight - Fallback Equal Share Assigned"
                    >
                      Fallback Wt
                    </span>
                  ) : (
                    <span style={{ opacity: 0.75 }}>{item.weightingSource}</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export const marketHeatmapDefinition: WidgetDefinition<HeatmapSettings> = {
  id: "market-heatmap",
  title: "Market Heatmap & Breadth",
  description: "Sectoral indices and constituent heatmaps with market breadth and transparent weighting.",
  category: "analytics",
  icon: "🔥",
  defaultWidth: 540,
  defaultHeight: 460,
  schema: {
    fields: [
      {
        name: "defaultMode",
        label: "Default Mode",
        type: "select",
        default: "INDICES",
        options: [
          { label: "Sectoral Indices", value: "INDICES" },
          { label: "Constituents Drill-In", value: "CONSTITUENTS" },
        ],
      },
      {
        name: "defaultIndexName",
        label: "Default Index",
        type: "select",
        default: "NIFTY 50",
        options: [
          { label: "NIFTY 50", value: "NIFTY 50" },
          { label: "NIFTY BANK", value: "NIFTY BANK" },
          { label: "NIFTY IT", value: "NIFTY IT" },
          { label: "NIFTY AUTO", value: "NIFTY AUTO" },
        ],
      },
    ],
  },
  component: MarketHeatmapWidget,
};
