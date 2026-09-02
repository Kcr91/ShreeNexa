import { Watchlist, WatchlistItem, WatchlistColumn } from "./types";

const WATCHLISTS_STORAGE_KEY = "shreenexa_watchlists_v1";

export const DEFAULT_WATCHLISTS: Watchlist[] = [
  {
    id: "wl-nifty50",
    name: "NIFTY 50",
    description: "Top large cap Indian equities",
    isDefault: true,
    columns: ["symbol", "ltp", "changePct", "volume", "highLow"],
    items: [
      {
        symbol: "RELIANCE",
        segment: "NSE_EQ",
        securityId: "2885",
        tradingSymbol: "RELIANCE-EQ",
        order: 0,
        ltp: 2980.50,
        changePct: 1.25,
        changeAbs: 36.75,
        volume: 4250000,
        high: 2995.00,
        low: 2950.00,
        bid: 2980.00,
        ask: 2981.00,
      },
      {
        symbol: "TCS",
        segment: "NSE_EQ",
        securityId: "11536",
        tradingSymbol: "TCS-EQ",
        order: 1,
        ltp: 4210.00,
        changePct: -0.45,
        changeAbs: -19.00,
        volume: 1850000,
        high: 4240.00,
        low: 4195.00,
        bid: 4209.50,
        ask: 4210.50,
      },
      {
        symbol: "HDFCBANK",
        segment: "NSE_EQ",
        securityId: "1333",
        tradingSymbol: "HDFCBANK-EQ",
        order: 2,
        ltp: 1640.20,
        changePct: 0.80,
        changeAbs: 13.00,
        volume: 6800000,
        high: 1655.00,
        low: 1630.00,
        bid: 1640.00,
        ask: 1640.50,
      },
      {
        symbol: "INFY",
        segment: "NSE_EQ",
        securityId: "1594",
        tradingSymbol: "INFY-EQ",
        order: 3,
        ltp: 1890.10,
        changePct: -1.10,
        changeAbs: -21.00,
        volume: 3100000,
        high: 1915.00,
        low: 1882.00,
        bid: 1889.50,
        ask: 1890.50,
      },
      {
        symbol: "ICICIBANK",
        segment: "NSE_EQ",
        securityId: "4963",
        tradingSymbol: "ICICIBANK-EQ",
        order: 4,
        ltp: 1215.30,
        changePct: 1.65,
        changeAbs: 19.70,
        volume: 5400000,
        high: 1222.00,
        low: 1201.00,
        bid: 1215.00,
        ask: 1215.50,
      },
    ],
  },
  {
    id: "wl-banknifty-fno",
    name: "BANK NIFTY F&O",
    description: "Active Bank Nifty weekly and monthly derivative contracts",
    isDefault: false,
    columns: ["symbol", "ltp", "changePct", "oi", "oiChangePct", "volume"],
    items: [
      {
        symbol: "BANKNIFTY-FUT",
        segment: "NSE_FNO",
        securityId: "52001",
        tradingSymbol: "BANKNIFTY26SEPFUT",
        order: 0,
        expiry: "2026-09-30",
        ltp: 52150.00,
        changePct: 0.65,
        changeAbs: 335.00,
        volume: 850000,
        oi: 2450000,
        oiChangePct: 3.2,
      },
      {
        symbol: "BANKNIFTY-52000-CE",
        segment: "NSE_FNO",
        securityId: "52002",
        tradingSymbol: "BANKNIFTY26SEP52000CE",
        order: 1,
        expiry: "2026-09-30",
        strike: 52000,
        optionType: "CE",
        ltp: 385.50,
        changePct: 12.50,
        changeAbs: 42.80,
        volume: 1250000,
        oi: 3800000,
        oiChangePct: 8.5,
      },
      {
        symbol: "BANKNIFTY-51500-PE",
        segment: "NSE_FNO",
        securityId: "52003",
        tradingSymbol: "BANKNIFTY26SEP51500PE",
        order: 2,
        expiry: "2026-09-30",
        strike: 51500,
        optionType: "PE",
        ltp: 145.20,
        changePct: -18.40,
        changeAbs: -32.80,
        volume: 980000,
        oi: 2900000,
        oiChangePct: -4.1,
      },
    ],
  },
  {
    id: "wl-breakout",
    name: "Breakout Stocks",
    description: "High volume breakout candidates",
    isDefault: false,
    columns: ["symbol", "ltp", "changePct", "volume", "highLow"],
    items: [
      {
        symbol: "TATASTEEL",
        segment: "NSE_EQ",
        securityId: "3499",
        tradingSymbol: "TATASTEEL-EQ",
        order: 0,
        ltp: 154.80,
        changePct: 2.85,
        changeAbs: 4.30,
        volume: 12400000,
        high: 156.50,
        low: 150.20,
      },
      {
        symbol: "SBIN",
        segment: "NSE_EQ",
        securityId: "3045",
        tradingSymbol: "SBIN-EQ",
        order: 1,
        ltp: 815.40,
        changePct: 1.15,
        changeAbs: 9.25,
        volume: 7600000,
        high: 822.00,
        low: 808.00,
      },
    ],
  },
];

export function loadWatchlists(): Watchlist[] {
  try {
    const raw = localStorage.getItem(WATCHLISTS_STORAGE_KEY);
    if (!raw) {
      saveWatchlists(DEFAULT_WATCHLISTS);
      return DEFAULT_WATCHLISTS;
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed;
    }
  } catch {
    // Fall back gracefully on corrupt storage
  }
  return DEFAULT_WATCHLISTS;
}

export function saveWatchlists(watchlists: Watchlist[]): void {
  try {
    localStorage.setItem(WATCHLISTS_STORAGE_KEY, JSON.stringify(watchlists));
  } catch (err) {
    console.error("Failed to save watchlists to localStorage:", err);
  }
}

export function createWatchlist(
  name: string,
  description: string = "",
  columns: WatchlistColumn[] = ["symbol", "ltp", "changePct", "volume"]
): Watchlist {
  const watchlists = loadWatchlists();
  const newWatchlist: Watchlist = {
    id: `wl-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
    name: name.trim() || "Untitled Watchlist",
    description,
    isDefault: false,
    columns,
    items: [],
  };
  watchlists.push(newWatchlist);
  saveWatchlists(watchlists);
  return newWatchlist;
}

export function updateWatchlist(
  id: string,
  updates: Partial<Pick<Watchlist, "name" | "description" | "columns">>
): Watchlist | null {
  const watchlists = loadWatchlists();
  const wl = watchlists.find((w) => w.id === id);
  if (!wl) return null;

  if (updates.name !== undefined) wl.name = updates.name.trim();
  if (updates.description !== undefined) wl.description = updates.description;
  if (updates.columns !== undefined) wl.columns = updates.columns;

  saveWatchlists(watchlists);
  return wl;
}

export function deleteWatchlist(id: string): boolean {
  const watchlists = loadWatchlists();
  const target = watchlists.find((w) => w.id === id);
  if (!target || target.isDefault) return false;

  const filtered = watchlists.filter((w) => w.id !== id);
  saveWatchlists(filtered);
  return true;
}

export function addSymbolToWatchlist(
  watchlistId: string,
  item: Omit<WatchlistItem, "order">
): Watchlist | null {
  const watchlists = loadWatchlists();
  const wl = watchlists.find((w) => w.id === watchlistId);
  if (!wl) return null;

  if (wl.items.some((i) => i.symbol === item.symbol)) {
    return wl; // Already present
  }

  const newItem: WatchlistItem = {
    ...item,
    order: wl.items.length,
  };
  wl.items.push(newItem);
  saveWatchlists(watchlists);
  return wl;
}

export function removeSymbolFromWatchlist(
  watchlistId: string,
  symbol: string
): Watchlist | null {
  const watchlists = loadWatchlists();
  const wl = watchlists.find((w) => w.id === watchlistId);
  if (!wl) return null;

  wl.items = wl.items.filter((i) => i.symbol !== symbol);
  // Re-index orders stably
  wl.items.forEach((item, index) => {
    item.order = index;
  });

  saveWatchlists(watchlists);
  return wl;
}

export function reorderWatchlistSymbols(
  watchlistId: string,
  orderedSymbols: string[]
): Watchlist | null {
  const watchlists = loadWatchlists();
  const wl = watchlists.find((w) => w.id === watchlistId);
  if (!wl) return null;

  const itemMap = new Map<string, WatchlistItem>(
    wl.items.map((item) => [item.symbol, item])
  );
  const reordered: WatchlistItem[] = [];

  orderedSymbols.forEach((sym, idx) => {
    const item = itemMap.get(sym);
    if (item) {
      item.order = idx;
      reordered.push(item);
      itemMap.delete(sym);
    }
  });

  // Append any unmentioned remaining items
  let nextOrder = reordered.length;
  itemMap.forEach((item) => {
    item.order = nextOrder++;
    reordered.push(item);
  });

  wl.items = reordered;
  saveWatchlists(watchlists);
  return wl;
}

export function moveItem(
  watchlistId: string,
  symbol: string,
  direction: "up" | "down"
): Watchlist | null {
  const watchlists = loadWatchlists();
  const wl = watchlists.find((w) => w.id === watchlistId);
  if (!wl) return null;

  const index = wl.items.findIndex((i) => i.symbol === symbol);
  if (index === -1) return null;

  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= wl.items.length) return wl;

  const temp = wl.items[index];
  wl.items[index] = wl.items[targetIndex];
  wl.items[targetIndex] = temp;

  wl.items.forEach((item, idx) => {
    item.order = idx;
  });

  saveWatchlists(watchlists);
  return wl;
}

/**
 * Reconciles user watchlists against a refreshed instrument master.
 *
 * Invariant: Symbols and manual ordering strictly survive instrument-master refreshes.
 */
export function reconcileWithInstrumentMaster(
  watchlists: Watchlist[],
  masterSymbols: Set<string>
): Watchlist[] {
  return watchlists.map((wl) => ({
    ...wl,
    items: wl.items.map((item) => ({
      ...item,
      // If symbol exists in master, mark it valid, otherwise retain existing symbol intact
      isStale: !masterSymbols.has(item.symbol),
    })),
  }));
}
