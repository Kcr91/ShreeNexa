#!/usr/bin/env python3
"""Regenerate the NSE reference data the frontend ships.

Writes:
  frontend/src/heatmap/officialConstituents.ts   index -> constituent symbols
  frontend/src/watchlist/nseStockMaster.ts       symbol -> Dhan securityId, name, sector

Sources (all public, no credentials needed):
  * niftyindices.com/IndexConstituent/<index>.csv  official index constituents
  * nsearchives.nseindia.com/content/equities/EQUITY_L.csv   live NSE equity master
  * nsearchives.nseindia.com/content/fo/fo_mktlots.csv       F&O eligible equities
  * images.dhan.co/api-data/api-scrip-master-detailed.csv    Dhan security ids

Usage:  python scripts/fetch_nse_constituents.py [--cache-dir DIR]

Run this whenever NSE rebalances an index (semi-annual for the broad market
indices, and ad hoc after a merger, demerger or symbol change), then review the
printed diff before committing. The script never invents a symbol: anything NSE
publishes that is not in the live equity master and Dhan scrip master is
reported and dropped rather than guessed at.
"""

# ==========================================================================
# from map.py
# ==========================================================================
# Authoritative mapping: catalog index name -> niftyindices IndexConstituent CSV filename
MAP = {
    # Broad market
    "NIFTY 50": "ind_nifty50list",
    "NIFTY NEXT 50": "ind_niftynext50list",
    "NIFTY MIDCAP 50": "ind_niftymidcap50list",
    "NIFTY MIDCAP 100": "ind_niftymidcap100list",
    "NIFTY MIDCAP 150": "ind_niftymidcap150list",
    "NIFTY SMLCAP 50": "ind_niftysmallcap50list",
    "NIFTY SMLCAP 100": "ind_niftysmallcap100list",
    "NIFTY SMLCAP 250": "ind_niftysmallcap250list",
    "NIFTY MIDSML 400": "ind_niftymidsmallcap400list",
    "NIFTY 100": "ind_nifty100list",
    "NIFTY 200": "ind_nifty200list",
    "NIFTY500 MULTICAP 50:25:25": "ind_nifty500Multicap502525_list",
    "NIFTY LARGEMIDCAP 250": "ind_niftylargemidcap250list",
    "NIFTY MID SELECT": "ind_niftymidcapselect_list",
    "NIFTY TOTAL MARKET": "ind_niftytotalmarket_list",
    "NIFTY MICROCAP 250": "ind_niftymicrocap250_list",
    "NIFTY 500": "ind_nifty500list",
    "NIFTY INDIA FPI 150": "ind_niftyIndiaFPI150_list",
    "NIFTY500 LARGEMIDSMALL EQUAL-CAP WEIGHTED": "ind_nifty500LargeMidSmallEqualCapWeighted_list",
    "NIFTY MIDSMALLCAP400 50:50": "ind_niftyMidSmallcap4005050_list",
    "NIFTY SMALLCAP 500": "ind_NiftySmallcap500_list",
    # Sectoral
    "NIFTY AUTO": "ind_niftyautolist",
    "NIFTY BANK": "ind_niftybanklist",
    "NIFTY FIN SERVICE": "ind_niftyfinancelist",
    "NIFTY FINSRV25/50": "ind_niftyfinancialservices25-50list",
    "NIFTY FMCG": "ind_niftyfmcglist",
    "NIFTY IT": "ind_niftyitlist",
    "NIFTY MEDIA": "ind_niftymedialist",
    "NIFTY METAL": "ind_niftymetallist",
    "NIFTY PHARMA": "ind_niftypharmalist",
    "NIFTY PSU BANK": "ind_niftypsubanklist",
    "NIFTY REALTY": "ind_niftyrealtylist",
    "NIFTY PVT BANK": "ind_nifty_privatebanklist",
    "NIFTY HEALTHCARE": "ind_niftyhealthcarelist",
    "NIFTY CONSR DURBL": "ind_niftyconsumerdurableslist",
    "NIFTY OIL AND GAS": "ind_niftyoilgaslist",
    "NIFTY MIDSML HLTH": "ind_niftymidsmallhealthcare_list",
    "NIFTY CHEMICALS": "ind_niftyChemicals_list",
    "NIFTY500 HEALTHCARE": "ind_nifty500Healthcare_list",
    "NIFTY FINSERVIEXBK": "ind_niftyfinancialservicesexbank_list",
    "NIFTY MS FIN SERV": "ind_niftymidsmallfinancailservice_list",
    "NIFTY MS IT TELCOM": "ind_niftymidsmallitAndtelecom_list",
    "NIFTY CEMENT": "ind_NiftyCement_list",
    "NIFTY REITS REALTY": "ind_niftyREITsRealty_list",
    # Thematic
    "NIFTY COMMODITIES": "ind_niftycommoditieslist",
    "NIFTY CONSUMPTION": "ind_niftyconsumptionlist",
    "NIFTY CPSE": "ind_niftycpselist",
    "NIFTY ENERGY": "ind_niftyenergylist",
    "NIFTY INFRA": "ind_niftyinfralist",
    "NIFTY MNC": "ind_niftymnclist",
    "NIFTY PSE": "ind_niftypselist",
    "NIFTY SERV SECTOR": "ind_niftyservicelist",
    "NIFTY100 LIQ 15": "ind_Nifty100_Liquid15",
    "NIFTY MID LIQ 15": "ind_Nifty_Midcap_Liquid15",
    "NIFTY IND DIGITAL": "ind_niftyindiadigital_list",
    "NIFTY INDIA MFG": "ind_niftyindiamanufacturing_list",
    "NIFTY TATA 25 CAP": "ind_nifty_tata25caplist",
    "NIFTY MULTI MFG": "ind_nifty500MulticapIndiaManufacturing503020_list",
    "NIFTY MULTI INFRA": "ind_nifty500MulticapInfrastructure503020_list",
    "NIFTY INTERNET": "ind_niftyIndiaInternet_list",
    "NIFTY WAVES": "ind_niftyWaves_list",
    "NIFTY INFRALOG": "ind_niftyIndiaInfrastructure_Logistics_list",
    "NIFTY IND DEFENCE": "ind_niftyindiadefence_list",
    "NIFTY IND TOURISM": "ind_niftyindiatourism_list",
    "NIFTY CAPITAL GOODS": "ind_niftyCapitalGoods_list",
    "NIFTY NEW CONSUMPTION": "ind_niftyIndiaNewAgeConsumption_list",
    "NIFTY CORP MARKET": "ind_niftyCapitalMarkets_list",
    "NIFTY MOBILITY": "ind_niftymobility_list",
    "NIFTY COREHOUSING": "ind_niftyCoreHousing_list",
    "NIFTY HOUSING": "ind_niftyhousing_list",
    "NIFTY IPO": "ind_niftyIPO_list",
    "NIFTY MS IND CONS": "ind_niftymidsmallindiaconsumption_list",
    "NIFTY NONCYC CONS": "ind_niftynon-cyclicalconsumer_list",
    "NIFTY RURAL": "ind_niftyRural_list",
    "NIFTY TRANS LOGISTICS": "ind_niftytransportationandlogistics _list",
    "NIFTY RAILWAYS": "ind_niftyIndiaRailwaysPSU_list",
    "NIFTYCONGLOMERATES": "ind_niftyConglomerate50_list",
    # Strategy
    "NIFTY DIVIDEND OPP 50": "ind_niftydivopp50list",
    "NIFTY GROWTH SECTORS 15": "ind_NiftyGrowth_Sectors15_Index",
    "NIFTY HIGH BETA 50": "nifty_High_Beta50_Index",
    "NIFTY LOW VOLATILITY 50": "nifty_low_Volatility50_Index",
    "NIFTY QUALITY 30": "ind_nifty100Quality30list",
    "NIFTY ALPHA 50": "ind_nifty_Alpha_Index",
}
# Indices for which NSE publishes NO constituent CSV -> derived from parent index by
# documented methodology screens (see DERIVED below).
DERIVED = {
    "NIFTY SHARIAH 25": ("NIFTY 500", "shariah", 25),
    "NIFTY50 SHARIAH": ("NIFTY 50", "shariah", None),
    "NIFTY500 SHARIAH": ("NIFTY 500", "shariah", None),
    "NIFTY100 ESG": ("NIFTY 100", "esg", None),
    "NIFTY100 ENH ESG": ("NIFTY 100", "esg", None),
    "NIFTY EV": ("NIFTY 500", "ev", None),
}


# ==========================================================================
# from normalize.py
# ==========================================================================
# NSE publishes some constituent CSVs with stale rows. Normalize them against the
# live NSE equity master (EQUITY_L.csv) and the Dhan scrip master.
RENAMES = {
    "AMARAJABAT": "ARE&M",  # Amara Raja renamed to Amara Raja Energy & Mobility
    "MINDAIND": "UNOMINDA",  # Minda Industries renamed to UNO Minda
    "TATAMOTORS": "TMPV",  # demerger; TMPV carries the original ISIN INE155A01022
    "IBULHSGFIN": "SAMMAANCAP",  # Indiabulls Housing Finance renamed to Sammaan Capital
    "LTIM": "LTM",  # LTIMindtree renamed; NSE symbol is now LTM
    "MCDOWELL-N": "UNITDSPR",  # United Spirits symbol change
    "ZOMATO": "ETERNAL",  # Zomato renamed to Eternal
    "GMRINFRA": "GMRAIRPORT",  # GMR Infrastructure renamed to GMR Airports
    "BCON": "BIOCON",  # typo in the previous hand-maintained list
}
# Rows in official CSVs that are no longer tradable and have no successor symbol.
RETIRED = {
    "HDFC",  # merged into HDFCBANK
    "TATAMTRDVR",  # DVR class delisted
    "JBCHEPHARM",
    "SABEVENTS",
    "SABTNL",  # no longer in NSE's equity master
    "GUJGASLTD",  # merged
    "PEL",
    "DELTACORP",
}


def normalize(symbols):
    """Apply renames, drop NSE's DUMMY* placeholder rows and retired symbols."""
    out, seen = [], set()
    for s in symbols:
        if s.startswith("DUMMY") or s in RETIRED:
            continue
        s = RENAMES.get(s, s)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
