#!/usr/bin/env python3
"""Fetch official NSE index constituents and regenerate the frontend data modules.

See scripts/_nse_sources.py for the source list and the index -> CSV mapping.

    python scripts/fetch_nse_constituents.py                # refresh everything
    python scripts/fetch_nse_constituents.py --cache-dir X  # reuse downloads in X
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _nse_sources import DERIVED, MAP, normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
}
NIFTY_CSV = "https://www.niftyindices.com/IndexConstituent/{}.csv"
EQUITY_L = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
DHAN_MASTER = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

# Business-activity screens for the indices NSE publishes no constituent CSV for.
SHARIAH_EXCLUDED_INDUSTRIES = {"Financial Services"}
SHARIAH_EXCLUDED_SYMBOLS = {
    "UBL",
    "UNITDSPR",
    "RADICO",
    "GLOBUSSPR",
    "SDBL",
    "ABDL",
    "ITC",
    "GODFRYPHLP",
    "VSTIND",
    "ITCHOTELS",
    "NAZARA",
    "PVRINOX",
    "ZEEL",
    "SUNTV",
    "NETWORK18",
    "TV18BRDCST",
    "SAREGAMA",
    "TIPSMUSIC",
    "TIPSFILMS",
    "DBCORP",
    "HATHWAY",
    "DISHTV",
    "PFOCUS",
    "JAGRAN",
    "NDTV",
    "INDHOTEL",
    "EIHOTEL",
    "CHALET",
    "LEMONTREE",
    "JUBLFOOD",
    "WESTLIFE",
    "DEVYANI",
    "SAPPHIRE",
    "MHRIL",
    "TAJGVK",
    "SAMHI",
    "VENTIVE",
    "JUNIPER",
}
ESG_EXCLUDED_SYMBOLS = {
    "ITC",
    "GODFRYPHLP",
    "VSTIND",
    "UBL",
    "UNITDSPR",
    "RADICO",
    "NAZARA",
    "COALINDIA",
    "NLCINDIA",
    "ADANIPOWER",
    "ADANIENT",
    "GMDCLTD",
    "BEL",
    "BDL",
    "HAL",
    "MAZDOCK",
    "SOLARINDS",
}

CONSTITUENTS_TS = os.path.join(ROOT, "frontend", "src", "heatmap", "officialConstituents.ts")
STOCK_MASTER_TS = os.path.join(ROOT, "frontend", "src", "watchlist", "nseStockMaster.ts")
BACKEND_JSON = os.path.join(ROOT, "config", "nifty_official_constituents.json")


def fetch(url: str, cache: str, name: str, retries: int = 3) -> bytes:
    path = os.path.join(cache, name)
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return open(path, "rb").read()
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={**UA, "Referer": "https://www.nseindia.com/"}
            )
            data = urllib.request.urlopen(req, timeout=90).read()
            open(path, "wb").write(data)
            time.sleep(0.3)
            return data
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise SystemExit(f"could not fetch {url}: {last}")


def read_constituents(cache: str):
    out = {}
    for index, slug in MAP.items():
        data = fetch(NIFTY_CSV.format(urllib.parse.quote(slug)), cache, slug + ".csv")
        if not data.startswith(b"Company"):
            raise SystemExit(f"{index}: {slug}.csv is not a constituent CSV (index renamed?)")
        rows = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        out[index] = [
            {
                "symbol": r["Symbol"].strip(),
                "name": (r.get("Company Name") or r.get("Company") or "").strip(),
                "industry": (r.get("Industry") or "").strip(),
            }
            for r in rows
            if (r.get("Symbol") or "").strip()
        ]
    return out


def read_dhan(cache: str):
    data = fetch(DHAN_MASTER, cache, "dhan_detailed.csv")
    out = {}
    for r in csv.DictReader(io.StringIO(data.decode("utf-8", "replace"))):
        if r["EXCH_ID"] != "NSE" or r["SEGMENT"] != "E" or r["INSTRUMENT"] != "EQUITY":
            continue
        sym = (r["UNDERLYING_SYMBOL"] or "").strip()
        if sym and sym not in out:
            out[sym] = {
                "securityId": r["SECURITY_ID"].strip(),
                "name": r["DISPLAY_NAME"].strip(),
                "isin": r["ISIN"].strip(),
            }
    return out


def load_previous():
    if not os.path.exists(CONSTITUENTS_TS):
        return {}
    m = re.search(r"const RAW_JSON = `([\s\S]*?)`;", open(CONSTITUENTS_TS, encoding="utf-8").read())
    if not m:
        return {}
    return {k: [x["symbol"] for x in v] for k, v in json.loads(m.group(1)).items()}


def report(prev, now):
    print("\n=== constituent changes ===")
    changed = 0
    for index in sorted(now):
        before, after = prev.get(index, []), now[index]
        if before == after:
            continue
        changed += 1
        added, removed = set(after) - set(before), set(before) - set(after)
        print(f"{index}: {len(before)} -> {len(after)}  +{len(added)} -{len(removed)}")
        if added:
            print("    added:  ", ", ".join(sorted(added)))
        if removed:
            print("    removed:", ", ".join(sorted(removed)))
    print(f"{changed} of {len(now)} indices changed")


def write_constituents(official, dhan):
    payload = {k: [{"symbol": s, "name": dhan[s]["name"]} for s in v] for k, v in official.items()}
    header = HEADER_TEMPLATE % (
        len(payload) - len(DERIVED),
        len(payload),
        len(DERIVED),
        json.dumps(sorted(DERIVED)),
    )
    body = "const RAW_JSON = `" + json.dumps(payload, separators=(",", ":")) + "`;\n\n"
    body += (
        "export const OFFICIAL_INDEX_CONSTITUENTS: "
        "Record<string, OfficialConstituentStock[]> = JSON.parse(RAW_JSON);\n"
    )
    open(CONSTITUENTS_TS, "w", encoding="utf-8", newline="\n").write(header + body)
    print(f"\nwrote {CONSTITUENTS_TS} ({len(payload)} indices)")


def write_stock_master(official, dhan, industry):
    symbols = sorted({s for v in official.values() for s in v})
    row = (
        '  {{ symbol: "{s}", tradingSymbol: "{s}-EQ", securityId: "{sid}", '
        'name: "{n}", sector: "{sec}" }},'
    )
    rows = "\n".join(
        row.format(
            s=s,
            sid=dhan[s]["securityId"],
            n=dhan[s]["name"].replace('"', ""),
            sec=industry.get(s, "Other"),
        )
        for s in symbols
    )
    open(STOCK_MASTER_TS, "w", encoding="utf-8", newline="\n").write(MASTER_TEMPLATE % rows)
    print(f"wrote {STOCK_MASTER_TS} ({len(symbols)} stocks)")


def write_backend_json(official, dhan, industry):
    """The heatmap API reads the same constituents; keep both copies in step."""
    payload = {
        index: {
            "source_file": MAP.get(index, "derived") + (".csv" if index in MAP else ""),
            "derived": index in DERIVED,
            "count": len(symbols),
            "stocks": [
                {
                    "symbol": s,
                    "name": dhan[s]["name"],
                    "sector": industry.get(s, "Other"),
                    "securityId": dhan[s]["securityId"],
                }
                for s in symbols
            ],
        }
        for index, symbols in official.items()
    }
    with open(BACKEND_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {BACKEND_JSON} ({len(payload)} indices)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "build", "nse-cache"))
    args = ap.parse_args()
    os.makedirs(args.cache_dir, exist_ok=True)
    cache = args.cache_dir

    fetched = read_constituents(cache)
    dhan = read_dhan(cache)
    fetch(EQUITY_L, cache, "EQUITY_L.csv")  # cached for the test suite / manual review

    industry = {}
    for rows in fetched.values():
        for r in rows:
            if r["industry"]:
                industry.setdefault(r["symbol"], r["industry"])

    official = {index: normalize([r["symbol"] for r in rows]) for index, rows in fetched.items()}

    unknown = sorted({s for v in official.values() for s in v} - set(dhan))
    if unknown:
        print(
            f"WARNING: dropping {len(unknown)} symbols absent from the Dhan scrip master: {unknown}"
        )
        official = {k: [s for s in v if s in dhan] for k, v in official.items()}

    def screen(parent, kind):
        excluded = SHARIAH_EXCLUDED_SYMBOLS if kind == "shariah" else ESG_EXCLUDED_SYMBOLS
        return [
            s
            for s in official[parent]
            if s not in excluded
            and not (kind == "shariah" and industry.get(s) in SHARIAH_EXCLUDED_INDUSTRIES)
        ]

    prev = load_previous()
    nifty100 = set(official["NIFTY 100"])
    shariah500 = screen("NIFTY 500", "shariah")
    official["NIFTY500 SHARIAH"] = shariah500
    official["NIFTY50 SHARIAH"] = screen("NIFTY 50", "shariah")
    official["NIFTY SHARIAH 25"] = [s for s in shariah500 if s in nifty100][:25]
    official["NIFTY100 ESG"] = screen("NIFTY 100", "esg")
    official["NIFTY100 ENH ESG"] = screen("NIFTY 100", "esg")
    # NSE publishes no CSV and no derivable screen for NIFTY EV; carry the existing
    # curated list forward, normalized against the live masters.
    official["NIFTY EV"] = [s for s in normalize(prev.get("NIFTY EV", [])) if s in dhan]

    report(prev, official)
    write_constituents(official, dhan)
    write_stock_master(official, dhan, industry)
    write_backend_json(official, dhan, industry)


HEADER_TEMPLATE = """// Official NSE index constituents.
//
// Source of record: the "Index Constituent" CSV published on each index page at
// https://www.niftyindices.com/IndexConstituent/<index>.csv
// Symbols are normalized against the live NSE equity master
// (nsearchives.nseindia.com/content/equities/EQUITY_L.csv) and the Dhan scrip
// master, which drops NSE's DUMMY* placeholder rows and applies symbol renames
// (e.g. TATAMOTORS -> TMPV, LTIM -> LTM, ZOMATO -> ETERNAL).
//
// Regenerate with: python scripts/fetch_nse_constituents.py
//
// %d of the %d indices below are the official NSE constituent list verbatim.
// NSE publishes no constituent CSV for the other %d, so their membership is
// derived and flagged in DERIVED_INDICES:
//   * Shariah indices - parent index filtered by the published Nifty Shariah
//     business-activity screens (financials, alcohol, tobacco, gambling,
//     conventional media/entertainment, hotels). The additional financial-ratio
//     screen needs balance-sheet data, so membership is an approximation.
//   * ESG indices     - Nifty 100 minus the controversial-business exclusions
//     (tobacco, alcohol, gambling, thermal coal, defence). ESG scores are not public.
//   * NIFTY EV        - curated constituent list; NSE publishes no CSV.

export interface OfficialConstituentStock {
  symbol: string;
  name: string;
}

/** Indices whose membership is derived by screen, not an official NSE CSV. */
export const DERIVED_INDICES: ReadonlySet<string> = new Set(%s);

"""

MASTER_TEMPLATE = """// NSE cash-segment stock master for every symbol in an index we ship.
//
// symbol / sector : official NSE index constituent CSVs (niftyindices.com) and the
//                   NSE equity master (nsearchives.nseindia.com/content/equities/EQUITY_L.csv)
// securityId      : Dhan scrip master (https://images.dhan.co/api-data/api-scrip-master-detailed.csv)
//                   - these are the real ids the Dhan API expects, do not hand-edit them.
//
// Regenerate with: python scripts/fetch_nse_constituents.py

export interface NseStockMasterEntry {
  symbol: string;
  tradingSymbol: string;
  securityId: string;
  name: string;
  sector: string;
}

export const NSE_STOCK_MASTER: NseStockMasterEntry[] = [
%s
];

export const NSE_STOCK_BY_SYMBOL: Map<string, NseStockMasterEntry> = new Map(
  NSE_STOCK_MASTER.map((s) => [s.symbol, s])
);
"""


if __name__ == "__main__":
    main()
