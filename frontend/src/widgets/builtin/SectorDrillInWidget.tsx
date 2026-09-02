import React, { useState, useEffect } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { IndexDrillInResponse } from "../../sector/types";
import { fetchSectorCatalog, fetchIndexDrillIn } from "../../sector/api";
import { createWatchlist, addSymbolToWatchlist } from "../../watchlist/storage";

export interface SectorDrillInSettings {
  defaultIndexName?: string;
}

export const SectorDrillInWidget: React.FC<WidgetComponentProps<SectorDrillInSettings>> = ({
  settings,
}) => {
  const [selectedIndex, setSelectedIndex] = useState<string>(
    settings.defaultIndexName || "NIFTY 50"
  );
  const [isHistorical, setIsHistorical] = useState(false);
  const [historicalDate, setHistoricalDate] = useState("2024-01-01");
  const [drillInData, setDrillInData] = useState<IndexDrillInResponse | null>(null);
  const [catalog, setCatalog] = useState<{ index_name: string; sector: string }[]>([]);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  useEffect(() => {
    fetchSectorCatalog().then((cat) => setCatalog(cat));
  }, []);

  useEffect(() => {
    const asOf = isHistorical ? historicalDate : undefined;
    fetchIndexDrillIn(selectedIndex, asOf).then((data) => {
      setDrillInData(data);
    });
  }, [selectedIndex, isHistorical, historicalDate]);

  const handleExportToWatchlist = () => {
    if (!drillInData || drillInData.constituents.length === 0) return;

    const wlName = `${drillInData.index_name} (${isHistorical ? historicalDate : "Live"})`;
    const newWl = createWatchlist(wlName, `Exported from ${drillInData.index_name} drill-in`);

    drillInData.constituents.forEach((item, idx) => {
      addSymbolToWatchlist(newWl.id, {
        symbol: item.symbol,
        segment: "NSE_EQ",
        securityId: (1000 + idx).toString(),
        tradingSymbol: `${item.symbol}-EQ`,
        ltp: item.ltp || 100,
        changePct: item.changePct || 0,
      });
    });

    setExportNotice(`Exported ${drillInData.constituents.length} symbols to watchlist "${wlName}"!`);
    setTimeout(() => setExportNotice(null), 4000);
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
      {/* 1. Control Header: Sector Selector & Date Picker */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "var(--spacing-2)",
          padding: "var(--spacing-2)",
          backgroundColor: "var(--bg-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <label style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontWeight: 600 }}>
            Index / Sector:
          </label>
          <select
            value={selectedIndex}
            onChange={(e) => setSelectedIndex(e.target.value)}
            style={{
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--bg-input)",
              color: "var(--text-primary)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
            }}
          >
            {catalog.map((cat) => (
              <option key={cat.index_name} value={cat.index_name}>
                {cat.index_name} ({cat.sector})
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <label style={{ fontSize: "var(--font-size-xs)", display: "flex", alignItems: "center", gap: "4px" }}>
            <input
              type="checkbox"
              checked={isHistorical}
              onChange={(e) => setIsHistorical(e.target.checked)}
            />
            Historical Date
          </label>

          {isHistorical && (
            <input
              type="date"
              value={historicalDate}
              onChange={(e) => setHistoricalDate(e.target.value)}
              style={{
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "var(--bg-input)",
                color: "var(--text-primary)",
                fontSize: "var(--font-size-xs)",
              }}
            />
          )}

          <button
            type="button"
            onClick={handleExportToWatchlist}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-brand)",
              backgroundColor: "transparent",
              color: "var(--color-brand)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
            title="Export as Watchlist"
          >
            📋 Save to Watchlist
          </button>
        </div>
      </div>

      {/* 2. Visible Provenance & Stale Fallback Banner */}
      {drillInData && (
        <div
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "var(--font-size-xs)",
            backgroundColor: drillInData.has_fallback ? "rgba(245, 158, 11, 0.15)" : "rgba(16, 185, 129, 0.15)",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          {drillInData.has_fallback ? (
            <span style={{ color: "var(--color-warning, #f59e0b)", fontWeight: 600 }}>
              ⚠️ Fallback / Stale Snapshot Active (Source: {drillInData.provenance_sources.join(", ")})
            </span>
          ) : (
            <span style={{ color: "var(--color-up)", fontWeight: 600 }}>
              ✓ Verified Official Point-in-Time Membership
            </span>
          )}

          <span style={{ color: "var(--text-muted)" }}>
            Effective As-Of: {drillInData.as_of || "Latest"} · {drillInData.total_constituents} Constituents
          </span>
        </div>
      )}

      {/* Export notification toast */}
      {exportNotice && (
        <div
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "var(--color-up-bg)",
            color: "var(--color-up)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            textAlign: "center",
          }}
        >
          {exportNotice}
        </div>
      )}

      {/* 3. Sector Distribution Summary Chips */}
      {drillInData && Object.keys(drillInData.sector_weights).length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--spacing-1)",
            padding: "var(--spacing-1) var(--spacing-2)",
            borderBottom: "1px solid var(--border-subtle)",
            backgroundColor: "var(--bg-elevated)",
          }}
        >
          {Object.entries(drillInData.sector_weights).map(([sec, wt]) => (
            <span
              key={sec}
              style={{
                fontSize: "10px",
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {sec}: <strong>{wt}%</strong>
            </span>
          ))}
        </div>
      )}

      {/* 4. Constituents Data Table */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {!drillInData || drillInData.constituents.length === 0 ? (
          <div style={{ padding: "var(--spacing-3)", color: "var(--text-muted)" }}>
            Loading index constituents...
          </div>
        ) : (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "left",
              fontSize: "var(--font-size-xs)",
            }}
          >
            <thead>
              <tr
                style={{
                  backgroundColor: "var(--bg-elevated)",
                  color: "var(--text-muted)",
                  borderBottom: "1px solid var(--border-subtle)",
                  position: "sticky",
                  top: 0,
                }}
              >
                <th style={{ padding: "6px 8px" }}>Symbol</th>
                <th style={{ padding: "6px 8px" }}>Sector</th>
                <th style={{ padding: "6px 8px", textAlign: "right" }}>Weight (%)</th>
                <th style={{ padding: "6px 8px", textAlign: "right" }}>LTP (₹)</th>
                <th style={{ padding: "6px 8px", textAlign: "right" }}>Chg %</th>
                <th style={{ padding: "6px 8px", textAlign: "center" }}>Provenance</th>
                <th style={{ padding: "6px 8px", textAlign: "center" }}>Effective Range</th>
              </tr>
            </thead>
            <tbody>
              {drillInData.constituents.map((item) => {
                const isUp = (item.changePct || 0) >= 0;
                return (
                  <tr
                    key={item.symbol}
                    style={{ borderBottom: "1px solid var(--border-subtle)" }}
                  >
                    <td style={{ padding: "6px 8px", fontWeight: 600 }}>{item.symbol}</td>
                    <td style={{ padding: "6px 8px", color: "var(--text-muted)" }}>
                      {item.sector || "—"}
                    </td>
                    <td style={{ padding: "6px 8px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      {item.weight !== null ? `${item.weight}%` : "—"}
                    </td>
                    <td style={{ padding: "6px 8px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      {item.ltp !== undefined ? `₹${item.ltp.toFixed(2)}` : "—"}
                    </td>
                    <td style={{ padding: "6px 8px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      {item.changePct !== undefined ? (
                        <span style={{ color: isUp ? "var(--color-up)" : "var(--color-down)" }}>
                          {isUp ? "+" : ""}{item.changePct.toFixed(2)}%
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td style={{ padding: "6px 8px", textAlign: "center" }}>
                      <span
                        style={{
                          fontSize: "10px",
                          padding: "1px 5px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: item.source.toLowerCase().includes("fallback")
                            ? "rgba(245, 158, 11, 0.2)"
                            : "var(--bg-elevated)",
                          color: item.source.toLowerCase().includes("fallback")
                            ? "var(--color-warning, #f59e0b)"
                            : "var(--text-muted)",
                          fontWeight: 600,
                        }}
                      >
                        {item.source}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: "6px 8px",
                        textAlign: "center",
                        fontSize: "10px",
                        color: "var(--text-muted)",
                      }}
                    >
                      {item.valid_from} → {item.valid_to || "Present"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export const sectorDrillInDefinition: WidgetDefinition<SectorDrillInSettings> = {
  id: "sector-drill-in",
  title: "Sector & Index Drill-In",
  description: "Browse sector constituents, effective membership intervals, and transparent provenance.",
  category: "watchlist",
  icon: "📊",
  defaultWidth: 460,
  defaultHeight: 520,
  schema: {
    fields: [
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
  component: SectorDrillInWidget,
};
