import React, { useState, useEffect, useMemo, useCallback } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  IndexCategory,
  IndexHeatmapItem,
  ConstituentHeatmapItem,
  MarketBreadth,
} from "../../heatmap/types";
import {
  calculateMarketBreadth,
  handleMissingWeights,
  getNseColorForPct,
} from "../../heatmap/engine";
import {
  ALL_INDICES_BY_CATEGORY,
  BROAD_MARKET_INDICES,
  SECTORAL_INDICES,
  THEMATIC_INDICES,
  STRATEGY_INDICES,
  NIFTY_50_AUTHENTIC_CONSTITUENTS,
  getConstituentsForIndex,
} from "../../heatmap/indicesCatalog";

export type ConstituentSortOption =
  | "WEIGHT_DESC"
  | "WEIGHT_ASC"
  | "CHANGE_DESC"
  | "CHANGE_ASC"
  | "NAME_ASC"
  | "NAME_DESC";

export type IndexSortOption =
  | "DEFAULT"
  | "CHANGE_DESC"
  | "CHANGE_ASC"
  | "WEIGHT_DESC"
  | "WEIGHT_ASC"
  | "NAME_ASC"
  | "NAME_DESC";

export interface HeatmapSettings {
  defaultMode?: "INDICES" | "CONSTITUENTS";
  defaultCategory?: IndexCategory;
  defaultIndexName?: string;
  defaultConstituentSort?: ConstituentSortOption;
  defaultIndexSort?: IndexSortOption;
}

const CATEGORY_TABS: { key: IndexCategory; label: string; count: number }[] = [
  { key: "BROAD_MARKET", label: "Broad Market Indices", count: BROAD_MARKET_INDICES.length },
  { key: "SECTORAL", label: "Sectoral Indices", count: SECTORAL_INDICES.length },
  { key: "THEMATIC", label: "Thematic Indices", count: THEMATIC_INDICES.length },
  { key: "STRATEGY", label: "Strategy Indices", count: STRATEGY_INDICES.length },
];

function formatNseTimestamp(date: Date): string {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = String(date.getDate()).padStart(2, "0");
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  return `${day}-${month}-${year} ${hours}:${minutes}:${seconds}`;
}

export const MarketHeatmapWidget: React.FC<WidgetComponentProps<HeatmapSettings>> = ({
  settings,
}) => {
  const [activeCategory, setActiveCategory] = useState<IndexCategory>(
    settings.defaultCategory || "BROAD_MARKET"
  );
  const [viewMode, setViewMode] = useState<"INDICES" | "CONSTITUENTS">(
    settings.defaultMode || "INDICES"
  );
  const [selectedIndex, setSelectedIndex] = useState<string>(
    settings.defaultIndexName || "NIFTY 50"
  );
  const [constituentSort, setConstituentSort] = useState<ConstituentSortOption>(
    settings.defaultConstituentSort || "WEIGHT_DESC"
  );
  const [indexSort, setIndexSort] = useState<IndexSortOption>(
    settings.defaultIndexSort || "DEFAULT"
  );

  const [categoryData, setCategoryData] = useState<Record<IndexCategory, IndexHeatmapItem[]>>({
    BROAD_MARKET: BROAD_MARKET_INDICES,
    SECTORAL: SECTORAL_INDICES,
    THEMATIC: THEMATIC_INDICES,
    STRATEGY: STRATEGY_INDICES,
  });

  const [constituentsCache, setConstituentsCache] = useState<Record<string, ConstituentHeatmapItem[]>>({
    "NIFTY 50": NIFTY_50_AUTHENTIC_CONSTITUENTS,
  });

  const [isStreaming, setIsStreaming] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  // Attempt backend fetch if API is reachable
  useEffect(() => {
    fetch("/api/v1/heatmap/indices")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setCategoryData((prev) => {
            const updated = { ...prev };
            data.forEach((d) => {
              const cat: IndexCategory = (d.category as IndexCategory) || "SECTORAL";
              if (updated[cat]) {
                const idx = updated[cat].findIndex((i) => i.indexName === d.index_name);
                if (idx >= 0) {
                  updated[cat][idx] = {
                    ...updated[cat][idx],
                    ltp: d.ltp,
                    changePct: d.change_pct,
                    advances: d.advances,
                    declines: d.declines,
                    unchanged: d.unchanged,
                    futuresBasis: d.futures_basis,
                    oiChangePct: d.oi_change_pct,
                  };
                }
              }
            });
            return updated;
          });
        }
      })
      .catch(() => {});
  }, []);

  // Fetch or resolve constituents when selectedIndex changes
  useEffect(() => {
    if (!constituentsCache[selectedIndex]) {
      // First try backend API
      fetch(`/api/v1/heatmap/${encodeURIComponent(selectedIndex)}/constituents`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data && Array.isArray(data.constituents) && data.constituents.length > 0) {
            setConstituentsCache((prev) => ({
              ...prev,
              [selectedIndex]: data.constituents.map((c: any) => ({
                symbol: c.symbol,
                sector: c.sector,
                weight: c.weight,
                isWeightFallback: c.is_weight_fallback,
                weightingSource: c.weighting_source,
                changePct: c.change_pct,
                ltp: c.ltp,
                volume: c.volume,
              })),
            }));
          } else {
            // Use authentic / realistic generated fallback
            const generated = getConstituentsForIndex(selectedIndex);
            setConstituentsCache((prev) => ({
              ...prev,
              [selectedIndex]: generated,
            }));
          }
        })
        .catch(() => {
          const generated = getConstituentsForIndex(selectedIndex);
          setConstituentsCache((prev) => ({
            ...prev,
            [selectedIndex]: generated,
          }));
        });
    }
  }, [selectedIndex, constituentsCache]);

  // Live streaming simulation tick
  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      setLastUpdated(new Date());

      if (viewMode === "INDICES") {
        setCategoryData((prev) => {
          const list = prev[activeCategory];
          if (!list || list.length === 0) return prev;

          // Pick 3 random items to adjust tick
          const updated = [...list];
          for (let k = 0; k < Math.min(3, updated.length); k++) {
            const randIdx = Math.floor(Math.random() * updated.length);
            const item = { ...updated[randIdx] };
            const delta = Number(((Math.random() - 0.5) * 0.08).toFixed(2));
            item.changePct = Number((item.changePct + delta).toFixed(2));
            item.ltp = Number((item.ltp * (1 + delta / 100)).toFixed(2));
            updated[randIdx] = item;
          }

          return { ...prev, [activeCategory]: updated };
        });
      } else {
        setConstituentsCache((prev) => {
          const list = prev[selectedIndex];
          if (!list || list.length === 0) return prev;

          const updated = [...list];
          for (let k = 0; k < Math.min(4, updated.length); k++) {
            const randIdx = Math.floor(Math.random() * updated.length);
            const item = { ...updated[randIdx] };
            const delta = Number(((Math.random() - 0.5) * 0.12).toFixed(2));
            item.changePct = Number((item.changePct + delta).toFixed(2));
            item.ltp = Number((item.ltp * (1 + delta / 100)).toFixed(2));
            updated[randIdx] = item;
          }

          return { ...prev, [selectedIndex]: updated };
        });
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [isStreaming, viewMode, activeCategory, selectedIndex]);

  // Toggle sort direction helper
  const toggleSortDirection = useCallback(() => {
    if (viewMode === "CONSTITUENTS") {
      setConstituentSort((prev) => {
        if (prev === "WEIGHT_DESC") return "WEIGHT_ASC";
        if (prev === "WEIGHT_ASC") return "WEIGHT_DESC";
        if (prev === "CHANGE_DESC") return "CHANGE_ASC";
        if (prev === "CHANGE_ASC") return "CHANGE_DESC";
        if (prev === "NAME_ASC") return "NAME_DESC";
        return "NAME_ASC";
      });
    } else {
      setIndexSort((prev) => {
        if (prev === "CHANGE_DESC") return "CHANGE_ASC";
        if (prev === "CHANGE_ASC") return "CHANGE_DESC";
        if (prev === "WEIGHT_DESC") return "WEIGHT_ASC";
        if (prev === "WEIGHT_ASC") return "WEIGHT_DESC";
        if (prev === "NAME_ASC") return "NAME_DESC";
        if (prev === "NAME_DESC") return "NAME_ASC";
        return "CHANGE_DESC";
      });
    }
  }, [viewMode]);

  // Current active indices list (sorted as per indexSort)
  const currentIndicesList = useMemo(() => {
    const list = [...(categoryData[activeCategory] || ALL_INDICES_BY_CATEGORY[activeCategory])];
    switch (indexSort) {
      case "CHANGE_DESC":
        return list.sort((a, b) => b.changePct - a.changePct || a.indexName.localeCompare(b.indexName));
      case "CHANGE_ASC":
        return list.sort((a, b) => a.changePct - b.changePct || a.indexName.localeCompare(b.indexName));
      case "WEIGHT_DESC":
        return list.sort((a, b) => b.weight - a.weight || a.indexName.localeCompare(b.indexName));
      case "WEIGHT_ASC":
        return list.sort((a, b) => a.weight - b.weight || a.indexName.localeCompare(b.indexName));
      case "NAME_ASC":
        return list.sort((a, b) => a.indexName.localeCompare(b.indexName));
      case "NAME_DESC":
        return list.sort((a, b) => b.indexName.localeCompare(a.indexName));
      case "DEFAULT":
      default:
        return list;
    }
  }, [categoryData, activeCategory, indexSort]);

  // Current active constituents list (sorted as per constituentSort, defaulted to weightage high to low)
  const currentConstituents = useMemo(() => {
    const list = constituentsCache[selectedIndex] || getConstituentsForIndex(selectedIndex);
    const resolved = handleMissingWeights(list).constituents;
    const sorted = [...resolved];
    switch (constituentSort) {
      case "WEIGHT_DESC":
        return sorted.sort((a, b) => b.weight - a.weight || a.symbol.localeCompare(b.symbol));
      case "WEIGHT_ASC":
        return sorted.sort((a, b) => a.weight - b.weight || a.symbol.localeCompare(b.symbol));
      case "CHANGE_DESC":
        return sorted.sort((a, b) => b.changePct - a.changePct || a.symbol.localeCompare(b.symbol));
      case "CHANGE_ASC":
        return sorted.sort((a, b) => a.changePct - b.changePct || a.symbol.localeCompare(b.symbol));
      case "NAME_ASC":
        return sorted.sort((a, b) => a.symbol.localeCompare(b.symbol));
      case "NAME_DESC":
        return sorted.sort((a, b) => b.symbol.localeCompare(a.symbol));
      default:
        return sorted.sort((a, b) => b.weight - a.weight || a.symbol.localeCompare(b.symbol));
    }
  }, [constituentsCache, selectedIndex, constituentSort]);

  // Compute active market breadth
  const activeBreadth: MarketBreadth = useMemo(() => {
    if (viewMode === "INDICES") {
      return calculateMarketBreadth(currentIndicesList);
    }
    return calculateMarketBreadth(currentConstituents);
  }, [viewMode, currentIndicesList, currentConstituents]);

  const handleCategorySelect = (category: IndexCategory) => {
    setActiveCategory(category);
    setViewMode("INDICES");
  };

  const handleIndexClick = (indexName: string) => {
    setSelectedIndex(indexName);
    setViewMode("CONSTITUENTS");
  };

  const handleBackToOverview = () => {
    setViewMode("INDICES");
  };

  const handleStockClick = (symbol: string) => {
    window.dispatchEvent(
      new CustomEvent("shreenexa:select-symbol", { detail: { symbol } })
    );
  };

  const handleManualRefresh = useCallback(() => {
    setLastUpdated(new Date());
    if (viewMode === "INDICES") {
      setCategoryData((prev) => {
        const list = prev[activeCategory];
        if (!list) return prev;
        const updated = list.map((item) => {
          const delta = Number(((Math.random() - 0.5) * 0.05).toFixed(2));
          return {
            ...item,
            changePct: Number((item.changePct + delta).toFixed(2)),
            ltp: Number((item.ltp * (1 + delta / 100)).toFixed(2)),
          };
        });
        return { ...prev, [activeCategory]: updated };
      });
    } else {
      setConstituentsCache((prev) => {
        const list = prev[selectedIndex];
        if (!list) return prev;
        const updated = list.map((item) => {
          const delta = Number(((Math.random() - 0.5) * 0.06).toFixed(2));
          return {
            ...item,
            changePct: Number((item.changePct + delta).toFixed(2)),
            ltp: Number((item.ltp * (1 + delta / 100)).toFixed(2)),
          };
        });
        return { ...prev, [selectedIndex]: updated };
      });
    }
  }, [viewMode, activeCategory, selectedIndex]);

  // Header Title calculation
  const headerTitle = useMemo(() => {
    if (viewMode === "CONSTITUENTS") {
      return `${selectedIndex}(${currentConstituents.length})`;
    }
    const catTab = CATEGORY_TABS.find((t) => t.key === activeCategory);
    return `${catTab?.label || "Indices"}(${currentIndicesList.length})`;
  }, [viewMode, selectedIndex, currentConstituents.length, activeCategory, currentIndicesList.length]);

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "row",
        backgroundColor: "var(--bg-surface)",
        color: "var(--text-primary)",
        fontSize: "var(--font-size-sm)",
        overflow: "hidden",
        userSelect: "none",
      }}
    >
      {/* =================================================================== */}
      {/* Left Navigation Panel                                               */}
      {/* =================================================================== */}
      <div
        style={{
          width: "205px",
          minWidth: "190px",
          maxWidth: "240px",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "var(--bg-elevated)",
          borderRight: "1px solid var(--border-subtle)",
          overflowY: "auto",
        }}
      >
        {viewMode === "INDICES" ? (
          // 1. Category Selector (Images 1, 2, 3)
          <div style={{ display: "flex", flexDirection: "column", padding: "12px 8px" }}>
            <div
              style={{
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                overflow: "hidden",
                backgroundColor: "var(--bg-surface)",
              }}
            >
              {CATEGORY_TABS.map((tab, idx) => {
                const isActive = activeCategory === tab.key;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => handleCategorySelect(tab.key)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "10px 14px",
                      background: isActive ? "rgba(216, 90, 56, 0.08)" : "transparent",
                      border: "none",
                      borderLeft: isActive ? "3px solid #d85a38" : "3px solid transparent",
                      borderBottom:
                        idx < CATEGORY_TABS.length - 1 ? "1px solid var(--border-subtle)" : "none",
                      color: isActive ? "#d85a38" : "var(--text-primary)",
                      fontWeight: isActive ? 700 : 500,
                      fontSize: "12.5px",
                      cursor: "pointer",
                      transition: "background 0.15s ease",
                      outline: "none",
                    }}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

          </div>
        ) : (
          // 2. Index List for Drill-In Mode (Image 4)
          <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <div
              style={{
                padding: "10px 12px",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                backgroundColor: "var(--bg-surface)",
              }}
            >
              <button
                type="button"
                onClick={handleBackToOverview}
                style={{
                  background: "none",
                  border: "none",
                  color: "#d85a38",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: 0,
                }}
              >
                ← Categories
              </button>
              <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>
                {CATEGORY_TABS.find((t) => t.key === activeCategory)?.label}
              </span>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "8px 6px" }}>
              <div
                style={{
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  overflow: "hidden",
                  backgroundColor: "var(--bg-surface)",
                }}
              >
                {currentIndicesList.map((idxItem, i) => {
                  const isSelected = selectedIndex === idxItem.indexName;
                  return (
                    <button
                      key={idxItem.indexName}
                      type="button"
                      onClick={() => setSelectedIndex(idxItem.indexName)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "8px 10px",
                        background: isSelected ? "rgba(216, 90, 56, 0.08)" : "transparent",
                        border: "none",
                        borderLeft: isSelected ? "3px solid #d85a38" : "3px solid transparent",
                        borderBottom:
                          i < currentIndicesList.length - 1 ? "1px solid var(--border-subtle)" : "none",
                        color: isSelected ? "#d85a38" : "var(--text-primary)",
                        fontWeight: isSelected ? 700 : 500,
                        fontSize: "11px",
                        cursor: "pointer",
                        outline: "none",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        display: "block",
                      }}
                      title={idxItem.indexName}
                    >
                      {idxItem.indexName}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* =================================================================== */}
      {/* Right Content Area                                                  */}
      {/* =================================================================== */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          height: "100%",
          overflow: "hidden",
        }}
      >
        {/* 1. Header Toolbar (Images 1-4) */}
        <div
          style={{
            padding: "8px 14px",
            backgroundColor: "var(--bg-surface)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
          }}
        >
          {/* Left Title & Back Navigation */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {viewMode === "CONSTITUENTS" && (
              <button
                type="button"
                onClick={handleBackToOverview}
                style={{
                  background: "none",
                  border: "none",
                  color: "#d85a38",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: "2px 6px",
                  borderRadius: "4px",
                }}
              >
                ← Back
              </button>
            )}

            <span
              style={{
                fontSize: "16px",
                fontWeight: 800,
                color: "#2a225e",
                letterSpacing: "0.2px",
              }}
            >
              {headerTitle}
            </span>

            {/* View Mode icons */}
            <div style={{ display: "flex", alignItems: "center", gap: "4px", marginLeft: "4px", opacity: 0.7 }}>
              <span style={{ fontSize: "14px", cursor: "pointer" }} title="Grid View">▦</span>
              <span style={{ fontSize: "14px", cursor: "pointer" }} title="Chart View">📊</span>
            </div>
          </div>

          {/* Right Controls: Sort selector, Streaming toggle, Legend Badges, Timestamp, Refresh */}
          <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
            {/* Sort Control */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
                backgroundColor: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "2px 6px",
              }}
            >
              <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Sort:</span>
              <select
                aria-label="Sort order"
                value={viewMode === "CONSTITUENTS" ? constituentSort : indexSort}
                onChange={(e) => {
                  if (viewMode === "CONSTITUENTS") {
                    setConstituentSort(e.target.value as ConstituentSortOption);
                  } else {
                    setIndexSort(e.target.value as IndexSortOption);
                  }
                }}
                style={{
                  backgroundColor: "transparent",
                  color: "var(--text-primary)",
                  border: "none",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  outline: "none",
                  paddingRight: "2px",
                }}
              >
                {viewMode === "CONSTITUENTS" ? (
                  <>
                    <option value="WEIGHT_DESC">Weightage: High → Low (Default)</option>
                    <option value="WEIGHT_ASC">Weightage: Low → High</option>
                    <option value="CHANGE_DESC">% Change: High → Low (Gainers)</option>
                    <option value="CHANGE_ASC">% Change: Low → High (Losers)</option>
                    <option value="NAME_ASC">Symbol: A → Z</option>
                    <option value="NAME_DESC">Symbol: Z → A</option>
                  </>
                ) : (
                  <>
                    <option value="DEFAULT">Default (NSE List)</option>
                    <option value="CHANGE_DESC">% Change: High → Low (Gainers)</option>
                    <option value="CHANGE_ASC">% Change: Low → High (Losers)</option>
                    <option value="WEIGHT_DESC">Weight: High → Low</option>
                    <option value="WEIGHT_ASC">Weight: Low → High</option>
                    <option value="NAME_ASC">Index Name: A → Z</option>
                    <option value="NAME_DESC">Index Name: Z → A</option>
                  </>
                )}
              </select>
              <button
                type="button"
                onClick={toggleSortDirection}
                aria-label="Reverse sort direction"
                title="Reverse sort direction"
                style={{
                  background: "none",
                  border: "none",
                  color: "#d85a38",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 800,
                  padding: "0 2px",
                  lineHeight: "1",
                }}
              >
                ⇅
              </button>
            </div>

            {/* Streaming Toggle */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px" }}>
              <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Streaming</span>
              <button
                type="button"
                onClick={() => setIsStreaming(!isStreaming)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  border: isStreaming ? "1px solid #0b7a3e" : "1px solid var(--border-subtle)",
                  backgroundColor: isStreaming ? "#0b7a3e" : "var(--bg-elevated)",
                  color: isStreaming ? "#ffffff" : "var(--text-muted)",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontSize: "10.5px",
                  transition: "all 0.15s ease",
                }}
              >
                {isStreaming ? "On" : "Off"}
              </button>
            </div>

            {/* Official 7-tier NSE Legend Badges */}
            <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
              <span style={{ backgroundColor: "#0b7a3e", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>5</span>
              <span style={{ backgroundColor: "#28a745", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>3</span>
              <span style={{ backgroundColor: "#58ba6d", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>1</span>
              <span style={{ backgroundColor: "#8e99a8", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>0%</span>
              <span style={{ backgroundColor: "#e87070", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>-1</span>
              <span style={{ backgroundColor: "#c9302c", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>-3</span>
              <span style={{ backgroundColor: "#8b0000", color: "#fff", padding: "1px 7px", borderRadius: "3px", fontWeight: 700, fontSize: "10px" }}>-5</span>
            </div>

            {/* Timestamp & Refresh */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "var(--text-muted)" }}>
              <span>As on {formatNseTimestamp(lastUpdated)} IST</span>
              <button
                type="button"
                onClick={handleManualRefresh}
                title="Refresh market data"
                style={{
                  background: "none",
                  border: "none",
                  color: "#d85a38",
                  fontSize: "14px",
                  fontWeight: 800,
                  cursor: "pointer",
                  padding: "0 2px",
                }}
              >
                ↻
              </button>
            </div>
          </div>
        </div>

        {/* 2. Sentiment & Market Breadth Bar */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "var(--spacing-2)",
            padding: "4px 14px",
            backgroundColor: "var(--bg-elevated)",
            borderBottom: "1px solid var(--border-subtle)",
            fontSize: "11px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
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
                backgroundColor: "var(--bg-surface)",
                color: "var(--text-muted)",
              }}
            >
              ● {activeBreadth.unchanged} Unch
            </span>
            <span style={{ color: "var(--text-muted)" }}>
              A/D: <strong>{activeBreadth.advanceDeclineRatio.toFixed(2)}</strong>
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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
                    : "var(--bg-surface)",
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

        {/* 3. Heatmap Grid Matrix */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "12px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
            gap: "8px",
            alignContent: "flex-start",
          }}
        >
          {viewMode === "INDICES" ? (
            // Category Indices Heatmap (Images 1, 2, 3)
            currentIndicesList.map((item) => {
              const isUp = item.changePct >= 0;
              const bgColor = getNseColorForPct(item.changePct);

              return (
                <div
                  key={item.indexName}
                  data-testid="index-card"
                  onClick={() => handleIndexClick(item.indexName)}
                  style={{
                    backgroundColor: bgColor,
                    borderRadius: "6px",
                    padding: "8px 10px",
                    color: "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    minHeight: "72px",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.15)",
                    transition: "transform 0.12s ease, box-shadow 0.12s ease",
                  }}
                  title={`Click to view constituents of ${item.indexName}`}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: "4px",
                    }}
                  >
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: "11px",
                        lineHeight: "1.25",
                        letterSpacing: "0.1px",
                        whiteSpace: "normal",
                        wordBreak: "break-word",
                        flex: 1,
                      }}
                    >
                      {item.indexName}
                    </div>
                    {item.weight > 0 && (
                      <span
                        style={{
                          fontSize: "9px",
                          opacity: 0.88,
                          fontFamily: "var(--font-family-mono)",
                          fontWeight: 700,
                          backgroundColor: "rgba(0, 0, 0, 0.22)",
                          padding: "1px 3px",
                          borderRadius: "2px",
                          whiteSpace: "nowrap",
                        }}
                        title={`Category weight: ${item.weight.toFixed(1)}%`}
                      >
                        {item.weight.toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-end",
                      marginTop: "8px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "11.5px",
                        fontFamily: "var(--font-family-mono)",
                        fontWeight: 700,
                      }}
                    >
                      {item.ltp.toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </span>
                    <span
                      style={{
                        fontSize: "11px",
                        fontFamily: "var(--font-family-mono)",
                        fontWeight: 700,
                      }}
                    >
                      {isUp ? "+" : ""}
                      {item.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            // Constituent Drill-In Heatmap (Image 4)
            currentConstituents.map((stock) => {
              const isUp = stock.changePct >= 0;
              const bgColor = getNseColorForPct(stock.changePct);

              return (
                <div
                  key={stock.symbol}
                  data-testid="constituent-card"
                  onClick={() => handleStockClick(stock.symbol)}
                  style={{
                    backgroundColor: bgColor,
                    borderRadius: "6px",
                    padding: "8px 10px",
                    color: "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    minHeight: "68px",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.15)",
                    position: "relative",
                    transition: "transform 0.12s ease, box-shadow 0.12s ease",
                  }}
                  title={`${stock.name || stock.symbol} (${stock.sector}) - Weight: ${stock.weight.toFixed(2)}%`}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: "4px",
                    }}
                  >
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: "11.5px",
                        letterSpacing: "0.2px",
                      }}
                    >
                      {stock.symbol}
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                      {stock.isWeightFallback && (
                        <span
                          style={{
                            backgroundColor: "rgba(245, 158, 11, 0.95)",
                            color: "#000",
                            padding: "1px 3px",
                            borderRadius: "2px",
                            fontSize: "8px",
                            fontWeight: 700,
                            lineHeight: "1",
                          }}
                          title="Missing Official Weight - Estimated Share Assigned"
                        >
                          Est
                        </span>
                      )}
                      <span
                        style={{
                          fontSize: "9.5px",
                          opacity: 0.9,
                          fontFamily: "var(--font-family-mono)",
                          fontWeight: 700,
                          backgroundColor: "rgba(0, 0, 0, 0.22)",
                          padding: "1px 3.5px",
                          borderRadius: "2px",
                          lineHeight: "1.1",
                        }}
                        title={`Index Weight: ${stock.weight.toFixed(2)}%`}
                      >
                        {stock.weight.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-end",
                      marginTop: "8px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "11.5px",
                        fontFamily: "var(--font-family-mono)",
                        fontWeight: 700,
                      }}
                    >
                      {stock.ltp.toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </span>
                    <span
                      style={{
                        fontSize: "11px",
                        fontFamily: "var(--font-family-mono)",
                        fontWeight: 700,
                      }}
                    >
                      {isUp ? "+" : ""}
                      {stock.changePct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export const marketHeatmapDefinition: WidgetDefinition<HeatmapSettings> = {
  id: "market-heatmap",
  title: "Market Heatmap & Breadth",
  description:
    "Sectoral indices and constituent heatmaps with market breadth and transparent weighting.",
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
