import { describe, it, expect, beforeEach } from "vitest";
import {
  STANDARD_WATCHLISTS,
  FNO_208_STOCKS,
  NIFTY_50_SYMBOLS,
  instantiateStandardWatchlist,
  searchStandardWatchlists,
  getStandardWatchlistById,
} from "./standardWatchlists";
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

  it("defines Nifty 50 with exactly 50 constituent stocks", () => {
    const nifty50Preset = getStandardWatchlistById("std-nifty-50");
    expect(nifty50Preset).toBeDefined();
    expect(NIFTY_50_SYMBOLS.length).toBe(50);
    expect(nifty50Preset!.itemCount).toBe(50);

    const instantiated = instantiateStandardWatchlist(nifty50Preset!);
    expect(instantiated.name).toBe("Nifty 50");
    expect(instantiated.items.length).toBe(50);
    expect(instantiated.items[0].symbol).toBe("RELIANCE");
    expect(instantiated.items[0].order).toBe(0);
    expect(instantiated.items[49].order).toBe(49);
  });

  it("defines NSE F&O Stocks with all 208 F&O stocks", () => {
    expect(FNO_208_STOCKS.length).toBe(208);

    const fnoPreset = getStandardWatchlistById("std-nse-fno-stocks");
    expect(fnoPreset).toBeDefined();
    expect(fnoPreset!.itemCount).toBe(208);

    const instantiated = instantiateStandardWatchlist(fnoPreset!);
    expect(instantiated.items.length).toBe(208);
    expect(instantiated.isGroupedBySector).toBeFalsy();

    // Verify all 208 symbols are unique
    const uniqueSymbols = new Set(instantiated.items.map((i) => i.symbol));
    expect(uniqueSymbols.size).toBe(208);
  });

  it("defines NSE F&O Stocks (Grouped by sector) with sector ordering and sector tags", () => {
    const groupedPreset = getStandardWatchlistById("std-nse-fno-stocks-grouped");
    expect(groupedPreset).toBeDefined();
    expect(groupedPreset!.isGroupedBySector).toBe(true);

    const instantiated = instantiateStandardWatchlist(groupedPreset!);
    expect(instantiated.isGroupedBySector).toBe(true);
    expect(instantiated.items.length).toBe(208);

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
