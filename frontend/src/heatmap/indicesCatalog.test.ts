import { describe, it, expect } from "vitest";
import {
  ALL_INDICES_BY_CATEGORY,
  getConstituentsForIndex,
} from "./indicesCatalog";
import { OFFICIAL_INDEX_CONSTITUENTS, DERIVED_INDICES } from "./officialConstituents";
import { NSE_STOCK_BY_SYMBOL } from "../watchlist/nseStockMaster";

const ALL_INDICES = Object.values(ALL_INDICES_BY_CATEGORY).flat();

describe("Index catalog constituent integrity", () => {
  it("backs every catalogued index with a constituent list", () => {
    for (const index of ALL_INDICES) {
      const official = OFFICIAL_INDEX_CONSTITUENTS[index.indexName];
      expect(official, `${index.indexName} has no constituent list`).toBeDefined();
      expect(official.length).toBeGreaterThan(0);
    }
  });

  it("drills into real NSE stocks, never a heuristic sector slice", () => {
    for (const index of ALL_INDICES) {
      const constituents = getConstituentsForIndex(index.indexName);
      expect(constituents.length, `${index.indexName} drill-in is empty`).toBeGreaterThan(0);
      for (const c of constituents) {
        expect(
          NSE_STOCK_BY_SYMBOL.has(c.symbol),
          `${index.indexName}: ${c.symbol} is not a listed NSE stock`
        ).toBe(true);
      }
      // The equal-weight fallback path means the index was not resolved officially.
      expect(
        constituents.some((c) => c.weightingSource === "FALLBACK_EQUAL_WEIGHT"),
        `${index.indexName} fell back to the heuristic sector filter`
      ).toBe(false);
    }
  });

  it("reports the declared constituent count that the drill-in actually returns", () => {
    for (const index of ALL_INDICES) {
      const constituents = getConstituentsForIndex(index.indexName);
      expect(index.constituentCount, `${index.indexName} count is stale`).toBe(
        constituents.length
      );
    }
  });

  it("never lists the same stock twice within an index", () => {
    for (const [name, list] of Object.entries(OFFICIAL_INDEX_CONSTITUENTS)) {
      const unique = new Set(list.map((s) => s.symbol));
      expect(unique.size, `${name} has duplicate constituents`).toBe(list.length);
    }
  });

  it("flags indices with no official NSE constituent CSV as derived, not official", () => {
    for (const index of ALL_INDICES) {
      const expected = DERIVED_INDICES.has(index.indexName) ? "DERIVED_SCREEN" : "OFFICIAL_NSE";
      expect(index.weightingSource, `${index.indexName} weighting source`).toBe(expected);
      for (const c of getConstituentsForIndex(index.indexName)) {
        expect(c.weightingSource).toBe(expected);
      }
    }
  });

  it("keeps the Shariah indices free of the businesses their methodology excludes", () => {
    // The Shariah lists used to be a verbatim copy of Nifty 50, banks included.
    const banned = ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "ITC"];
    for (const name of ["NIFTY SHARIAH 25", "NIFTY50 SHARIAH", "NIFTY500 SHARIAH"]) {
      const symbols = new Set(OFFICIAL_INDEX_CONSTITUENTS[name].map((s) => s.symbol));
      for (const b of banned) {
        expect(symbols.has(b), `${name} must not contain ${b}`).toBe(false);
      }
    }
  });

  it("gives each index a distinct membership unless NSE shares the universe", () => {
    // Indices NSE genuinely builds on an identical universe with different weights.
    const sharedUniverse = [
      new Set(["NIFTY FIN SERVICE", "NIFTY FINSRV25/50"]),
      new Set(["NIFTY MIDSML 400", "NIFTY MIDSMALLCAP400 50:50"]),
      new Set([
        "NIFTY 500",
        "NIFTY500 MULTICAP 50:25:25",
        "NIFTY500 LARGEMIDSMALL EQUAL-CAP WEIGHTED",
      ]),
      new Set(["NIFTY100 ESG", "NIFTY100 ENH ESG"]),
    ];
    const bySignature = new Map<string, string[]>();
    for (const [name, list] of Object.entries(OFFICIAL_INDEX_CONSTITUENTS)) {
      const sig = list
        .map((s) => s.symbol)
        .sort()
        .join(",");
      bySignature.set(sig, [...(bySignature.get(sig) ?? []), name]);
    }
    for (const names of bySignature.values()) {
      if (names.length === 1) continue;
      const allowed = sharedUniverse.some((group) => names.every((n) => group.has(n)));
      expect(allowed, `${names.join(" / ")} share an identical constituent list`).toBe(true);
    }
  });

  it("weights each index to 100%", () => {
    for (const index of ALL_INDICES) {
      const total = getConstituentsForIndex(index.indexName).reduce((a, c) => a + c.weight, 0);
      expect(total, `${index.indexName} weights`).toBeCloseTo(100, 1);
    }
  });
});
