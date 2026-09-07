import { describe, it, expect, beforeEach } from "vitest";
import {
  STANDARD_WATCHLISTS,
  FNO_STOCKS,
  NIFTY_50_SYMBOLS,
  instantiateStandardWatchlist,
  searchStandardWatchlists,
  getStandardWatchlistById,
} from "./standardWatchlists";
import { NSE_STOCK_BY_SYMBOL } from "./nseStockMaster";
import { OFFICIAL_INDEX_CONSTITUENTS } from "../heatmap/officialConstituents";
import {
  loadWatchlists,
  addStandardWatchlistToUser,
} from "./storage";

describe("Standard Watchlists Catalog and Factory", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("contains all required standard presets matching specification", () => {
    expect(STANDARD_WATCHLISTS.length).toBeGreaterThanOrEqual(20);

    const ids = STANDARD_WATCHLISTS.map((p) => p.id);
    expect(ids).toContain("std-nifty-50");
    expect(ids).toContain("std-nifty-50-grouped");
    expect(ids).toContain("std-nifty-next-50");
    expect(ids).toContain("std-nifty-next-50-grouped");
    expect(ids).toContain("std-bse-sensex");
    expect(ids).toContain("std-bse-sensex-grouped");
    expect(ids).toContain("std-nifty-100");
    expect(ids).toContain("std-nifty-200");
    expect(ids).toContain("std-nifty-largemidcap-250");
    expect(ids).toContain("std-nifty-midcap-150");
    expect(ids).toContain("std-nifty-midcap-select");
    expect(ids).toContain("std-nifty-smallcap-250");
    expect(ids).toContain("std-nifty-microcap-250");
    expect(ids).toContain("std-bank-nifty");
    expect(ids).toContain("std-nifty-finnifty");
    expect(ids).toContain("std-nifty-it");
    expect(ids).toContain("std-nifty-auto");
    expect(ids).toContain("std-nifty-fmcg");
    expect(ids).toContain("std-nifty-pharma");
    expect(ids).toContain("std-nifty-metal");
    expect(ids).toContain("std-nifty-realty");
    expect(ids).toContain("std-bse-bankex");
    expect(ids).toContain("std-nse-fno-stocks");
    expect(ids).toContain("std-nse-fno-stocks-grouped");
  });

  it("defines Nifty 50 as the official NSE constituent list", () => {
    const nifty50Preset = getStandardWatchlistById("std-nifty-50");
    expect(nifty50Preset).toBeDefined();

    const official = OFFICIAL_INDEX_CONSTITUENTS["NIFTY 50"].map((s) => s.symbol);
    expect(NIFTY_50_SYMBOLS.length).toBe(50);
    expect([...NIFTY_50_SYMBOLS].sort()).toEqual([...official].sort());
    expect(nifty50Preset!.itemCount).toBe(50);

    const instantiated = instantiateStandardWatchlist(nifty50Preset!);
    expect(instantiated.name).toBe("Nifty 50");
    expect(instantiated.items.length).toBe(50);
    expect(instantiated.items[0].order).toBe(0);
    expect(instantiated.items[49].order).toBe(49);
  });

  it("defines NSE F&O Stocks from the NSE derivatives market-lot list", () => {
    // Sourced from nsearchives.nseindia.com/content/fo/fo_mktlots.csv - the count
    // moves as NSE adds and removes names, so assert the shape, not a magic number.
    expect(FNO_STOCKS.length).toBeGreaterThan(180);

    const fnoPreset = getStandardWatchlistById("std-nse-fno-stocks");
    expect(fnoPreset).toBeDefined();
    expect(fnoPreset!.itemCount).toBe(FNO_STOCKS.length);

    const instantiated = instantiateStandardWatchlist(fnoPreset!);
    expect(instantiated.items.length).toBe(FNO_STOCKS.length);
    expect(instantiated.isGroupedBySector).toBeFalsy();

    const uniqueSymbols = new Set(instantiated.items.map((i) => i.symbol));
    expect(uniqueSymbols.size).toBe(FNO_STOCKS.length);

    // Every F&O name must carry a real Dhan security id.
    for (const stock of FNO_STOCKS) {
      expect(NSE_STOCK_BY_SYMBOL.get(stock.symbol)?.securityId).toBe(stock.securityId);
    }
  });

  it("defines NSE F&O Stocks (Grouped by sector) with sector ordering and sector tags", () => {
    const groupedPreset = getStandardWatchlistById("std-nse-fno-stocks-grouped");
    expect(groupedPreset).toBeDefined();
    expect(groupedPreset!.isGroupedBySector).toBe(true);

    const instantiated = instantiateStandardWatchlist(groupedPreset!);
    expect(instantiated.isGroupedBySector).toBe(true);
    expect(instantiated.items.length).toBe(FNO_STOCKS.length);

    // Verify all items have a valid sector assigned
    for (const item of instantiated.items) {
      expect(item.sector).toBeDefined();
      expect(item.sector!.length).toBeGreaterThan(0);
    }

    // Verify grouped preset is ordered by sector
    const sectors = instantiated.items.map((i) => i.sector!);
    for (let i = 1; i < sectors.length; i++) {
      expect(sectors[i].localeCompare(sectors[i - 1])).toBeGreaterThanOrEqual(0);
    }
  });

  it("filters standard watchlists correctly with searchStandardWatchlists", () => {
    const itResults = searchStandardWatchlists("IT");
    expect(itResults.some((p) => p.name === "Nifty IT")).toBe(true);

    const fnoResults = searchStandardWatchlists("F&O");
    expect(fnoResults.length).toBeGreaterThanOrEqual(2);
    expect(fnoResults.some((p) => p.id === "std-nse-fno-stocks")).toBe(true);

    const smallcapResults = searchStandardWatchlists("smallcap");
    expect(smallcapResults.some((p) => p.id === "std-nifty-smallcap-250")).toBe(true);

    const emptyResults = searchStandardWatchlists("XYZNONEXISTENTQUERY");
    expect(emptyResults.length).toBe(0);
  });

  it("adds standard watchlist to user storage and avoids name collisions", () => {
    const initialWatchlists = loadWatchlists();
    const initialCount = initialWatchlists.length;

    // Add Nifty 50 standard preset
    const addedWl = addStandardWatchlistToUser("std-nifty-50");
    expect(addedWl.name).toBe("Nifty 50");
    expect(addedWl.items.length).toBe(50);

    const afterFirstAdd = loadWatchlists();
    expect(afterFirstAdd.length).toBe(initialCount + 1);
    expect(afterFirstAdd.some((w) => w.id === addedWl.id)).toBe(true);

    // Add again -> should create duplicate with disambiguated name
    const addedAgain = addStandardWatchlistToUser("std-nifty-50");
    expect(addedAgain.name).toBe("Nifty 50 (1)");
    expect(addedAgain.id).not.toBe(addedWl.id);

    const afterSecondAdd = loadWatchlists();
    expect(afterSecondAdd.length).toBe(initialCount + 2);
  });
});

describe("Standard watchlist data integrity", () => {
  // Guards the class of bug where a preset shipped padded or invented rows:
  // synthetic STK### tickers, symbols with no security id, or a stale index list.
  it("resolves every shipped symbol to a real NSE stock with a Dhan security id", () => {
    for (const preset of STANDARD_WATCHLISTS) {
      if (preset.category !== "INDICES" && preset.category !== "F&O STOCKS") continue;
      const items = preset.getItems();
      for (const item of items) {
        if (item.instrumentType === "INDEX") continue;
        const entry = NSE_STOCK_BY_SYMBOL.get(item.symbol);
        expect(entry, `${preset.id}: unknown symbol ${item.symbol}`).toBeDefined();
        expect(item.securityId, `${preset.id}: ${item.symbol} has no security id`).toBe(
          entry!.securityId
        );
        expect(item.symbol).not.toMatch(/^STK\d+$/);
      }
    }
  });

  it("has no duplicate symbols and an accurate itemCount in any preset", () => {
    for (const preset of STANDARD_WATCHLISTS) {
      const items = preset.getItems();
      const unique = new Set(items.map((i) => i.symbol));
      expect(unique.size, `${preset.id} has duplicate symbols`).toBe(items.length);
      expect(preset.itemCount, `${preset.id} itemCount is stale`).toBe(items.length);
    }
  });

  it("matches the official NSE constituent list for every index-backed preset", () => {
    const backing: Record<string, string> = {
      "std-nifty-50": "NIFTY 50",
      "std-nifty-next-50": "NIFTY NEXT 50",
      "std-nifty-100": "NIFTY 100",
      "std-nifty-200": "NIFTY 200",
      "std-nifty-largemidcap-250": "NIFTY LARGEMIDCAP 250",
      "std-nifty-midcap-150": "NIFTY MIDCAP 150",
      "std-nifty-midcap-select": "NIFTY MID SELECT",
      "std-nifty-smallcap-250": "NIFTY SMLCAP 250",
      "std-nifty-microcap-250": "NIFTY MICROCAP 250",
      "std-bank-nifty": "NIFTY BANK",
      "std-nifty-finnifty": "NIFTY FIN SERVICE",
      "std-nifty-it": "NIFTY IT",
      "std-nifty-auto": "NIFTY AUTO",
      "std-nifty-fmcg": "NIFTY FMCG",
      "std-nifty-pharma": "NIFTY PHARMA",
      "std-nifty-metal": "NIFTY METAL",
      "std-nifty-realty": "NIFTY REALTY",
    };
    for (const [id, index] of Object.entries(backing)) {
      const preset = getStandardWatchlistById(id);
      expect(preset, `${id} missing`).toBeDefined();
      const official = OFFICIAL_INDEX_CONSTITUENTS[index].map((s) => s.symbol).sort();
      const shipped = preset!.getItems().map((i) => i.symbol).sort();
      expect(shipped, `${id} does not match ${index}`).toEqual(official);
    }
  });

  it("ships only currently-listed symbols in the hand-maintained BSE lists", () => {
    for (const id of ["std-bse-sensex", "std-bse-bankex"]) {
      const preset = getStandardWatchlistById(id)!;
      for (const item of preset.getItems()) {
        expect(NSE_STOCK_BY_SYMBOL.has(item.symbol), `${id}: stale symbol ${item.symbol}`).toBe(
          true
        );
      }
    }
  });
});
