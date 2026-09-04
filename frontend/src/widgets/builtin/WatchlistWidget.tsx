import React, { useState, useEffect, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  Watchlist,
  WatchlistColumn,
  ALL_COLUMNS,
} from "../../watchlist/types";
import {
  loadWatchlists,
  createWatchlist,
  deleteWatchlist,
  addSymbolToWatchlist,
  removeSymbolFromWatchlist,
  moveItem,
  updateWatchlist,
  KNOWN_EQUITY_INSTRUMENTS,
} from "../../watchlist/storage";

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
  const [searchSegment, setSearchSegment] = useState<"NSE_EQ" | "NSE_FNO">("NSE_EQ");
  const [addSymbolError, setAddSymbolError] = useState<string | null>(null);

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

  const handleAddSymbol = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbolSearchQuery.trim() || !activeWatchlist) return;

    const sym = symbolSearchQuery.trim().toUpperCase();
    setAddSymbolError(null);

    let resolved: { securityId: string; tradingSymbol: string; ltp?: number } | null =
      KNOWN_EQUITY_INSTRUMENTS[sym] || null;

    if (!resolved) {
      try {
        const res = await fetch(
          `/api/v1/instruments/search?query=${encodeURIComponent(sym)}&segment=${searchSegment}`
        );
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            const match = data.find((d: any) => d.symbol === sym) || data[0];
            resolved = {
              securityId: String(match.security_id || match.securityId),
              tradingSymbol:
                match.trading_symbol ||
                match.tradingSymbol ||
                `${sym}-${searchSegment === "NSE_EQ" ? "EQ" : "FUT"}`,
              ltp: match.ltp,
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

    addSymbolToWatchlist(activeWatchlist.id, {
      symbol: sym,
      segment: searchSegment,
      securityId: resolved.securityId,
      tradingSymbol: resolved.tradingSymbol,
      ltp: resolved.ltp ?? 0,
      changePct: 0,
      changeAbs: 0,
      volume: 0,
    });

    refreshWatchlists();
    setSymbolSearchQuery("");
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
        {/* Add Symbol Input */}
        <form onSubmit={handleAddSymbol} style={{ display: "flex", gap: "var(--spacing-1)", flex: 1 }}>
          <select
            value={searchSegment}
            onChange={(e) => setSearchSegment(e.target.value as "NSE_EQ" | "NSE_FNO")}
            style={{
              padding: "4px 6px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--bg-input)",
              color: "var(--text-primary)",
              fontSize: "var(--font-size-xs)",
            }}
          >
            <option value="NSE_EQ">EQ</option>
            <option value="NSE_FNO">F&O</option>
          </select>
          <input
            type="text"
            placeholder="Add symbol (e.g. INFY, NIFTY26SEPFUT)..."
            value={symbolSearchQuery}
            onChange={(e) => setSymbolSearchQuery(e.target.value)}
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
              backgroundColor: "var(--bg-elevated)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
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
                <th style={{ padding: "6px 8px", width: "70px", textAlign: "center" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activeWatchlist.items.map((item, idx) => {
                const changePct = item.changePct ?? 0;
                const isUp = changePct >= 0;
                const ltp = item.ltp ?? 0;

                return (
                  <tr
                    key={item.symbol}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      backgroundColor: "transparent",
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
                            </div>
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

                    <td style={{ padding: "6px 8px", textAlign: "center" }}>
                      <div style={{ display: "flex", justifyContent: "center", gap: "2px" }}>
                        <button
                          type="button"
                          onClick={() => handleMove(item.symbol, "up")}
                          disabled={idx === 0}
                          style={{
                            padding: "2px 4px",
                            backgroundColor: "transparent",
                            border: "none",
                            color: idx === 0 ? "var(--border-subtle)" : "var(--text-muted)",
                            cursor: idx === 0 ? "default" : "pointer",
                            fontSize: "10px",
                          }}
                          title="Move Up"
                        >
                          ▲
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMove(item.symbol, "down")}
                          disabled={idx === activeWatchlist.items.length - 1}
                          style={{
                            padding: "2px 4px",
                            backgroundColor: "transparent",
                            border: "none",
                            color:
                              idx === activeWatchlist.items.length - 1
                                ? "var(--border-subtle)"
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
                          onClick={() => handleRemoveSymbol(item.symbol)}
                          style={{
                            padding: "2px 4px",
                            backgroundColor: "transparent",
                            border: "none",
                            color: "var(--color-down)",
                            cursor: "pointer",
                            fontSize: "10px",
                          }}
                          title="Remove Symbol"
                        >
                          ✕
                        </button>
                      </div>
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
