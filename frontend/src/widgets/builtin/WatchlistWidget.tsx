import React, { useState, useEffect, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  Watchlist,
  WatchlistColumn,
  ALL_COLUMNS,
  WatchlistItem,
} from "../../watchlist/types";
import {
  DepthLevelType,
  MarketDepthBook,
} from "../../depth/types";
import {
  generateMockDepthBook,
  resolveSegmentDepthCapability,
} from "../../depth/engine";
import {
  loadWatchlists,
  createWatchlist,
  deleteWatchlist,
  addSymbolToWatchlist,
  removeSymbolFromWatchlist,
  moveItem,
  updateWatchlist,
  KNOWN_EQUITY_INSTRUMENTS,
  resolveCatalogInstrument,
  CatalogInstrument,
} from "../../watchlist/storage";
import { SymbolSearchDropdown } from "./SymbolSearchDropdown";

export interface WatchlistSettings {
  defaultWatchlistId?: string;
  refreshIntervalSec?: number;
}

export const WatchlistWidget: React.FC<WidgetComponentProps<WatchlistSettings>> = ({
  settings,
}) => {
  const [watchlists, setWatchlists] = useState<Watchlist[]>(() => loadWatchlists());
  const [activeWatchlistId, setActiveWatchlistId] = useState<string>(() => {
    const initial = loadWatchlists();
    if (settings.defaultWatchlistId && initial.some((w) => w.id === settings.defaultWatchlistId)) {
      return settings.defaultWatchlistId;
    }
    return initial[0]?.id || "wl-nifty50";
  });

  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [newWatchlistName, setNewWatchlistName] = useState("");
  const [isConfiguringColumns, setIsConfiguringColumns] = useState(false);
  const [symbolSearchQuery, setSymbolSearchQuery] = useState("");
  const [addSymbolError, setAddSymbolError] = useState<string | null>(null);

  // Zerodha-style row hover, selection, depth modal, and more actions
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [depthItem, setDepthItem] = useState<WatchlistItem | null>(null);
  const [depthLevelType, setDepthLevelType] = useState<DepthLevelType>("LEVEL_20");
  const [moreMenuSymbol, setMoreMenuSymbol] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Auto-dismiss notice toast
  useEffect(() => {
    if (actionNotice) {
      const timer = setTimeout(() => setActionNotice(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [actionNotice]);

  // Market Depth capability & mock book
  const depthCapability = useMemo(() => {
    if (!depthItem) return null;
    return resolveSegmentDepthCapability(depthItem.segment, depthLevelType);
  }, [depthItem, depthLevelType]);

  const depthBook: MarketDepthBook | null = useMemo(() => {
    if (!depthItem || !depthCapability) return null;
    const baseLtp = (depthItem.ltp ?? 0) > 0 ? (depthItem.ltp as number) : 1000.0;
    return generateMockDepthBook(
      depthItem.symbol,
      depthItem.segment,
      depthLevelType,
      baseLtp,
      Number(depthItem.securityId) || 1000
    );
  }, [depthItem, depthCapability, depthLevelType]);

  // Helper for instrument segment badge
  const getSegmentBadge = (item: WatchlistItem) => {
    const seg = item.segment || "NSE_EQ";
    const instType = item.instrumentType || "EQUITY";

    if (instType === "INDEX" || seg === "IDX_I") {
      return { label: "INDICES", bg: "rgba(163, 113, 247, 0.15)", color: "#a371f7", border: "rgba(163, 113, 247, 0.3)" };
    }
    if (instType === "ETF") {
      return { label: "ETF", bg: "rgba(46, 160, 67, 0.15)", color: "#3fb950", border: "rgba(46, 160, 67, 0.3)" };
    }
    if (seg.startsWith("MCX") || instType === "FUTCOM") {
      return { label: "MCX", bg: "rgba(240, 136, 62, 0.15)", color: "#f0883e", border: "rgba(240, 136, 62, 0.3)" };
    }
    if (seg.includes("CURRENCY") || instType === "FUTCUR") {
      return { label: "FOREX", bg: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", border: "rgba(56, 189, 248, 0.3)" };
    }
    if (seg === "NSE_FNO") {
      return { label: "NFO", bg: "rgba(88, 166, 255, 0.15)", color: "#58a6ff", border: "rgba(88, 166, 255, 0.3)" };
    }
    if (seg === "BSE_EQ") {
      return { label: "BSE", bg: "rgba(210, 153, 34, 0.15)", color: "#d29922", border: "rgba(210, 153, 34, 0.3)" };
    }
    return { label: "NSE", bg: "rgba(56, 139, 253, 0.15)", color: "#58a6ff", border: "rgba(56, 139, 253, 0.3)" };
  };

  // Reload watchlists from storage
  const refreshWatchlists = () => {
    const updated = loadWatchlists();
    setWatchlists(updated);
  };

  const activeWatchlist = useMemo(() => {
    return watchlists.find((w) => w.id === activeWatchlistId) || watchlists[0];
  }, [watchlists, activeWatchlistId]);

  // Keep activeWatchlistId synced if active watchlist was deleted
  useEffect(() => {
    if (!watchlists.some((w) => w.id === activeWatchlistId) && watchlists.length > 0) {
      setActiveWatchlistId(watchlists[0].id);
    }
  }, [watchlists, activeWatchlistId]);

  const handleCreateWatchlist = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWatchlistName.trim()) return;
    const created = createWatchlist(newWatchlistName.trim());
    refreshWatchlists();
    setActiveWatchlistId(created.id);
    setNewWatchlistName("");
    setIsCreatingNew(false);
  };

  const handleDeleteWatchlist = (id: string) => {
    if (deleteWatchlist(id)) {
      refreshWatchlists();
    }
  };

  const handleAddResolved = (item: CatalogInstrument) => {
    if (!activeWatchlist) return;
    setAddSymbolError(null);

    addSymbolToWatchlist(activeWatchlist.id, {
      symbol: item.symbol,
      segment: item.segment,
      securityId: item.securityId,
      tradingSymbol: item.tradingSymbol,
      name: item.name,
      instrumentType: item.instrumentType,
      ltp: item.ltp ?? 0,
      changePct: item.changePct ?? 0,
      changeAbs: 0,
      volume: 0,
      expiry: item.expiry,
      strike: item.strike,
      optionType: item.optionType,
    });

    refreshWatchlists();
    setSymbolSearchQuery("");
  };

  const handleAddSymbol = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const raw = (customQuery ?? symbolSearchQuery).trim();
    if (!raw || !activeWatchlist) return;

    const sym = raw.toUpperCase();
    setAddSymbolError(null);

    // 1. Check local catalog resolver (handles Nifty50, NIFTY 50, aliases, indices, equities, F&O)
    let resolved: CatalogInstrument | null = resolveCatalogInstrument(sym);

    // 2. Check KNOWN_EQUITY_INSTRUMENTS directly if not resolved
    if (!resolved && KNOWN_EQUITY_INSTRUMENTS[sym]) {
      const meta = KNOWN_EQUITY_INSTRUMENTS[sym];
      resolved = {
        symbol: sym,
        tradingSymbol: meta.tradingSymbol,
        securityId: meta.securityId,
        segment: meta.segment || "NSE_EQ",
        instrumentType: meta.instrumentType || "EQUITY",
        name: meta.name || meta.tradingSymbol,
        ltp: meta.ltp,
      };
    }

    // 3. Fallback to live backend API search
    if (!resolved) {
      try {
        const res = await fetch(
          `/api/v1/instruments/search?query=${encodeURIComponent(sym)}&is_active_only=true`
        );
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            const match =
              data.find(
                (d: any) =>
                  d.symbol?.toUpperCase() === sym ||
                  d.trading_symbol?.toUpperCase() === sym
              ) || data[0];
            resolved = {
              symbol: match.symbol || sym,
              securityId: String(match.security_id || match.securityId),
              tradingSymbol: match.trading_symbol || `${sym}-EQ`,
              segment: match.exchange_segment || "NSE_EQ",
              instrumentType: match.instrument_type || "EQUITY",
              name: match.name || match.trading_symbol || sym,
              ltp: match.ltp ?? 0,
              changePct: match.change_pct ?? 0,
              expiry: match.expiry_date,
              strike: match.strike_price,
              optionType: match.option_type,
            };
          }
        }
      } catch {
        // Offline fallback
      }
    }

    if (!resolved) {
      setAddSymbolError(`Unknown instrument '${sym}'. Please enter a recognized listed symbol.`);
      return;
    }

    handleAddResolved(resolved);
  };

  const handleRemoveSymbol = (symbol: string) => {
    if (!activeWatchlist) return;
    removeSymbolFromWatchlist(activeWatchlist.id, symbol);
    refreshWatchlists();
  };

  const handleMove = (symbol: string, direction: "up" | "down") => {
    if (!activeWatchlist) return;
    moveItem(activeWatchlist.id, symbol, direction);
    refreshWatchlists();
  };

  const toggleColumn = (colId: WatchlistColumn) => {
    if (!activeWatchlist || colId === "symbol") return;
    const currentCols = activeWatchlist.columns;
    const nextCols = currentCols.includes(colId)
      ? currentCols.filter((c) => c !== colId)
      : [...currentCols, colId];

    updateWatchlist(activeWatchlist.id, { columns: nextCols });
    refreshWatchlists();
  };

  if (!activeWatchlist) {
    return <div style={{ padding: "var(--spacing-3)" }}>No watchlists found.</div>;
  }

  const activeColumns = ALL_COLUMNS.filter((col) =>
    activeWatchlist.columns.includes(col.id)
  );

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
      {/* 1. Watchlist Tabs Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--spacing-1)",
          padding: "var(--spacing-1) var(--spacing-2)",
          backgroundColor: "var(--bg-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
          overflowX: "auto",
        }}
      >
        {watchlists.map((wl) => {
          const isActive = wl.id === activeWatchlist.id;
          return (
            <button
              key={wl.id}
              onClick={() => setActiveWatchlistId(wl.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--spacing-2)",
                padding: "var(--spacing-1) var(--spacing-3)",
                borderRadius: "var(--radius-sm)",
                border: "none",
                backgroundColor: isActive ? "var(--bg-surface)" : "transparent",
                color: isActive ? "var(--color-brand)" : "var(--text-muted)",
                fontWeight: isActive ? 600 : 500,
                fontSize: "var(--font-size-xs)",
                cursor: "pointer",
                whiteSpace: "nowrap",
                borderBottom: isActive ? "2px solid var(--color-brand)" : "2px solid transparent",
              }}
            >
              <span>{wl.name}</span>
              <span style={{ fontSize: "10px", opacity: 0.7 }}>({wl.items.length})</span>
            </button>
          );
        })}

        <button
          onClick={() => setIsCreatingNew((prev) => !prev)}
          style={{
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px dashed var(--border-subtle)",
            backgroundColor: "transparent",
            color: "var(--text-muted)",
            fontSize: "var(--font-size-xs)",
            cursor: "pointer",
          }}
          title="Create New Watchlist"
        >
          + New
        </button>
      </div>

      {/* 2. New Watchlist Inline Form */}
      {isCreatingNew && (
        <form
          onSubmit={handleCreateWatchlist}
          style={{
            display: "flex",
            gap: "var(--spacing-2)",
            padding: "var(--spacing-2)",
            backgroundColor: "var(--bg-surface)",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <input
            type="text"
            placeholder="Watchlist Name (e.g. IT Sector)"
            value={newWatchlistName}
            onChange={(e) => setNewWatchlistName(e.target.value)}
            autoFocus
            style={{
              flex: 1,
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--bg-input)",
              color: "var(--text-primary)",
              fontSize: "var(--font-size-xs)",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "4px 10px",
              backgroundColor: "var(--color-brand)",
              color: "#fff",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Create
          </button>
          <button
            type="button"
            onClick={() => setIsCreatingNew(false)}
            style={{
              padding: "4px 8px",
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
        </form>
      )}

      {/* 3. Watchlist Toolbar: Add Symbol, Column Picker, Delete */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "var(--spacing-2)",
          padding: "var(--spacing-2)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        {/* Zerodha-Style Symbol Search & Autocomplete Dropdown */}
        <form
          onSubmit={(e) => handleAddSymbol(e)}
          style={{ display: "flex", gap: "var(--spacing-1)", flex: 1, alignItems: "center" }}
        >
          <SymbolSearchDropdown
            value={symbolSearchQuery}
            onChange={setSymbolSearchQuery}
            onSelectInstrument={handleAddResolved}
            onSubmitText={(txt) => handleAddSymbol(undefined, txt)}
            existingSecurityIds={new Set(activeWatchlist.items.map((i) => i.securityId))}
            existingSymbols={new Set(activeWatchlist.items.map((i) => i.symbol))}
            placeholder="Add symbol (e.g. NIFTY, TCS, RELIANCE)..."
          />
          <button
            type="submit"
            style={{
              padding: "4px 12px",
              backgroundColor: "var(--bg-elevated)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
              height: "28px",
              whiteSpace: "nowrap",
            }}
          >
            Add
          </button>
        </form>

        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            onClick={() => setIsConfiguringColumns((prev) => !prev)}
            style={{
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: isConfiguringColumns ? "var(--bg-elevated)" : "transparent",
              color: "var(--text-muted)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
            title="Configure Columns"
          >
            ⚙ Columns
          </button>

          {!activeWatchlist.isDefault && (
            <button
              type="button"
              onClick={() => handleDeleteWatchlist(activeWatchlist.id)}
              style={{
                padding: "4px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "transparent",
                color: "var(--color-down)",
                fontSize: "var(--font-size-xs)",
                cursor: "pointer",
              }}
              title="Delete Watchlist"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {/* 3.1 Error message if symbol unresolved */}
      {addSymbolError && (
        <div
          role="alert"
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "rgba(239, 68, 68, 0.15)",
            color: "var(--color-down, #ef4444)",
            fontSize: "var(--font-size-xs)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{addSymbolError}</span>
          <button
            type="button"
            onClick={() => setAddSymbolError(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontWeight: "bold",
              padding: "0 4px",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* 3.2 Action Notice Toast Banner */}
      {actionNotice && (
        <div
          role="status"
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "rgba(88, 166, 255, 0.15)",
            color: "var(--color-brand, #58a6ff)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "var(--font-size-xs)",
          }}
        >
          <span>✓ {actionNotice}</span>
          <button
            type="button"
            onClick={() => setActionNotice(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontWeight: "bold",
              padding: "0 4px",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* 4. Column Configuration Panel */}
      {isConfiguringColumns && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--spacing-2)",
            padding: "var(--spacing-2)",
            backgroundColor: "var(--bg-elevated)",
            borderBottom: "1px solid var(--border-subtle)",
            fontSize: "var(--font-size-xs)",
          }}
        >
          {ALL_COLUMNS.map((col) => {
            const isChecked = activeWatchlist.columns.includes(col.id);
            const isSymbol = col.id === "symbol";
            return (
              <label
                key={col.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  cursor: isSymbol ? "default" : "pointer",
                  color: isChecked ? "var(--text-primary)" : "var(--text-muted)",
                }}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  disabled={isSymbol}
                  onChange={() => toggleColumn(col.id)}
                />
                {col.label}
              </label>
            );
          })}
        </div>
      )}

      {/* 5. Watchlist Data Table */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {activeWatchlist.items.length === 0 ? (
          <div
            style={{
              padding: "var(--spacing-4)",
              textAlign: "center",
              color: "var(--text-muted)",
            }}
          >
            No symbols in this watchlist. Use the search input above to add stocks or F&O contracts.
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
                  zIndex: 1,
                }}
              >
                <th style={{ padding: "6px 8px", width: "40px", textAlign: "center" }}>#</th>
                {activeColumns.map((col) => (
                  <th
                    key={col.id}
                    style={{
                      padding: "6px 8px",
                      textAlign: col.align || "left",
                      minWidth: `${col.minWidth}px`,
                      fontWeight: 600,
                    }}
                  >
                    {col.label}
                  </th>
                ))}
                <th style={{ padding: "6px 8px", width: "190px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activeWatchlist.items.map((item, idx) => {
                const changePct = item.changePct ?? 0;
                const isUp = changePct >= 0;
                const ltp = item.ltp ?? 0;
                const isIndex = item.instrumentType === "INDEX" || item.segment === "IDX_I";
                const isRowHovered = hoveredSymbol === item.symbol;
                const isRowSelected = selectedSymbol === item.symbol;

                return (
                  <tr
                    key={item.symbol}
                    onMouseEnter={() => setHoveredSymbol(item.symbol)}
                    onMouseLeave={() => {
                      if (hoveredSymbol === item.symbol) setHoveredSymbol(null);
                    }}
                    onClick={() => setSelectedSymbol(item.symbol)}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      backgroundColor: isRowSelected
                        ? "var(--color-primary-bg, rgba(88, 166, 255, 0.08))"
                        : isRowHovered
                        ? "var(--bg-elevated, rgba(255, 255, 255, 0.03))"
                        : "transparent",
                      transition: "background-color 0.15s ease",
                      cursor: "pointer",
                    }}
                  >
                    <td style={{ padding: "6px 8px", textAlign: "center", color: "var(--text-muted)" }}>
                      {idx + 1}
                    </td>

                    {activeColumns.map((col) => {
                      if (col.id === "symbol") {
                        return (
                          <td key={col.id} style={{ padding: "6px 8px", fontWeight: 600 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <span
                                style={{
                                  cursor: "grab",
                                  color:
                                    isRowHovered || isRowSelected
                                      ? "var(--color-brand, #58a6ff)"
                                      : "var(--text-muted, #484f58)",
                                  fontSize: "13px",
                                  letterSpacing: "-1px",
                                  lineHeight: 1,
                                  userSelect: "none",
                                }}
                                title="Drag to reorder"
                              >
                                ⠿
                              </span>
                              <span>{item.symbol}</span>
                              {item.segment === "NSE_FNO" && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "1px 4px",
                                    borderRadius: "var(--radius-sm)",
                                    backgroundColor: "var(--bg-elevated)",
                                    color: "var(--color-brand)",
                                    fontWeight: 700,
                                  }}
                                >
                                  F&O
                                </span>
                              )}
                              {(item.segment === "IDX_I" || item.instrumentType === "INDEX") && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "1px 4px",
                                    borderRadius: "var(--radius-sm)",
                                    backgroundColor: "rgba(163, 113, 247, 0.15)",
                                    color: "#a371f7",
                                    border: "1px solid rgba(163, 113, 247, 0.3)",
                                    fontWeight: 700,
                                  }}
                                >
                                  INDEX
                                </span>
                              )}
                              {item.instrumentType === "ETF" && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "1px 4px",
                                    borderRadius: "var(--radius-sm)",
                                    backgroundColor: "rgba(46, 160, 67, 0.15)",
                                    color: "#3fb950",
                                    border: "1px solid rgba(46, 160, 67, 0.3)",
                                    fontWeight: 700,
                                  }}
                                >
                                  ETF
                                </span>
                              )}
                              {(item.segment?.startsWith("MCX") || item.instrumentType === "FUTCOM") && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "1px 4px",
                                    borderRadius: "var(--radius-sm)",
                                    backgroundColor: "rgba(240, 136, 62, 0.15)",
                                    color: "#f0883e",
                                    border: "1px solid rgba(240, 136, 62, 0.3)",
                                    fontWeight: 700,
                                  }}
                                >
                                  MCX
                                </span>
                              )}
                              {(item.segment?.includes("CURRENCY") || item.instrumentType === "FUTCUR") && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "1px 4px",
                                    borderRadius: "var(--radius-sm)",
                                    backgroundColor: "rgba(56, 189, 248, 0.15)",
                                    color: "#38bdf8",
                                    border: "1px solid rgba(56, 189, 248, 0.3)",
                                    fontWeight: 700,
                                  }}
                                >
                                  FOREX
                                </span>
                              )}
                            </div>
                            {item.name && item.name !== item.symbol && (
                              <div
                                style={{
                                  fontSize: "10px",
                                  color: "var(--text-muted)",
                                  fontWeight: 400,
                                  marginTop: "1px",
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  maxWidth: "180px",
                                }}
                              >
                                {item.name}
                              </div>
                            )}
                          </td>
                        );
                      }

                      if (col.id === "ltp") {
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              fontWeight: 600,
                            }}
                          >
                            ₹{ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </td>
                        );
                      }

                      if (col.id === "changePct") {
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                            }}
                          >
                            <span
                              style={{
                                padding: "2px 6px",
                                borderRadius: "var(--radius-sm)",
                                backgroundColor: isUp ? "var(--color-up-bg)" : "var(--color-down-bg)",
                                color: isUp ? "var(--color-up)" : "var(--color-down)",
                                fontWeight: 600,
                              }}
                            >
                              {isUp ? "+" : ""}
                              {changePct.toFixed(2)}%
                            </span>
                          </td>
                        );
                      }

                      if (col.id === "changeAbs") {
                        const changeAbs = item.changeAbs ?? 0;
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: isUp ? "var(--color-up)" : "var(--color-down)",
                            }}
                          >
                            {isUp ? "+" : ""}
                            {changeAbs.toFixed(2)}
                          </td>
                        );
                      }

                      if (col.id === "volume") {
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {(item.volume ?? 0).toLocaleString("en-IN")}
                          </td>
                        );
                      }

                      if (col.id === "oi") {
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {item.oi !== undefined ? item.oi.toLocaleString("en-IN") : "—"}
                          </td>
                        );
                      }

                      if (col.id === "oiChangePct") {
                        const oiChg = item.oiChangePct;
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                            }}
                          >
                            {oiChg !== undefined ? (
                              <span style={{ color: oiChg >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                                {oiChg >= 0 ? "+" : ""}
                                {oiChg.toFixed(2)}%
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                        );
                      }

                      if (col.id === "highLow") {
                        const high = item.high !== undefined ? `₹${item.high.toFixed(1)}` : "—";
                        const low = item.low !== undefined ? `₹${item.low.toFixed(1)}` : "—";
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {high} / {low}
                          </td>
                        );
                      }

                      if (col.id === "bidAsk") {
                        const bid = item.bid !== undefined ? `₹${item.bid.toFixed(1)}` : "—";
                        const ask = item.ask !== undefined ? `₹${item.ask.toFixed(1)}` : "—";
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {bid} / {ask}
                          </td>
                        );
                      }

                      return <td key={col.id}>—</td>;
                    })}

                    <td style={{ padding: "4px 8px", textAlign: "right" }}>
                      {isRowHovered || isRowSelected ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-end",
                            gap: "4px",
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          {/* Buy & Sell Buttons: Strictly omitted for INDICES */}
                          {!isIndex && (
                            <>
                              <button
                                type="button"
                                aria-label={`Buy ${item.symbol}`}
                                onClick={() => setActionNotice(`BUY order prepared for ${item.symbol}`)}
                                style={{
                                  width: "26px",
                                  height: "24px",
                                  borderRadius: "3px",
                                  backgroundColor: "#1976d2",
                                  color: "#fff",
                                  border: "none",
                                  fontWeight: 700,
                                  fontSize: "11px",
                                  cursor: "pointer",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  lineHeight: 1,
                                }}
                                title={`Buy ${item.symbol}`}
                              >
                                B
                              </button>
                              <button
                                type="button"
                                aria-label={`Sell ${item.symbol}`}
                                onClick={() => setActionNotice(`SELL order prepared for ${item.symbol}`)}
                                style={{
                                  width: "26px",
                                  height: "24px",
                                  borderRadius: "3px",
                                  backgroundColor: "#ff5722",
                                  color: "#fff",
                                  border: "none",
                                  fontWeight: 700,
                                  fontSize: "11px",
                                  cursor: "pointer",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  lineHeight: 1,
                                }}
                                title={`Sell ${item.symbol}`}
                              >
                                S
                              </button>
                            </>
                          )}

                          {/* Market Depth Button */}
                          <button
                            type="button"
                            aria-label="Market Depth"
                            onClick={() => setDepthItem(item)}
                            style={{
                              width: "26px",
                              height: "24px",
                              borderRadius: "3px",
                              backgroundColor: "var(--bg-elevated, #21262d)",
                              border: "1px solid var(--border-subtle, #30363d)",
                              color: "var(--text-primary, #c9d1d9)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "12px",
                            }}
                            title="Market Depth"
                          >
                            ≡
                          </button>

                          {/* Open Chart Button */}
                          <button
                            type="button"
                            aria-label="Chart"
                            onClick={() => setActionNotice(`Chart switched to ${item.symbol}`)}
                            style={{
                              width: "26px",
                              height: "24px",
                              borderRadius: "3px",
                              backgroundColor: "var(--bg-elevated, #21262d)",
                              border: "1px solid var(--border-subtle, #30363d)",
                              color: "var(--text-primary, #c9d1d9)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "11px",
                            }}
                            title="Chart"
                          >
                            📈
                          </button>

                          {/* Delete Symbol Button */}
                          <button
                            type="button"
                            aria-label="Remove Symbol"
                            onClick={() => handleRemoveSymbol(item.symbol)}
                            style={{
                              width: "26px",
                              height: "24px",
                              borderRadius: "3px",
                              backgroundColor: "var(--bg-elevated, #21262d)",
                              border: "1px solid var(--border-subtle, #30363d)",
                              color: "var(--color-down, #f85149)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "12px",
                            }}
                            title="Remove Symbol"
                          >
                            🗑️
                          </button>

                          {/* More Options Button */}
                          <div style={{ position: "relative" }}>
                            <button
                              type="button"
                              aria-label="More options"
                              onClick={() =>
                                setMoreMenuSymbol(moreMenuSymbol === item.symbol ? null : item.symbol)
                              }
                              style={{
                                width: "26px",
                                height: "24px",
                                borderRadius: "3px",
                                backgroundColor: "var(--bg-elevated, #21262d)",
                                border: "1px solid var(--border-subtle, #30363d)",
                                color: "var(--text-primary, #c9d1d9)",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: "11px",
                                letterSpacing: "1px",
                              }}
                              title="More options"
                            >
                              •••
                            </button>

                            {moreMenuSymbol === item.symbol && (
                              <div
                                style={{
                                  position: "absolute",
                                  top: "100%",
                                  right: 0,
                                  marginTop: "4px",
                                  width: "140px",
                                  backgroundColor: "var(--bg-surface, #161b22)",
                                  border: "1px solid var(--border-default, #30363d)",
                                  borderRadius: "6px",
                                  boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
                                  zIndex: 100,
                                  padding: "4px 0",
                                  textAlign: "left",
                                }}
                              >
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActionNotice(`Alert created for ${item.symbol}`);
                                    setMoreMenuSymbol(null);
                                  }}
                                  style={{
                                    display: "block",
                                    width: "100%",
                                    textAlign: "left",
                                    padding: "6px 12px",
                                    background: "none",
                                    border: "none",
                                    color: "var(--text-primary, #c9d1d9)",
                                    fontSize: "11px",
                                    cursor: "pointer",
                                  }}
                                >
                                  🔔 Create Alert
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActionNotice(`GTT Order created for ${item.symbol}`);
                                    setMoreMenuSymbol(null);
                                  }}
                                  style={{
                                    display: "block",
                                    width: "100%",
                                    textAlign: "left",
                                    padding: "6px 12px",
                                    background: "none",
                                    border: "none",
                                    color: "var(--text-primary, #c9d1d9)",
                                    fontSize: "11px",
                                    cursor: "pointer",
                                  }}
                                >
                                  🎯 Create GTT
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActionNotice(`Technicals opened for ${item.symbol}`);
                                    setMoreMenuSymbol(null);
                                  }}
                                  style={{
                                    display: "block",
                                    width: "100%",
                                    textAlign: "left",
                                    padding: "6px 12px",
                                    background: "none",
                                    border: "none",
                                    color: "var(--text-primary, #c9d1d9)",
                                    fontSize: "11px",
                                    cursor: "pointer",
                                  }}
                                >
                                  📊 Technicals
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "2px" }}>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMove(item.symbol, "up");
                            }}
                            disabled={idx === 0}
                            style={{
                              padding: "2px 4px",
                              backgroundColor: "transparent",
                              border: "none",
                              color: idx === 0 ? "transparent" : "var(--text-muted)",
                              cursor: idx === 0 ? "default" : "pointer",
                              fontSize: "10px",
                            }}
                            title="Move Up"
                          >
                            ▲
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMove(item.symbol, "down");
                            }}
                            disabled={idx === activeWatchlist.items.length - 1}
                            style={{
                              padding: "2px 4px",
                              backgroundColor: "transparent",
                              border: "none",
                              color:
                                idx === activeWatchlist.items.length - 1
                                  ? "transparent"
                                  : "var(--text-muted)",
                              cursor: idx === activeWatchlist.items.length - 1 ? "default" : "pointer",
                              fontSize: "10px",
                            }}
                            title="Move Down"
                          >
                            ▼
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRemoveSymbol(item.symbol);
                            }}
                            style={{
                              padding: "2px 4px",
                              backgroundColor: "transparent",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              fontSize: "10px",
                            }}
                            title="Remove Symbol"
                          >
                            ✕
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* 6. Market Depth Modal */}
      {depthItem && depthBook && (
        <div
          role="dialog"
          aria-label="Market Depth Modal"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 3000,
          }}
          onClick={() => setDepthItem(null)}
        >
          <div
            style={{
              width: "520px",
              maxWidth: "95vw",
              backgroundColor: "var(--bg-surface, #161b22)",
              borderRadius: "8px",
              border: "1px solid var(--border-default, #30363d)",
              padding: "16px",
              boxShadow: "0 12px 36px rgba(0, 0, 0, 0.8)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontWeight: 700, color: "#fff", fontSize: "15px" }}>
                  {depthItem.tradingSymbol || depthItem.symbol}
                </span>
                <span
                  style={{
                    fontSize: "10px",
                    padding: "1px 6px",
                    borderRadius: "3px",
                    backgroundColor: getSegmentBadge(depthItem).bg,
                    color: getSegmentBadge(depthItem).color,
                    border: `1px solid ${getSegmentBadge(depthItem).border}`,
                    fontWeight: 700,
                  }}
                >
                  {getSegmentBadge(depthItem).label}
                </span>
                <span style={{ fontSize: "12px", color: "var(--text-muted, #8b949e)" }}>
                  {depthItem.name}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                {(depthItem.ltp ?? 0) > 0 && (
                  <span style={{ fontFamily: "var(--font-family-mono)", fontWeight: 700, fontSize: "14px", color: "#fff" }}>
                    ₹{(depthItem.ltp ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                )}
                <button
                  type="button"
                  aria-label="Close modal"
                  onClick={() => setDepthItem(null)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted, #8b949e)",
                    cursor: "pointer",
                    fontSize: "16px",
                    padding: "2px 6px",
                  }}
                  title="Close modal"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Capability & Spread Info */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "10px",
                color: "var(--text-muted, #8b949e)",
                fontSize: "11px",
                backgroundColor: "var(--bg-elevated, #0d1117)",
                padding: "6px 10px",
                borderRadius: "4px",
                border: "1px solid var(--border-subtle, #30363d)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span>
                  Capability:{" "}
                  <strong style={{ color: "#58a6ff" }}>
                    {depthCapability?.actualLevel === "LEVEL_20"
                      ? "20-Level Full Depth (NSE)"
                      : "5-Level Depth Feed (MCX/Forex/BSE)"}
                  </strong>
                </span>
                <div style={{ display: "flex", gap: "4px" }}>
                  <button
                    type="button"
                    onClick={() => setDepthLevelType("LEVEL_5")}
                    style={{
                      padding: "1px 6px",
                      fontSize: "10px",
                      borderRadius: "3px",
                      border: "1px solid var(--border-subtle, #30363d)",
                      backgroundColor: depthLevelType === "LEVEL_5" ? "var(--color-brand, #58a6ff)" : "transparent",
                      color: depthLevelType === "LEVEL_5" ? "#fff" : "var(--text-muted, #8b949e)",
                      cursor: "pointer",
                    }}
                  >
                    5
                  </button>
                  <button
                    type="button"
                    onClick={() => setDepthLevelType("LEVEL_20")}
                    style={{
                      padding: "1px 6px",
                      fontSize: "10px",
                      borderRadius: "3px",
                      border: "1px solid var(--border-subtle, #30363d)",
                      backgroundColor: depthLevelType === "LEVEL_20" ? "var(--color-brand, #58a6ff)" : "transparent",
                      color: depthLevelType === "LEVEL_20" ? "#fff" : "var(--text-muted, #8b949e)",
                      cursor: "pointer",
                    }}
                  >
                    20
                  </button>
                </div>
              </div>
              <span>
                Spread: ₹{depthBook.spread.toFixed(2)} ({depthBook.spreadPct}%)
              </span>
            </div>

            {/* Bids & Asks Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              {/* Bids */}
              <div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "40px 1fr 1fr",
                    fontWeight: 600,
                    color: "#3fb950",
                    borderBottom: "1px solid rgba(63, 185, 80, 0.3)",
                    paddingBottom: "4px",
                    marginBottom: "4px",
                    fontSize: "11px",
                  }}
                >
                  <span>Orders</span>
                  <span style={{ textAlign: "right" }}>Qty</span>
                  <span style={{ textAlign: "right" }}>Bid Price</span>
                </div>
                {depthBook.bids.slice(0, depthCapability?.actualLevel === "LEVEL_20" ? 20 : 5).map((bid, i) => (
                  <div
                    key={`bid-${i}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "40px 1fr 1fr",
                      padding: "2px 0",
                      fontFamily: "var(--font-family-mono)",
                      fontSize: "11px",
                    }}
                  >
                    <span style={{ color: "var(--text-muted, #8b949e)" }}>{bid.orders}</span>
                    <span style={{ textAlign: "right", color: "var(--text-primary, #f0f6fc)" }}>
                      {bid.quantity.toLocaleString("en-IN")}
                    </span>
                    <span style={{ textAlign: "right", color: "#3fb950", fontWeight: 600 }}>
                      {bid.price.toFixed(2)}
                    </span>
                  </div>
                ))}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    borderTop: "1px solid var(--border-subtle, #30363d)",
                    marginTop: "6px",
                    paddingTop: "4px",
                    fontWeight: 600,
                    fontSize: "11px",
                  }}
                >
                  <span>Total Bid</span>
                  <span style={{ fontFamily: "var(--font-family-mono)", color: "#3fb950" }}>
                    {depthBook.totalBidQty.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>

              {/* Asks */}
              <div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 40px",
                    fontWeight: 600,
                    color: "#f85149",
                    borderBottom: "1px solid rgba(248, 81, 73, 0.3)",
                    paddingBottom: "4px",
                    marginBottom: "4px",
                    fontSize: "11px",
                  }}
                >
                  <span>Ask Price</span>
                  <span style={{ textAlign: "right" }}>Qty</span>
                  <span style={{ textAlign: "right" }}>Orders</span>
                </div>
                {depthBook.asks.slice(0, depthCapability?.actualLevel === "LEVEL_20" ? 20 : 5).map((ask, i) => (
                  <div
                    key={`ask-${i}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 40px",
                      padding: "2px 0",
                      fontFamily: "var(--font-family-mono)",
                      fontSize: "11px",
                    }}
                  >
                    <span style={{ color: "#f85149", fontWeight: 600 }}>{ask.price.toFixed(2)}</span>
                    <span style={{ textAlign: "right", color: "var(--text-primary, #f0f6fc)" }}>
                      {ask.quantity.toLocaleString("en-IN")}
                    </span>
                    <span style={{ textAlign: "right", color: "var(--text-muted, #8b949e)" }}>{ask.orders}</span>
                  </div>
                ))}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    borderTop: "1px solid var(--border-subtle, #30363d)",
                    marginTop: "6px",
                    paddingTop: "4px",
                    fontWeight: 600,
                    fontSize: "11px",
                  }}
                >
                  <span>Total Ask</span>
                  <span style={{ fontFamily: "var(--font-family-mono)", color: "#f85149" }}>
                    {depthBook.totalAskQty.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const watchlistDefinition: WidgetDefinition<WatchlistSettings> = {
  id: "watchlist",
  title: "Market Watchlist",
  description: "Multiple manual and F&O watchlists with configurable columns and stable ordering.",
  category: "watchlist",
  icon: "📋",
  defaultWidth: 420,
  defaultHeight: 480,
  schema: {
    fields: [
      {
        name: "defaultWatchlistId",
        label: "Default Watchlist",
        type: "select",
        default: "wl-nifty50",
        options: [
          { label: "NIFTY 50", value: "wl-nifty50" },
          { label: "BANK NIFTY F&O", value: "wl-banknifty-fno" },
          { label: "Breakout Stocks", value: "wl-breakout" },
        ],
      },
      {
        name: "refreshIntervalSec",
        label: "Refresh Interval (s)",
        type: "number",
        default: 1,
        min: 1,
        max: 60,
      },
    ],
  },
  component: WatchlistWidget,
};
