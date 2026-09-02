import { describe, it, expect, beforeEach } from "vitest";
import {
  loadWatchlists,
  createWatchlist,
  updateWatchlist,
  deleteWatchlist,
  addSymbolToWatchlist,
  removeSymbolFromWatchlist,
  reorderWatchlistSymbols,
  moveItem,
  reconcileWithInstrumentMaster,
} from "./storage";

describe("Watchlist Storage and Manipulation", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("loads default seed watchlists on first launch", () => {
    const watchlists = loadWatchlists();
    expect(watchlists.length).toBeGreaterThanOrEqual(3);
    const names = watchlists.map((w) => w.name);
    expect(names).toContain("NIFTY 50");
    expect(names).toContain("BANK NIFTY F&O");
    expect(names).toContain("Breakout Stocks");
  });

  it("creates, updates, and deletes custom watchlists", () => {
    const created = createWatchlist("Tech Momentum", "IT stocks");
    expect(created.name).toBe("Tech Momentum");
    expect(created.isDefault).toBe(false);

    let all = loadWatchlists();
    expect(all.some((w) => w.id === created.id)).toBe(true);

    // Update columns and name
    const updated = updateWatchlist(created.id, {
      name: "Tech High Momentum",
      columns: ["symbol", "ltp", "volume", "bidAsk"],
    });
    expect(updated?.name).toBe("Tech High Momentum");
    expect(updated?.columns).toEqual(["symbol", "ltp", "volume", "bidAsk"]);

    // Delete custom watchlist
    const deleted = deleteWatchlist(created.id);
    expect(deleted).toBe(true);
    all = loadWatchlists();
    expect(all.some((w) => w.id === created.id)).toBe(false);

    // Cannot delete default watchlist
    const defaultDeleted = deleteWatchlist("wl-nifty50");
    expect(defaultDeleted).toBe(false);
  });

  it("adds, removes, and reorders symbols stably", () => {
    const wl = createWatchlist("Test Symbols");

    // Add symbols
    addSymbolToWatchlist(wl.id, {
      symbol: "SYM1",
      segment: "NSE_EQ",
      securityId: "1",
      tradingSymbol: "SYM1-EQ",
    });
    addSymbolToWatchlist(wl.id, {
      symbol: "SYM2",
      segment: "NSE_EQ",
      securityId: "2",
      tradingSymbol: "SYM2-EQ",
    });
    addSymbolToWatchlist(wl.id, {
      symbol: "SYM3",
      segment: "NSE_EQ",
      securityId: "3",
      tradingSymbol: "SYM3-EQ",
    });

    let refreshed = loadWatchlists().find((w) => w.id === wl.id)!;
    expect(refreshed.items.map((i) => i.symbol)).toEqual(["SYM1", "SYM2", "SYM3"]);

    // Move SYM3 up
    moveItem(wl.id, "SYM3", "up");
    refreshed = loadWatchlists().find((w) => w.id === wl.id)!;
    expect(refreshed.items.map((i) => i.symbol)).toEqual(["SYM1", "SYM3", "SYM2"]);

    // Reorder with explicit sequence
    reorderWatchlistSymbols(wl.id, ["SYM2", "SYM1", "SYM3"]);
    refreshed = loadWatchlists().find((w) => w.id === wl.id)!;
    expect(refreshed.items.map((i) => i.symbol)).toEqual(["SYM2", "SYM1", "SYM3"]);
    expect(refreshed.items[0].order).toBe(0);
    expect(refreshed.items[1].order).toBe(1);
    expect(refreshed.items[2].order).toBe(2);

    // Remove SYM1
    removeSymbolFromWatchlist(wl.id, "SYM1");
    refreshed = loadWatchlists().find((w) => w.id === wl.id)!;
    expect(refreshed.items.map((i) => i.symbol)).toEqual(["SYM2", "SYM3"]);
    expect(refreshed.items[0].order).toBe(0);
    expect(refreshed.items[1].order).toBe(1);
  });

  it("guarantees symbols and ordering survive instrument master refresh", () => {
    const initial = loadWatchlists();
    const nifty50 = initial.find((w) => w.id === "wl-nifty50")!;
    const initialOrder = nifty50.items.map((i) => i.symbol);

    // Simulate an instrument master refresh with only a subset of symbols present
    const refreshedMasterSymbols = new Set(["RELIANCE", "TCS", "NEW_SYMBOL_123"]);

    const reconciled = reconcileWithInstrumentMaster(initial, refreshedMasterSymbols);
    const reconciledNifty = reconciled.find((w) => w.id === "wl-nifty50")!;

    // Invariant: Symbols and order are strictly preserved
    expect(reconciledNifty.items.map((i) => i.symbol)).toEqual(initialOrder);

    // Symbols not in master are flagged stale but never dropped
    const hdfc = reconciledNifty.items.find((i) => i.symbol === "HDFCBANK")!;
    expect(hdfc.isStale).toBe(true);

    const reliance = reconciledNifty.items.find((i) => i.symbol === "RELIANCE")!;
    expect(reliance.isStale).toBe(false);
  });
});
