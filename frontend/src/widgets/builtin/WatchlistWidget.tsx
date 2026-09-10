import React, { useState, useEffect, useMemo } from "react";
import { apiClient } from "../../api/client";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  Watchlist,
  WatchlistColumn,
  ALL_COLUMNS,
  WatchlistItem,
} from "../../watchlist/types";
import {
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
  addStandardWatchlistToUser,
} from "../../watchlist/storage";
import { SymbolSearchDropdown } from "./SymbolSearchDropdown";
import { MarketDepthCard } from "../../depth/MarketDepthCard";
import { DiscoverWatchlistsModal } from "./DiscoverWatchlistsModal";
import { defaultWebSocketClient } from "../../websocket/client";
import { TickData } from "../../websocket/types";

export type WatchlistSortOption =
  | "default"
  | "pct_desc"
  | "pct_asc"
  | "name_asc"
  | "name_desc"
  | "price_desc"
  | "price_asc";

export const NON_SORTABLE_COLUMNS: readonly WatchlistColumn[] = [
  "fiftyTwoWeek", // 52W H / L
  "highLow",      // High / Low
  "bidAsk",       // Bid / Ask
];

export const getFiftyTwoWeekHigh = (item: WatchlistItem): number => {
  return item.fiftyTwoWeekHigh ?? Number.NaN;
};

export const getFiftyTwoWeekLow = (item: WatchlistItem): number => {
  return item.fiftyTwoWeekLow ?? Number.NaN;
};

const FEED_SEGMENTS: Record<string, string> = {
  IDX_I: "0",
  NSE_EQ: "1",
  NSE_FNO: "2",
  NSE_CURRENCY: "3",
  BSE_EQ: "4",
  MCX_COMM: "5",
  BSE_CURRENCY: "7",
  BSE_FNO: "8",
};

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
  const [isDiscoverModalOpen, setIsDiscoverModalOpen] = useState(false);
  const [newWatchlistName, setNewWatchlistName] = useState("");
  const [isConfiguringColumns, setIsConfiguringColumns] = useState(false);
  const [symbolSearchQuery, setSymbolSearchQuery] = useState("");
  const [addSymbolError, setAddSymbolError] = useState<string | null>(null);

  // Zerodha-style row hover, selection, depth modal, and more actions
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [depthItem, setDepthItem] = useState<WatchlistItem | null>(null);
  const [moreMenuSymbol, setMoreMenuSymbol] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Auto-dismiss notice toast
  useEffect(() => {
    if (actionNotice) {
      const timer = setTimeout(() => setActionNotice(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [actionNotice]);

  // Global Ctrl + Shift + K to open Discover modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && (e.key === "K" || e.key === "k")) {
        e.preventDefault();
        setIsDiscoverModalOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Market Depth capability
  const depthCapability = useMemo(() => {
    if (!depthItem) return null;
    return resolveSegmentDepthCapability(depthItem.segment, "LEVEL_20");
  }, [depthItem]);

  // Reload watchlists from storage
  const refreshWatchlists = () => {
    const updated = loadWatchlists();
    setWatchlists(updated);
  };

  const activeWatchlist = useMemo(() => {
    return watchlists.find((w) => w.id === activeWatchlistId) || watchlists[0];
  }, [watchlists, activeWatchlistId]);

  const marketStateLabel = useMemo(() => {
    const states = activeWatchlist?.items.map((item) => item.marketDataState) ?? [];
    if (states.includes("LIVE")) return "LIVE";
    if (states.includes("MARKET_CLOSED")) return "MARKET CLOSED";
    if (states.includes("STALE")) return "STALE";
    if (states.includes("ERROR")) return "ERROR";
    return "UNAVAILABLE";
  }, [activeWatchlist]);

  // Flash state map for dynamic tick animation
  const [priceFlashes, setPriceFlashes] = useState<Record<string, "up" | "down">>({});

  // Real-time live feed subscription and quote tick processing
  useEffect(() => {
    if (activeWatchlist && activeWatchlist.items.length > 0) {
      const symbols = activeWatchlist.items.map((i) => i.symbol);
      const instruments = activeWatchlist.items
        .filter((item) => item.securityId && FEED_SEGMENTS[item.segment])
        .map((item) => ({
          segment: FEED_SEGMENTS[item.segment],
          securityId: item.securityId,
          symbol: item.symbol,
        }));
      defaultWebSocketClient.connect();
      defaultWebSocketClient.subscribeChannels(["quotes"], symbols, instruments);
    }

    const unsub = defaultWebSocketClient.onChannel("quotes", (data: unknown) => {
      const tick = data as TickData;
      if (!tick || !tick.symbol) return;

      const sym = tick.symbol.toUpperCase();

      setWatchlists((prevWatchlists) => {
        let changed = false;
        const next = prevWatchlists.map((wl) => {
          const itemIdx = wl.items.findIndex((i) => {
            const iSym = i.symbol.toUpperCase();
            return (
              iSym === sym ||
              (sym === "NIFTY" && (iSym === "NIFTY 50" || iSym === "NIFTY50")) ||
              (sym === "BANKNIFTY" && (iSym === "NIFTY BANK" || iSym === "BANK NIFTY")) ||
              ((sym === "NIFTY 50" || sym === "NIFTY50") && iSym === "NIFTY") ||
              ((sym === "NIFTY BANK" || sym === "BANK NIFTY") && iSym === "BANKNIFTY")
            );
          });
          if (itemIdx === -1) return wl;

          changed = true;
          const updatedItems = [...wl.items];
          const oldItem = updatedItems[itemIdx];
          const oldLtp = oldItem.ltp;
          const newLtp = tick.ltp;

          if (oldLtp !== undefined && newLtp !== oldLtp) {
            const flashDir = newLtp >= oldLtp ? "up" : "down";
            setPriceFlashes((prev) => ({ ...prev, [oldItem.symbol]: flashDir }));
            setTimeout(() => {
              setPriceFlashes((prev) => {
                const nextFlash = { ...prev };
                delete nextFlash[oldItem.symbol];
                return nextFlash;
              });
            }, 700);
          }

          updatedItems[itemIdx] = {
            ...oldItem,
            ltp: newLtp,
            changeAbs: tick.change ?? oldItem.changeAbs,
            changePct: tick.changePct ?? oldItem.changePct,
            volume: tick.volume ?? oldItem.volume,
            ltt: tick.sourceTimestamp !== undefined
              ? String(tick.sourceTimestamp)
              : oldItem.ltt,
            isStale: tick.isStale,
            marketDataState: tick.marketState,
            marketDataSource: tick.source,
            marketDataReceivedAt: tick.timestamp / 1000,
            marketDataError: undefined,
          };
          return { ...wl, items: updatedItems };
        });

        return changed ? next : prevWatchlists;
      });
    });

    const unsubState = defaultWebSocketClient.onStateChange((state) => {
      if (state !== "ERROR") return;
      setWatchlists((previous) => previous.map((watchlist) => watchlist.id === activeWatchlistId
        ? {
            ...watchlist,
            items: watchlist.items.map((item) => ({
              ...item,
              marketDataState: item.ltp === undefined ? "ERROR" : "STALE",
              marketDataError: "Authoritative Dhan market-data feed is unavailable",
            })),
          }
        : watchlist));
    });

    return () => {
      unsub();
      unsubState();
      if (activeWatchlist) {
        const symbols = activeWatchlist.items.map((item) => item.symbol);
        const instruments = activeWatchlist.items
          .filter((item) => item.securityId && FEED_SEGMENTS[item.segment])
          .map((item) => ({
            segment: FEED_SEGMENTS[item.segment],
            securityId: item.securityId,
            symbol: item.symbol,
          }));
        defaultWebSocketClient.unsubscribeChannels(["quotes"], symbols, instruments);
      }
    };
  }, [activeWatchlistId, activeWatchlist?.items.length]);

  const [sortColumn, setSortColumn] = useState<WatchlistColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc" | null>(null);

  const handleHeaderSort = (colId: WatchlistColumn) => {
    if (NON_SORTABLE_COLUMNS.includes(colId)) return;
    if (sortColumn !== colId) {
      setSortColumn(colId);
      // For text column (symbol): ascending (A-Z) first. For numbers: descending (high to low) first.
      setSortDirection(colId === "symbol" ? "asc" : "desc");
    } else if (sortDirection === (colId === "symbol" ? "asc" : "desc")) {
      setSortDirection(colId === "symbol" ? "desc" : "asc");
    } else {
      setSortColumn(null);
      setSortDirection(null);
    }
  };

  const sortedItems = useMemo(() => {
    if (!activeWatchlist?.items) return [];
    const list = [...activeWatchlist.items];
    if (!sortColumn || !sortDirection) return list;

    return list.sort((a, b) => {
      let comp = 0;
      switch (sortColumn) {
        case "symbol": {
          const nameA = a.name || a.symbol;
          const nameB = b.name || b.symbol;
          comp = nameA.localeCompare(nameB);
          break;
        }
        case "ltp":
          comp = (a.ltp ?? 0) - (b.ltp ?? 0);
          break;
        case "changeAbs":
          comp = (a.changeAbs ?? 0) - (b.changeAbs ?? 0);
          break;
        case "changePct":
          comp = (a.changePct ?? 0) - (b.changePct ?? 0);
          break;
        case "volume":
          comp = (a.volume ?? 0) - (b.volume ?? 0);
          break;
        case "fiftyTwoWeekHigh":
          comp = getFiftyTwoWeekHigh(a) - getFiftyTwoWeekHigh(b);
          break;
        case "fiftyTwoWeekLow":
          comp = getFiftyTwoWeekLow(a) - getFiftyTwoWeekLow(b);
          break;
        case "oi":
          comp = (a.oi ?? 0) - (b.oi ?? 0);
          break;
        case "oiChangePct":
          comp = (a.oiChangePct ?? 0) - (b.oiChangePct ?? 0);
          break;
        default:
          comp = 0;
      }
      return sortDirection === "asc" ? comp : -comp;
    });
  }, [activeWatchlist, sortColumn, sortDirection]);

  const handleSelectSymbol = (item: WatchlistItem) => {
    setSelectedSymbol(item.symbol);
    try {
      window.dispatchEvent(
        new CustomEvent("shreenexa:select-symbol", {
          detail: { symbol: item.symbol, item },
        })
      );
    } catch {
      // safe fallback
    }
  };

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

  const handleAddStandardWatchlist = (presetId: string) => {
    const added = addStandardWatchlistToUser(presetId);
    refreshWatchlists();
    setActiveWatchlistId(added.id);
    setActionNotice(`Added standard watchlist "${added.name}" (${added.items.length} stocks)`);
    setIsDiscoverModalOpen(false);
  };

  const handleCreateCustomWatchlist = (name: string) => {
    const created = createWatchlist(name);
    refreshWatchlists();
    setActiveWatchlistId(created.id);
    setActionNotice(`Created watchlist "${created.name}"`);
    setIsDiscoverModalOpen(false);
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
      fiftyTwoWeekHigh: item.fiftyTwoWeekHigh,
      fiftyTwoWeekLow: item.fiftyTwoWeekLow,
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
        fiftyTwoWeekHigh: meta.fiftyTwoWeekHigh,
        fiftyTwoWeekLow: meta.fiftyTwoWeekLow,
      };
    }

    // 3. Fallback to live backend API search
    if (!resolved) {
      try {
        const token = apiClient.getCsrfToken() || "demo-csrf-token";
        const res = await fetch(
          `/api/v1/instruments/search?query=${encodeURIComponent(sym)}&is_active_only=true`,
          {
            credentials: "include",
            headers: {
              Accept: "application/json",
              Authorization: `Bearer ${token}`,
              "x-csrf-token": token,
            },
          }
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
          onClick={() => setIsDiscoverModalOpen(true)}
          style={{
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px dashed var(--border-subtle)",
            backgroundColor: "transparent",
            color: "var(--text-muted)",
            fontSize: "var(--font-size-xs)",
            cursor: "pointer",
          }}
          title="Create New or Select Standard Watchlist"
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

        <div style={{ display: "flex", gap: "var(--spacing-1)", alignItems: "center" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              fontSize: "11px",
              color: marketStateLabel === "LIVE" ? "var(--color-up, #3fb950)" : "var(--text-muted)",
              backgroundColor: marketStateLabel === "LIVE" ? "rgba(46, 160, 67, 0.15)" : "var(--bg-elevated)",
              padding: "2px 8px",
              borderRadius: "12px",
              border: "1px solid rgba(46, 160, 67, 0.3)",
              fontWeight: 600,
            }}
            title={`Dhan market data: ${marketStateLabel}`}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: marketStateLabel === "LIVE" ? "var(--color-up, #3fb950)" : "var(--text-muted)",
                boxShadow: marketStateLabel === "LIVE" ? "0 0 6px var(--color-up, #3fb950)" : "none",
              }}
            />
            <span>{marketStateLabel}</span>
          </div>

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
                {activeColumns.map((col) => {
                  const isSortable = col.sortable !== false && !NON_SORTABLE_COLUMNS.includes(col.id);
                  const isSorted = isSortable && sortColumn === col.id;
                  const sortArrow = isSorted
                    ? sortDirection === "asc"
                      ? "▲"
                      : "▼"
                    : "↕";

                  return (
                    <th
                      key={col.id}
                      onClick={isSortable ? () => handleHeaderSort(col.id) : undefined}
                      style={{
                        padding: "6px 8px",
                        textAlign: col.align || "left",
                        minWidth: `${col.minWidth}px`,
                        fontWeight: 600,
                        cursor: isSortable ? "pointer" : "default",
                        userSelect: isSortable ? "none" : "auto",
                      }}
                      role="columnheader"
                      aria-sort={
                        isSortable
                          ? isSorted
                            ? sortDirection === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                          : undefined
                      }
                      title={isSortable ? `Click to sort by ${col.label}` : undefined}
                    >
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          justifyContent:
                            col.align === "right"
                              ? "flex-end"
                              : col.align === "center"
                              ? "center"
                              : "flex-start",
                          width: "100%",
                        }}
                      >
                        <span>{col.label}</span>
                        {isSortable && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleHeaderSort(col.id);
                            }}
                            aria-label={`Sort by ${col.label}`}
                            tabIndex={-1}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              background: "none",
                              border: "none",
                              padding: 0,
                              margin: 0,
                              cursor: "pointer",
                              fontSize: "10px",
                              lineHeight: 1,
                              color: isSorted
                                ? "var(--color-brand, #58a6ff)"
                                : "var(--text-muted, #8b949e)",
                              opacity: isSorted ? 1 : 0.5,
                              transition: "opacity 0.15s, color 0.15s",
                            }}
                          >
                            {sortArrow}
                          </button>
                        )}
                      </div>
                    </th>
                  );
                })}
                <th style={{ padding: "6px 8px", width: "190px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((item, idx) => {
                const changePct = item.changePct;
                const isUp = typeof changePct === "number" && changePct >= 0;
                const ltp = item.ltp;
                const isIndex = item.instrumentType === "INDEX" || item.segment === "IDX_I";
                const isRowHovered = hoveredSymbol === item.symbol;
                const isRowSelected = selectedSymbol === item.symbol;
                const showSectorHeader = Boolean(
                  activeWatchlist?.isGroupedBySector &&
                    item.sector &&
                    (idx === 0 || item.sector !== sortedItems[idx - 1].sector)
                );

                return (
                  <React.Fragment key={item.symbol}>
                    {showSectorHeader && (
                      <tr
                        key={`sec-header-${item.sector}`}
                        style={{
                          backgroundColor: "rgba(56, 126, 209, 0.12)",
                          borderTop: "1px solid rgba(56, 126, 209, 0.25)",
                          borderBottom: "1px solid rgba(56, 126, 209, 0.25)",
                        }}
                      >
                        <td
                          colSpan={activeColumns.length + 2}
                          style={{
                            padding: "6px 12px",
                            fontSize: "11px",
                            fontWeight: 700,
                            color: "#64b5f6",
                            letterSpacing: "0.6px",
                            textTransform: "uppercase",
                          }}
                        >
                          📂 {item.sector}
                        </td>
                      </tr>
                    )}
                    <tr
                      key={item.symbol}
                      onMouseEnter={() => setHoveredSymbol(item.symbol)}
                      onMouseLeave={() => {
                        if (hoveredSymbol === item.symbol) setHoveredSymbol(null);
                      }}
                      onClick={() => handleSelectSymbol(item)}
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
                              {item.sector && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    padding: "1px 4px",
                                    borderRadius: "var(--radius-sm)",
                                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                                    color: "var(--text-muted)",
                                    border: "1px solid var(--border-subtle)",
                                  }}
                                  title={`Sector: ${item.sector}`}
                                >
                                  {item.sector}
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
                        const flash = priceFlashes[item.symbol];
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              fontWeight: 600,
                              backgroundColor:
                                flash === "up"
                                  ? "rgba(46, 160, 67, 0.28)"
                                  : flash === "down"
                                  ? "rgba(248, 81, 73, 0.28)"
                                  : "transparent",
                              borderRadius: "var(--radius-sm)",
                              transition: "background-color 0.35s ease",
                            }}
                          >
                            {typeof ltp === "number"
                              ? `₹${ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                              : "N/A"}
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
                              {typeof changePct === "number"
                                ? `${isUp ? "+" : ""}${changePct.toFixed(2)}%`
                                : "N/A"}
                            </span>
                          </td>
                        );
                      }

                      if (col.id === "changeAbs") {
                        const changeAbs = item.changeAbs;
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
                            {typeof changeAbs === "number"
                              ? `${isUp ? "+" : ""}${changeAbs.toFixed(2)}`
                              : "N/A"}
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
                            {typeof item.volume === "number" ? item.volume.toLocaleString("en-IN") : "N/A"}
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

                      if (col.id === "fiftyTwoWeekHigh") {
                        const high52 = getFiftyTwoWeekHigh(item);
                        if (ltp === undefined || !Number.isFinite(high52)) {
                          return <td key={col.id} style={{ textAlign: "right" }}>N/A</td>;
                        }
                        const diffPct = ((ltp - high52) / high52) * 100;
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: "var(--text-primary)",
                            }}
                          >
                            <span>₹{high52.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                            <span
                              style={{
                                fontSize: "10px",
                                color: diffPct >= 0 ? "var(--color-up)" : "var(--color-down)",
                                marginLeft: "4px",
                              }}
                            >
                              ({diffPct >= 0 ? "+" : ""}{diffPct.toFixed(2)}%)
                            </span>
                          </td>
                        );
                      }

                      if (col.id === "fiftyTwoWeekLow") {
                        const low52 = getFiftyTwoWeekLow(item);
                        if (ltp === undefined || !Number.isFinite(low52)) {
                          return <td key={col.id} style={{ textAlign: "right" }}>N/A</td>;
                        }
                        const diffPct = ((ltp - low52) / low52) * 100;
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              color: "var(--text-primary)",
                            }}
                          >
                            <span>₹{low52.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                            <span
                              style={{
                                fontSize: "10px",
                                color: diffPct >= 0 ? "var(--color-up)" : "var(--color-down)",
                                marginLeft: "4px",
                              }}
                            >
                              ({diffPct >= 0 ? "+" : ""}{diffPct.toFixed(2)}%)
                            </span>
                          </td>
                        );
                      }

                      if (col.id === "fiftyTwoWeek") {
                        const high52 = getFiftyTwoWeekHigh(item);
                        const low52 = getFiftyTwoWeekLow(item);
                        if (
                          ltp === undefined ||
                          !Number.isFinite(high52) ||
                          !Number.isFinite(low52)
                        ) {
                          return <td key={col.id} style={{ textAlign: "right" }}>N/A</td>;
                        }
                        const diffHigh = ((ltp - high52) / high52) * 100;
                        const diffLow = ((ltp - low52) / low52) * 100;
                        return (
                          <td
                            key={col.id}
                            style={{
                              padding: "6px 8px",
                              textAlign: "right",
                              fontFamily: "var(--font-family-mono)",
                              fontSize: "11px",
                            }}
                          >
                            <div>
                              H: ₹{high52.toFixed(1)}{" "}
                              <span style={{ color: diffHigh >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                                ({diffHigh >= 0 ? "+" : ""}{diffHigh.toFixed(1)}%)
                              </span>
                            </div>
                            <div style={{ color: "var(--text-muted)", marginTop: "1px" }}>
                              L: ₹{low52.toFixed(1)}{" "}
                              <span style={{ color: diffLow >= 0 ? "var(--color-up)" : "var(--color-down)" }}>
                                ({diffLow >= 0 ? "+" : ""}{diffLow.toFixed(1)}%)
                              </span>
                            </div>
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
                            onClick={() => {
                              setDepthItem(item);
                              handleSelectSymbol(item);
                            }}
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
                </React.Fragment>
              );
            })}
            </tbody>
          </table>
        )}
      </div>

      {/* 6. Market Depth Modal */}
      {depthItem && (
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
          <div onClick={(e) => e.stopPropagation()} style={{ maxWidth: "95vw" }}>
            <MarketDepthCard
              item={depthItem}
              onClose={() => setDepthItem(null)}
              capability={
                depthCapability?.actualLevel === "LEVEL_20"
                  ? "20-Level Full Depth (NSE)"
                  : "5-Level Depth Feed"
              }
            />
          </div>
        </div>
      )}

      {/* 7. Zerodha-style Discover Watchlists Modal */}
      <DiscoverWatchlistsModal
        isOpen={isDiscoverModalOpen}
        onClose={() => setIsDiscoverModalOpen(false)}
        userWatchlists={watchlists}
        activeWatchlistId={activeWatchlistId}
        onSelectWatchlist={(id) => {
          setActiveWatchlistId(id);
          setIsDiscoverModalOpen(false);
        }}
        onAddStandardWatchlist={handleAddStandardWatchlist}
        onCreateCustomWatchlist={handleCreateCustomWatchlist}
        onDeleteWatchlist={handleDeleteWatchlist}
      />
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
