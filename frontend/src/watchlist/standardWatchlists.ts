import { Watchlist, WatchlistItem, WatchlistColumn } from "./types";
import { NSE_STOCK_BY_SYMBOL } from "./nseStockMaster";

export interface StandardWatchlistDefinition {
  id: string;
  name: string;
  category: "INDICES" | "F&O STOCKS";
  description: string;
  isGroupedBySector?: boolean;
  itemCount: number;
  columns?: WatchlistColumn[];
  getItems: () => WatchlistItem[];
}

export interface StockMasterEntry {
  symbol: string;
  tradingSymbol: string;
  securityId: string;
  name: string;
  sector: string;
  segment?: string;
  ltp: number;
  changePct: number;
  changeAbs?: number;
  volume?: number;
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
}

// ---------------------------------------------------------------------------
// NSE F&O Stock Master Catalog
//
// Membership: NSE's published derivatives market-lot file
//   https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv
// securityId: Dhan scrip master. name/sector: NSE equity master + index CSVs.
// ltp / changePct / 52-week values are placeholder quotes replaced by the live
// feed at runtime; only symbol, securityId, name and sector are reference data.
//
// Regenerate with: python scripts/fetch_nse_constituents.py
// ---------------------------------------------------------------------------
export const FNO_STOCKS: StockMasterEntry[] = [
  { symbol: "360ONE", tradingSymbol: "360ONE-EQ", securityId: "13061", name: "360 One WAM", sector: "Financial Services", ltp: 2455.5, changePct: -1.58, fiftyTwoWeekHigh: 3241.26, fiftyTwoWeekLow: 1767.96 },
  { symbol: "ABCAPITAL", tradingSymbol: "ABCAPITAL-EQ", securityId: "21614", name: "Aditya Birla Capital", sector: "Financial Services", ltp: 220.00, changePct: 1.20, fiftyTwoWeekHigh: 245.00, fiftyTwoWeekLow: 155.00 },
  { symbol: "ADANIENSOL", tradingSymbol: "ADANIENSOL-EQ", securityId: "10217", name: "Adani Energy Solutions", sector: "Power", ltp: 468.0, changePct: -1.9, fiftyTwoWeekHigh: 617.76, fiftyTwoWeekLow: 336.96 },
  { symbol: "ABB", tradingSymbol: "ABB-EQ", securityId: "13", name: "ABB", sector: "Capital Goods", ltp: 8100.00, changePct: 0.90, fiftyTwoWeekHigh: 9200.00, fiftyTwoWeekLow: 3900.00 },
  { symbol: "ADANIPORTS", tradingSymbol: "ADANIPORTS-EQ", securityId: "15083", name: "Adani Ports & SEZ", sector: "Services", ltp: 1450.00, changePct: 0.90, fiftyTwoWeekHigh: 1607.00, fiftyTwoWeekLow: 750.00 },
  { symbol: "AMBER", tradingSymbol: "AMBER-EQ", securityId: "1185", name: "Amber Enterprises", sector: "Consumer Durables", ltp: 643.0, changePct: 1.03, fiftyTwoWeekHigh: 848.76, fiftyTwoWeekLow: 462.96 },
  { symbol: "ASIANPAINT", tradingSymbol: "ASIANPAINT-EQ", securityId: "236", name: "Asian Paints", sector: "Consumer Durables", ltp: 3180.00, changePct: -0.30, fiftyTwoWeekHigh: 3422.00, fiftyTwoWeekLow: 2670.00 },
  { symbol: "AMBUJACEM", tradingSymbol: "AMBUJACEM-EQ", securityId: "1270", name: "Ambuja Cements", sector: "Construction Materials", ltp: 630.00, changePct: 0.50, fiftyTwoWeekHigh: 706.00, fiftyTwoWeekLow: 400.00 },
  { symbol: "ADANIENT", tradingSymbol: "ADANIENT-EQ", securityId: "25", name: "Adani Enterprises", sector: "Metals & Mining", ltp: 3020.00, changePct: -0.40, fiftyTwoWeekHigh: 3740.00, fiftyTwoWeekLow: 2100.00 },
  { symbol: "BAJAJ-AUTO", tradingSymbol: "BAJAJ-AUTO-EQ", securityId: "16669", name: "Bajaj Auto", sector: "Automobile and Auto Components", ltp: 10400.00, changePct: 1.15, fiftyTwoWeekHigh: 12200.00, fiftyTwoWeekLow: 4600.00 },
  { symbol: "BAJAJHLDNG", tradingSymbol: "BAJAJHLDNG-EQ", securityId: "305", name: "Bajaj Holdings & Investments", sector: "Financial Services", ltp: 1975.0, changePct: 1.61, fiftyTwoWeekHigh: 2607.0, fiftyTwoWeekLow: 1422.0 },
  { symbol: "APLAPOLLO", tradingSymbol: "APLAPOLLO-EQ", securityId: "25780", name: "APL Apollo Tubes", sector: "Capital Goods", ltp: 3765.5, changePct: 1.34, fiftyTwoWeekHigh: 4970.46, fiftyTwoWeekLow: 2711.16 },
  { symbol: "ADANIGREEN", tradingSymbol: "ADANIGREEN-EQ", securityId: "3563", name: "Adani Green Energy", sector: "Power", ltp: 1341.5, changePct: 2.73, fiftyTwoWeekHigh: 1770.78, fiftyTwoWeekLow: 965.88 },
  { symbol: "AUROPHARMA", tradingSymbol: "AUROPHARMA-EQ", securityId: "275", name: "Aurobindo Pharma", sector: "Healthcare", ltp: 1480.00, changePct: 0.60, fiftyTwoWeekHigh: 1600.00, fiftyTwoWeekLow: 810.00 },
  { symbol: "AXISBANK", tradingSymbol: "AXISBANK-EQ", securityId: "5900", name: "Axis Bank", sector: "Financial Services", ltp: 1180.00, changePct: 0.60, fiftyTwoWeekHigh: 1339.00, fiftyTwoWeekLow: 934.00 },
  { symbol: "BOSCHLTD", tradingSymbol: "BOSCHLTD-EQ", securityId: "2181", name: "Bosch", sector: "Automobile and Auto Components", ltp: 33500.00, changePct: 0.50, fiftyTwoWeekHigh: 38000.00, fiftyTwoWeekLow: 18500.00 },
  { symbol: "BRITANNIA", tradingSymbol: "BRITANNIA-EQ", securityId: "547", name: "Britannia Industries", sector: "Fast Moving Consumer Goods", ltp: 5800.00, changePct: 0.35, fiftyTwoWeekHigh: 6050.00, fiftyTwoWeekLow: 4400.00 },
  { symbol: "CDSL", tradingSymbol: "CDSL-EQ", securityId: "21174", name: "CDSL", sector: "Financial Services", ltp: 1420.00, changePct: 2.20, fiftyTwoWeekHigh: 1650.00, fiftyTwoWeekLow: 750.00 },
  { symbol: "BANDHANBNK", tradingSymbol: "BANDHANBNK-EQ", securityId: "2263", name: "Bandhan Bank", sector: "Financial Services", ltp: 198.50, changePct: 1.10, fiftyTwoWeekHigh: 263.00, fiftyTwoWeekLow: 168.00 },
  { symbol: "BANKBARODA", tradingSymbol: "BANKBARODA-EQ", securityId: "4668", name: "Bank of Baroda", sector: "Financial Services", ltp: 245.50, changePct: 0.90, fiftyTwoWeekHigh: 298.00, fiftyTwoWeekLow: 188.00 },
  { symbol: "BDL", tradingSymbol: "BDL-EQ", securityId: "2144", name: "Bharat Dynamics", sector: "Capital Goods", ltp: 241.5, changePct: -0.62, fiftyTwoWeekHigh: 318.78, fiftyTwoWeekLow: 173.88 },
  { symbol: "BHARATFORG", tradingSymbol: "BHARATFORG-EQ", securityId: "422", name: "Bharat Forge", sector: "Automobile and Auto Components", ltp: 1520.00, changePct: 0.60, fiftyTwoWeekHigh: 1720.00, fiftyTwoWeekLow: 980.00 },
  { symbol: "COALINDIA", tradingSymbol: "COALINDIA-EQ", securityId: "20374", name: "Coal India", sector: "Oil Gas & Consumable Fuels", ltp: 495.35, changePct: -1.12, fiftyTwoWeekHigh: 543.00, fiftyTwoWeekLow: 260.00 },
  { symbol: "BHARTIARTL", tradingSymbol: "BHARTIARTL-EQ", securityId: "10604", name: "Bharti Airtel", sector: "Telecommunication", ltp: 1620.00, changePct: 0.50, fiftyTwoWeekHigh: 1680.00, fiftyTwoWeekLow: 890.00 },
  { symbol: "BLUESTARCO", tradingSymbol: "BLUESTARCO-EQ", securityId: "8311", name: "Blue Star", sector: "Consumer Durables", ltp: 758.5, changePct: -0.54, fiftyTwoWeekHigh: 1001.22, fiftyTwoWeekLow: 546.12 },
  { symbol: "BPCL", tradingSymbol: "BPCL-EQ", securityId: "526", name: "Bharat Petroleum", sector: "Oil Gas & Consumable Fuels", ltp: 350.00, changePct: -0.60, fiftyTwoWeekHigh: 395.00, fiftyTwoWeekLow: 170.00 },
  { symbol: "ALKEM", tradingSymbol: "ALKEM-EQ", securityId: "11703", name: "Alkem Laboratories", sector: "Healthcare", ltp: 5800.00, changePct: 0.20, fiftyTwoWeekHigh: 6250.00, fiftyTwoWeekLow: 3500.00 },
  { symbol: "CAMS", tradingSymbol: "CAMS-EQ", securityId: "342", name: "CAMS", sector: "Financial Services", ltp: 4480.00, changePct: 0.19, fiftyTwoWeekHigh: 4750.00, fiftyTwoWeekLow: 2300.00 },
  { symbol: "CHOLAFIN", tradingSymbol: "CHOLAFIN-EQ", securityId: "19257", name: "CIFCL-7.5%-30092026-NCD", sector: "Financial Services", ltp: 1480.00, changePct: 1.80, fiftyTwoWeekHigh: 1620.00, fiftyTwoWeekLow: 1060.00 },
  { symbol: "CIPLA", tradingSymbol: "CIPLA-EQ", securityId: "694", name: "Cipla", sector: "Healthcare", ltp: 1585.00, changePct: -0.70, fiftyTwoWeekHigh: 1700.00, fiftyTwoWeekLow: 1130.00 },
  { symbol: "COCHINSHIP", tradingSymbol: "COCHINSHIP-EQ", securityId: "21508", name: "Cochin Shipyard", sector: "Capital Goods", ltp: 2508.5, changePct: -1.37, fiftyTwoWeekHigh: 3311.22, fiftyTwoWeekLow: 1806.12 },
  { symbol: "COLPAL", tradingSymbol: "COLPAL-EQ", securityId: "15141", name: "Colgate Palmolive", sector: "Fast Moving Consumer Goods", ltp: 3550.00, changePct: 0.50, fiftyTwoWeekHigh: 3880.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "COFORGE", tradingSymbol: "COFORGE-EQ", securityId: "11543", name: "Coforge", sector: "Information Technology", ltp: 6750.00, changePct: 0.85, fiftyTwoWeekHigh: 7200.00, fiftyTwoWeekLow: 4300.00 },
  { symbol: "CROMPTON", tradingSymbol: "CROMPTON-EQ", securityId: "17094", name: "Crompton Greaves", sector: "Consumer Durables", ltp: 440.00, changePct: 0.50, fiftyTwoWeekHigh: 480.00, fiftyTwoWeekLow: 260.00 },
  { symbol: "CONCOR", tradingSymbol: "CONCOR-EQ", securityId: "4749", name: "Container Corporation of India", sector: "Services", ltp: 940.00, changePct: 0.30, fiftyTwoWeekHigh: 1180.00, fiftyTwoWeekLow: 670.00 },
  { symbol: "DABUR", tradingSymbol: "DABUR-EQ", securityId: "772", name: "Dabur India", sector: "Fast Moving Consumer Goods", ltp: 640.00, changePct: 0.40, fiftyTwoWeekHigh: 672.00, fiftyTwoWeekLow: 489.00 },
  { symbol: "ANGELONE", tradingSymbol: "ANGELONE-EQ", securityId: "324", name: "Angel One", sector: "Financial Services", ltp: 2750.00, changePct: 1.40, fiftyTwoWeekHigh: 3899.00, fiftyTwoWeekLow: 2120.00 },
  { symbol: "APOLLOHOSP", tradingSymbol: "APOLLOHOSP-EQ", securityId: "157", name: "Apollo Hospitals", sector: "Healthcare", ltp: 7150.00, changePct: 0.90, fiftyTwoWeekHigh: 7500.00, fiftyTwoWeekLow: 4700.00 },
  { symbol: "DELHIVERY", tradingSymbol: "DELHIVERY-EQ", securityId: "9599", name: "Delhivery", sector: "Services", ltp: 420.00, changePct: 0.65, fiftyTwoWeekHigh: 488.00, fiftyTwoWeekLow: 340.00 },
  { symbol: "DIVISLAB", tradingSymbol: "DIVISLAB-EQ", securityId: "10940", name: "Divis Laboratories", sector: "Healthcare", ltp: 5400.00, changePct: 1.20, fiftyTwoWeekHigh: 5750.00, fiftyTwoWeekLow: 3350.00 },
  { symbol: "DLF", tradingSymbol: "DLF-EQ", securityId: "14732", name: "DLF", sector: "Realty", ltp: 860.00, changePct: 1.10, fiftyTwoWeekHigh: 960.00, fiftyTwoWeekLow: 480.00 },
  { symbol: "DMART", tradingSymbol: "DMART-EQ", securityId: "19913", name: "Avenue Supermarts DMart", sector: "Consumer Services", ltp: 1866.0, changePct: 2.67, fiftyTwoWeekHigh: 2463.12, fiftyTwoWeekLow: 1343.52 },
  { symbol: "DRREDDY", tradingSymbol: "DRREDDY-EQ", securityId: "881", name: "Dr Reddys Laboratories", sector: "Healthcare", ltp: 6600.00, changePct: 0.85, fiftyTwoWeekHigh: 7100.00, fiftyTwoWeekLow: 5200.00 },
  { symbol: "DIXON", tradingSymbol: "DIXON-EQ", securityId: "21690", name: "Dixon Technologies", sector: "Consumer Durables", ltp: 12800.00, changePct: 2.10, fiftyTwoWeekHigh: 14500.00, fiftyTwoWeekLow: 4800.00 },
  { symbol: "ETERNAL", tradingSymbol: "ETERNAL-EQ", securityId: "5097", name: "Eternal", sector: "Consumer Services", ltp: 255.00, changePct: 2.30, fiftyTwoWeekHigh: 280.00, fiftyTwoWeekLow: 95.00 },
  { symbol: "FORCEMOT", tradingSymbol: "FORCEMOT-EQ", securityId: "11573", name: "Force Motors", sector: "Automobile and Auto Components", ltp: 2263.0, changePct: -2.43, fiftyTwoWeekHigh: 2987.16, fiftyTwoWeekLow: 1629.36 },
  { symbol: "FORTIS", tradingSymbol: "FORTIS-EQ", securityId: "14592", name: "Fortis Healthcare", sector: "Healthcare", ltp: 3368.5, changePct: -0.57, fiftyTwoWeekHigh: 4446.42, fiftyTwoWeekLow: 2425.32 },
  { symbol: "GLENMARK", tradingSymbol: "GLENMARK-EQ", securityId: "7406", name: "Glenmark Pharmaceuticals", sector: "Healthcare", ltp: 1650.00, changePct: 0.80, fiftyTwoWeekHigh: 1820.00, fiftyTwoWeekLow: 710.00 },
  { symbol: "GODFRYPHLP", tradingSymbol: "GODFRYPHLP-EQ", securityId: "1181", name: "Godfrey Phillips", sector: "Fast Moving Consumer Goods", ltp: 6850.00, changePct: 0.29, fiftyTwoWeekHigh: 7600.00, fiftyTwoWeekLow: 2050.00 },
  { symbol: "BANKINDIA", tradingSymbol: "BANKINDIA-EQ", securityId: "4745", name: "Bank of India", sector: "Financial Services", ltp: 1953.0, changePct: -3.06, fiftyTwoWeekHigh: 2577.96, fiftyTwoWeekLow: 1406.16 },
  { symbol: "GODREJPROP", tradingSymbol: "GODREJPROP-EQ", securityId: "17875", name: "Godrej Properties", sector: "Realty", ltp: 3100.00, changePct: 1.80, fiftyTwoWeekHigh: 3400.00, fiftyTwoWeekLow: 1550.00 },
  { symbol: "GODREJCP", tradingSymbol: "GODREJCP-EQ", securityId: "10099", name: "Godrej Consumer Products", sector: "Fast Moving Consumer Goods", ltp: 1450.00, changePct: 0.60, fiftyTwoWeekHigh: 1540.00, fiftyTwoWeekLow: 970.00 },
  { symbol: "HCLTECH", tradingSymbol: "HCLTECH-EQ", securityId: "7229", name: "HCL Technologies", sector: "Information Technology", ltp: 1780.00, changePct: -0.90, fiftyTwoWeekHigh: 1890.00, fiftyTwoWeekLow: 1190.00 },
  { symbol: "HDFCBANK", tradingSymbol: "HDFCBANK-EQ", securityId: "1333", name: "HDFC Bank", sector: "Financial Services", ltp: 1640.20, changePct: 0.80, fiftyTwoWeekHigh: 1794.00, fiftyTwoWeekLow: 1363.55 },
  { symbol: "GRASIM", tradingSymbol: "GRASIM-EQ", securityId: "1232", name: "Grasim Industries", sector: "Construction Materials", ltp: 2650.00, changePct: -0.20, fiftyTwoWeekHigh: 2880.00, fiftyTwoWeekLow: 1850.00 },
  { symbol: "GVT&D", tradingSymbol: "GVT&D-EQ", securityId: "16783", name: "GE Vernova T&D", sector: "Capital Goods", ltp: 3296.0, changePct: -0.85, fiftyTwoWeekHigh: 4350.72, fiftyTwoWeekLow: 2373.12 },
  { symbol: "HAVELLS", tradingSymbol: "HAVELLS-EQ", securityId: "9819", name: "Havells", sector: "Consumer Durables", ltp: 1980.00, changePct: 0.60, fiftyTwoWeekHigh: 2100.00, fiftyTwoWeekLow: 1250.00 },
  { symbol: "HDFCLIFE", tradingSymbol: "HDFCLIFE-EQ", securityId: "467", name: "HDFC Life Insurance", sector: "Financial Services", ltp: 710.00, changePct: 0.15, fiftyTwoWeekHigh: 760.00, fiftyTwoWeekLow: 570.00 },
  { symbol: "BEL", tradingSymbol: "BEL-EQ", securityId: "383", name: "Bharat Electronics", sector: "Capital Goods", ltp: 305.00, changePct: 1.80, fiftyTwoWeekHigh: 340.00, fiftyTwoWeekLow: 125.00 },
  { symbol: "BHEL", tradingSymbol: "BHEL-EQ", securityId: "438", name: "Bharat Heavy Electricals", sector: "Capital Goods", ltp: 275.00, changePct: 1.40, fiftyTwoWeekHigh: 335.00, fiftyTwoWeekLow: 98.00 },
  { symbol: "HINDALCO", tradingSymbol: "HINDALCO-EQ", securityId: "1363", name: "Hindalco Industries", sector: "Metals & Mining", ltp: 670.00, changePct: 1.10, fiftyTwoWeekHigh: 715.00, fiftyTwoWeekLow: 448.00 },
  { symbol: "BIOCON", tradingSymbol: "BIOCON-EQ", securityId: "11373", name: "Biocon", sector: "Healthcare", ltp: 360.00, changePct: 1.10, fiftyTwoWeekHigh: 395.00, fiftyTwoWeekLow: 220.00 },
  { symbol: "HINDUNILVR", tradingSymbol: "HINDUNILVR-EQ", securityId: "1394", name: "Hindustan Unilever", sector: "Fast Moving Consumer Goods", ltp: 2780.00, changePct: -0.45, fiftyTwoWeekHigh: 3034.00, fiftyTwoWeekLow: 2170.00 },
  { symbol: "HINDZINC", tradingSymbol: "HINDZINC-EQ", securityId: "1424", name: "Hindustan Zinc", sector: "Metals & Mining", ltp: 2426.0, changePct: 3.3, fiftyTwoWeekHigh: 3202.32, fiftyTwoWeekLow: 1746.72 },
  { symbol: "IDFCFIRSTB", tradingSymbol: "IDFCFIRSTB-EQ", securityId: "11184", name: "IDFC First Bank", sector: "Financial Services", ltp: 72.80, changePct: -0.20, fiftyTwoWeekHigh: 95.70, fiftyTwoWeekLow: 70.10 },
  { symbol: "INDUSINDBK", tradingSymbol: "INDUSINDBK-EQ", securityId: "5258", name: "Indusind Bank", sector: "Financial Services", ltp: 1420.00, changePct: -0.80, fiftyTwoWeekHigh: 1694.00, fiftyTwoWeekLow: 1332.00 },
  { symbol: "ICICIGI", tradingSymbol: "ICICIGI-EQ", securityId: "21770", name: "ICICI Lombard General Insurance", sector: "Financial Services", ltp: 2050.00, changePct: 0.60, fiftyTwoWeekHigh: 2220.00, fiftyTwoWeekLow: 1300.00 },
  { symbol: "CGPOWER", tradingSymbol: "CGPOWER-EQ", securityId: "760", name: "CG Power & Industrial Solutions", sector: "Capital Goods", ltp: 3070.5, changePct: 1.41, fiftyTwoWeekHigh: 4053.06, fiftyTwoWeekLow: 2210.76 },
  { symbol: "IRFC", tradingSymbol: "IRFC-EQ", securityId: "2029", name: "IRFC", sector: "Financial Services", ltp: 168.00, changePct: 2.10, fiftyTwoWeekHigh: 229.00, fiftyTwoWeekLow: 65.00 },
  { symbol: "JINDALSTEL", tradingSymbol: "JINDALSTEL-EQ", securityId: "6733", name: "Jindal Steel", sector: "Metals & Mining", ltp: 980.00, changePct: 1.20, fiftyTwoWeekHigh: 1080.00, fiftyTwoWeekLow: 580.00 },
  { symbol: "JIOFIN", tradingSymbol: "JIOFIN-EQ", securityId: "18143", name: "Jio Financial Services", sector: "Financial Services", ltp: 335.00, changePct: 0.80, fiftyTwoWeekHigh: 395.00, fiftyTwoWeekLow: 205.00 },
  { symbol: "IEX", tradingSymbol: "IEX-EQ", securityId: "220", name: "Indian Energy Exchange", sector: "Financial Services", ltp: 195.00, changePct: 1.30, fiftyTwoWeekHigh: 215.00, fiftyTwoWeekLow: 125.00 },
  { symbol: "INDHOTEL", tradingSymbol: "INDHOTEL-EQ", securityId: "1512", name: "Indian Hotels Company", sector: "Consumer Services", ltp: 690.00, changePct: 1.20, fiftyTwoWeekHigh: 740.00, fiftyTwoWeekLow: 380.00 },
  { symbol: "INDIANB", tradingSymbol: "INDIANB-EQ", securityId: "14309", name: "Indian Bank", sector: "Financial Services", ltp: 2190.5, changePct: -2.71, fiftyTwoWeekHigh: 2891.46, fiftyTwoWeekLow: 1577.16 },
  { symbol: "JSWENERGY", tradingSymbol: "JSWENERGY-EQ", securityId: "17869", name: "JSW Energy", sector: "Power", ltp: 3191.5, changePct: -3.25, fiftyTwoWeekHigh: 4212.78, fiftyTwoWeekLow: 2297.88 },
  { symbol: "JSWSTEEL", tradingSymbol: "JSWSTEEL-EQ", securityId: "11723", name: "JSW Steel", sector: "Metals & Mining", ltp: 940.00, changePct: 0.50, fiftyTwoWeekHigh: 1040.00, fiftyTwoWeekLow: 730.00 },
  { symbol: "KAYNES", tradingSymbol: "KAYNES-EQ", securityId: "12092", name: "Kaynes Technology India", sector: "Capital Goods", ltp: 4950.00, changePct: 1.60, fiftyTwoWeekHigh: 5400.00, fiftyTwoWeekLow: 2100.00 },
  { symbol: "KEI", tradingSymbol: "KEI-EQ", securityId: "13310", name: "KEI Industries", sector: "Capital Goods", ltp: 1935.5, changePct: -0.18, fiftyTwoWeekHigh: 2554.86, fiftyTwoWeekLow: 1393.56 },
  { symbol: "INFY", tradingSymbol: "INFY-EQ", securityId: "1594", name: "Infosys", sector: "Information Technology", ltp: 1890.10, changePct: -1.10, fiftyTwoWeekHigh: 1991.45, fiftyTwoWeekLow: 1358.35 },
  { symbol: "INOXWIND", tradingSymbol: "INOXWIND-EQ", securityId: "7852", name: "Inox Wind", sector: "Capital Goods", ltp: 1514.0, changePct: -1.34, fiftyTwoWeekHigh: 1998.48, fiftyTwoWeekLow: 1090.08 },
  { symbol: "ITC", tradingSymbol: "ITC-EQ", securityId: "1660", name: "ITC", sector: "Fast Moving Consumer Goods", ltp: 495.00, changePct: -0.20, fiftyTwoWeekHigh: 528.00, fiftyTwoWeekLow: 399.00 },
  { symbol: "KPITTECH", tradingSymbol: "KPITTECH-EQ", securityId: "9683", name: "KPIT Technologies", sector: "Information Technology", ltp: 1680.00, changePct: 1.10, fiftyTwoWeekHigh: 1920.00, fiftyTwoWeekLow: 1100.00 },
  { symbol: "JUBLFOOD", tradingSymbol: "JUBLFOOD-EQ", securityId: "18096", name: "Jubilant FoodWorks", sector: "Consumer Services", ltp: 650.00, changePct: 0.80, fiftyTwoWeekHigh: 710.00, fiftyTwoWeekLow: 420.00 },
  { symbol: "LT", tradingSymbol: "LT-EQ", securityId: "11483", name: "Larsen & Toubro", sector: "Construction", ltp: 3620.00, changePct: 1.80, fiftyTwoWeekHigh: 3919.00, fiftyTwoWeekLow: 2850.00 },
  { symbol: "M&M", tradingSymbol: "M&M-EQ", securityId: "2031", name: "Mahindra & Mahindra", sector: "Automobile and Auto Components", ltp: 2850.00, changePct: 1.70, fiftyTwoWeekHigh: 3014.00, fiftyTwoWeekLow: 1450.00 },
  { symbol: "KALYANKJIL", tradingSymbol: "KALYANKJIL-EQ", securityId: "2955", name: "Kalyan Jewellers", sector: "Consumer Durables", ltp: 710.00, changePct: 2.45, fiftyTwoWeekHigh: 795.00, fiftyTwoWeekLow: 215.00 },
  { symbol: "MANKIND", tradingSymbol: "MANKIND-EQ", securityId: "15380", name: "Mankind Pharma", sector: "Healthcare", ltp: 2943.0, changePct: -1.23, fiftyTwoWeekHigh: 3884.76, fiftyTwoWeekLow: 2118.96 },
  { symbol: "MARICO", tradingSymbol: "MARICO-EQ", securityId: "4067", name: "Marico", sector: "Fast Moving Consumer Goods", ltp: 650.00, changePct: 0.30, fiftyTwoWeekHigh: 690.00, fiftyTwoWeekLow: 485.00 },
  { symbol: "ADANIPOWER", tradingSymbol: "ADANIPOWER-EQ", securityId: "17388", name: "Adani Power", sector: "Power", ltp: 1182.0, changePct: -0.43, fiftyTwoWeekHigh: 1560.24, fiftyTwoWeekLow: 851.04 },
  { symbol: "MCX", tradingSymbol: "MCX-EQ", securityId: "31181", name: "MCX", sector: "Financial Services", ltp: 5600.00, changePct: 2.40, fiftyTwoWeekHigh: 6200.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "NAM-INDIA", tradingSymbol: "NAM-INDIA-EQ", securityId: "357", name: "Nippon Life India AMC", sector: "Financial Services", ltp: 3181.5, changePct: 1.7, fiftyTwoWeekHigh: 4199.58, fiftyTwoWeekLow: 2290.68 },
  { symbol: "KFINTECH", tradingSymbol: "KFINTECH-EQ", securityId: "13359", name: "KFin Technologies", sector: "Financial Services", ltp: 2174.0, changePct: 1.95, fiftyTwoWeekHigh: 2869.68, fiftyTwoWeekLow: 1565.28 },
  { symbol: "NESTLEIND", tradingSymbol: "NESTLEIND-EQ", securityId: "17963", name: "Nestle", sector: "Fast Moving Consumer Goods", ltp: 2500.00, changePct: -0.10, fiftyTwoWeekHigh: 2770.00, fiftyTwoWeekLow: 2140.00 },
  { symbol: "EICHERMOT", tradingSymbol: "EICHERMOT-EQ", securityId: "910", name: "Eicher Motors", sector: "Automobile and Auto Components", ltp: 4900.00, changePct: 1.40, fiftyTwoWeekHigh: 5100.00, fiftyTwoWeekLow: 3160.00 },
  { symbol: "LODHA", tradingSymbol: "LODHA-EQ", securityId: "3220", name: "Lodha Developers", sector: "Realty", ltp: 3672.0, changePct: 0.57, fiftyTwoWeekHigh: 4847.04, fiftyTwoWeekLow: 2643.84 },
  { symbol: "FEDERALBNK", tradingSymbol: "FEDERALBNK-EQ", securityId: "1023", name: "Federal Bank", sector: "Financial Services", ltp: 192.80, changePct: 0.35, fiftyTwoWeekHigh: 210.00, fiftyTwoWeekLow: 135.00 },
  { symbol: "OBEROIRLTY", tradingSymbol: "OBEROIRLTY-EQ", securityId: "20242", name: "Oberoi Realty", sector: "Realty", ltp: 1850.00, changePct: 1.40, fiftyTwoWeekHigh: 2050.00, fiftyTwoWeekLow: 1050.00 },
  { symbol: "LTM", tradingSymbol: "LTM-EQ", securityId: "17818", name: "LTM", sector: "Information Technology", ltp: 6100.00, changePct: 0.70, fiftyTwoWeekHigh: 6440.00, fiftyTwoWeekLow: 4500.00 },
  { symbol: "LUPIN", tradingSymbol: "LUPIN-EQ", securityId: "10440", name: "Lupin", sector: "Healthcare", ltp: 2150.00, changePct: 1.40, fiftyTwoWeekHigh: 2320.00, fiftyTwoWeekLow: 1100.00 },
  { symbol: "PAGEIND", tradingSymbol: "PAGEIND-EQ", securityId: "14413", name: "Page Industries", sector: "Textiles", ltp: 42000.00, changePct: 0.20, fiftyTwoWeekHigh: 45000.00, fiftyTwoWeekLow: 33000.00 },
  { symbol: "MANAPPURAM", tradingSymbol: "MANAPPURAM-EQ", securityId: "19061", name: "Manappuram Finance", sector: "Financial Services", ltp: 198.70, changePct: -0.38, fiftyTwoWeekHigh: 230.00, fiftyTwoWeekLow: 150.00 },
  { symbol: "PAYTM", tradingSymbol: "PAYTM-EQ", securityId: "6705", name: "One 97 Communications", sector: "Financial Services", ltp: 645.00, changePct: -1.20, fiftyTwoWeekHigh: 998.00, fiftyTwoWeekLow: 310.00 },
  { symbol: "PFC", tradingSymbol: "PFC-EQ", securityId: "14299", name: "Power Finance Corporation", sector: "Financial Services", ltp: 495.00, changePct: 1.60, fiftyTwoWeekHigh: 580.00, fiftyTwoWeekLow: 205.00 },
  { symbol: "PGEL", tradingSymbol: "PGEL-EQ", securityId: "25358", name: "PG Electroplast", sector: "Consumer Durables", ltp: 1809.0, changePct: 0.56, fiftyTwoWeekHigh: 2387.88, fiftyTwoWeekLow: 1302.48 },
  { symbol: "MARUTI", tradingSymbol: "MARUTI-EQ", securityId: "10999", name: "Maruti Suzuki", sector: "Automobile and Auto Components", ltp: 12400.00, changePct: 0.90, fiftyTwoWeekHigh: 13680.00, fiftyTwoWeekLow: 9250.00 },
  { symbol: "MAXHEALTH", tradingSymbol: "MAXHEALTH-EQ", securityId: "22377", name: "Max Healthcare Institute", sector: "Healthcare", ltp: 940.00, changePct: 1.20, fiftyTwoWeekHigh: 1040.00, fiftyTwoWeekLow: 540.00 },
  { symbol: "PHOENIXLTD", tradingSymbol: "PHOENIXLTD-EQ", securityId: "14552", name: "Phoenix Mills", sector: "Realty", ltp: 1820.00, changePct: 0.90, fiftyTwoWeekHigh: 2100.00, fiftyTwoWeekLow: 850.00 },
  { symbol: "PNB", tradingSymbol: "PNB-EQ", securityId: "10666", name: "Punjab National Bank", sector: "Financial Services", ltp: 112.40, changePct: 1.40, fiftyTwoWeekHigh: 142.90, fiftyTwoWeekLow: 68.00 },
  { symbol: "MOTHERSON", tradingSymbol: "MOTHERSON-EQ", securityId: "25510", name: "SMIL-6.5%-20092027-NCD", sector: "Automobile and Auto Components", ltp: 185.00, changePct: 1.30, fiftyTwoWeekHigh: 215.00, fiftyTwoWeekLow: 85.00 },
  { symbol: "POLYCAB", tradingSymbol: "POLYCAB-EQ", securityId: "9590", name: "Polycab", sector: "Capital Goods", ltp: 6800.00, changePct: 1.20, fiftyTwoWeekHigh: 7300.00, fiftyTwoWeekLow: 3800.00 },
  { symbol: "POWERINDIA", tradingSymbol: "POWERINDIA-EQ", securityId: "18457", name: "Hitachi Energy", sector: "Capital Goods", ltp: 4190.0, changePct: -2.18, fiftyTwoWeekHigh: 5530.8, fiftyTwoWeekLow: 3016.8 },
  { symbol: "NMDC", tradingSymbol: "NMDC-EQ", securityId: "15332", name: "NMDC", sector: "Metals & Mining", ltp: 225.00, changePct: 0.70, fiftyTwoWeekHigh: 286.00, fiftyTwoWeekLow: 130.00 },
  { symbol: "OFSS", tradingSymbol: "OFSS-EQ", securityId: "10738", name: "Oracle Financial Services Software", sector: "Information Technology", ltp: 11200.00, changePct: 1.90, fiftyTwoWeekHigh: 12500.00, fiftyTwoWeekLow: 3900.00 },
  { symbol: "PRESTIGE", tradingSymbol: "PRESTIGE-EQ", securityId: "20302", name: "Prestige Estates Projects", sector: "Realty", ltp: 1750.00, changePct: 1.50, fiftyTwoWeekHigh: 2070.00, fiftyTwoWeekLow: 600.00 },
  { symbol: "OIL", tradingSymbol: "OIL-EQ", securityId: "17438", name: "Oil India", sector: "Oil Gas & Consumable Fuels", ltp: 339.5, changePct: 0.69, fiftyTwoWeekHigh: 448.14, fiftyTwoWeekLow: 244.44 },
  { symbol: "ONGC", tradingSymbol: "ONGC-EQ", securityId: "2475", name: "Oil & Natural Gas Corporation", sector: "Oil Gas & Consumable Fuels", ltp: 320.00, changePct: 0.40, fiftyTwoWeekHigh: 344.00, fiftyTwoWeekLow: 175.00 },
  { symbol: "PATANJALI", tradingSymbol: "PATANJALI-EQ", securityId: "17029", name: "Patanjali Foods", sector: "Fast Moving Consumer Goods", ltp: 3869.0, changePct: -1.24, fiftyTwoWeekHigh: 5107.08, fiftyTwoWeekLow: 2785.68 },
  { symbol: "RECLTD", tradingSymbol: "RECLTD-EQ", securityId: "15355", name: "REC", sector: "Financial Services", ltp: 560.00, changePct: 1.90, fiftyTwoWeekHigh: 654.00, fiftyTwoWeekLow: 220.00 },
  { symbol: "SBILIFE", tradingSymbol: "SBILIFE-EQ", securityId: "21808", name: "SBI Life Insurance", sector: "Financial Services", ltp: 1780.00, changePct: -0.25, fiftyTwoWeekHigh: 1890.00, fiftyTwoWeekLow: 1260.00 },
  { symbol: "GMRAIRPORT", tradingSymbol: "GMRAIRPORT-EQ", securityId: "13528", name: "GMR Airports", sector: "Services", ltp: 94.00, changePct: 0.50, fiftyTwoWeekHigh: 108.00, fiftyTwoWeekLow: 55.00 },
  { symbol: "SBIN", tradingSymbol: "SBIN-EQ", securityId: "3045", name: "State Bank of India", sector: "Financial Services", ltp: 815.40, changePct: 1.15, fiftyTwoWeekHigh: 912.00, fiftyTwoWeekLow: 555.00 },
  { symbol: "SHREECEM", tradingSymbol: "SHREECEM-EQ", securityId: "3103", name: "Shree Cement", sector: "Construction Materials", ltp: 24500.00, changePct: -0.10, fiftyTwoWeekHigh: 30800.00, fiftyTwoWeekLow: 23500.00 },
  { symbol: "TATACONSUM", tradingSymbol: "TATACONSUM-EQ", securityId: "3432", name: "Tata Consumer Products", sector: "Fast Moving Consumer Goods", ltp: 1180.00, changePct: 0.10, fiftyTwoWeekHigh: 1269.00, fiftyTwoWeekLow: 830.00 },
  { symbol: "PETRONET", tradingSymbol: "PETRONET-EQ", securityId: "11351", name: "Petronet LNG", sector: "Oil Gas & Consumable Fuels", ltp: 355.00, changePct: 0.20, fiftyTwoWeekHigh: 385.00, fiftyTwoWeekLow: 190.00 },
  { symbol: "TATAELXSI", tradingSymbol: "TATAELXSI-EQ", securityId: "3411", name: "Tata Elxsi", sector: "Information Technology", ltp: 7650.00, changePct: 0.40, fiftyTwoWeekHigh: 9200.00, fiftyTwoWeekLow: 6400.00 },
  { symbol: "TATASTEEL", tradingSymbol: "TATASTEEL-EQ", securityId: "3499", name: "Tata Steel", sector: "Metals & Mining", ltp: 154.80, changePct: 0.40, fiftyTwoWeekHigh: 184.60, fiftyTwoWeekLow: 114.60 },
  { symbol: "TMPV", tradingSymbol: "TMPV-EQ", securityId: "3456", name: "Tata Motors Passenger Vehicles", sector: "Automobile and Auto Components", ltp: 980.00, changePct: 2.10, fiftyTwoWeekHigh: 1179.00, fiftyTwoWeekLow: 600.00 },
  { symbol: "UPL", tradingSymbol: "UPL-EQ", securityId: "11287", name: "UPL", sector: "Chemicals", ltp: 580.00, changePct: 0.70, fiftyTwoWeekHigh: 635.00, fiftyTwoWeekLow: 450.00 },
  { symbol: "PIDILITIND", tradingSymbol: "PIDILITIND-EQ", securityId: "2664", name: "Pidilite Industries", sector: "Chemicals", ltp: 3150.00, changePct: -0.30, fiftyTwoWeekHigh: 3350.00, fiftyTwoWeekLow: 2280.00 },
  { symbol: "WAAREEENER", tradingSymbol: "WAAREEENER-EQ", securityId: "25907", name: "Waaree Energies", sector: "Capital Goods", ltp: 986.0, changePct: -3.05, fiftyTwoWeekHigh: 1301.52, fiftyTwoWeekLow: 709.92 },
  { symbol: "PIIND", tradingSymbol: "PIIND-EQ", securityId: "24184", name: "PI Industries", sector: "Chemicals", ltp: 4450.00, changePct: 0.50, fiftyTwoWeekHigh: 4680.00, fiftyTwoWeekLow: 3300.00 },
  { symbol: "BAJAJFINSV", tradingSymbol: "BAJAJFINSV-EQ", securityId: "16675", name: "Bajaj Finserv", sector: "Financial Services", ltp: 1720.00, changePct: 0.25, fiftyTwoWeekHigh: 1910.00, fiftyTwoWeekLow: 1419.00 },
  { symbol: "POLICYBZR", tradingSymbol: "POLICYBZR-EQ", securityId: "6656", name: "PB FinTech", sector: "Financial Services", ltp: 1780.00, changePct: 1.85, fiftyTwoWeekHigh: 1950.00, fiftyTwoWeekLow: 680.00 },
  { symbol: "PREMIERENE", tradingSymbol: "PREMIERENE-EQ", securityId: "25049", name: "Premier Energies", sector: "Capital Goods", ltp: 4190.0, changePct: -2.18, fiftyTwoWeekHigh: 5530.8, fiftyTwoWeekLow: 3016.8 },
  { symbol: "RADICO", tradingSymbol: "RADICO-EQ", securityId: "10990", name: "Radico Khaitan", sector: "Fast Moving Consumer Goods", ltp: 3797.5, changePct: 2.66, fiftyTwoWeekHigh: 5012.7, fiftyTwoWeekLow: 2734.2 },
  { symbol: "RBLBANK", tradingSymbol: "RBLBANK-EQ", securityId: "18391", name: "RBL Bank", sector: "Financial Services", ltp: 215.00, changePct: -0.90, fiftyTwoWeekHigh: 300.00, fiftyTwoWeekLow: 192.00 },
  { symbol: "SAIL", tradingSymbol: "SAIL-EQ", securityId: "2963", name: "Steel Authority of India", sector: "Metals & Mining", ltp: 132.00, changePct: 0.80, fiftyTwoWeekHigh: 175.00, fiftyTwoWeekLow: 82.00 },
  { symbol: "SOLARINDS", tradingSymbol: "SOLARINDS-EQ", securityId: "13332", name: "Solar Industries", sector: "Chemicals", ltp: 582.5, changePct: 1.76, fiftyTwoWeekHigh: 768.9, fiftyTwoWeekLow: 419.4 },
  { symbol: "SUNPHARMA", tradingSymbol: "SUNPHARMA-EQ", securityId: "3351", name: "Sun Pharmaceutical", sector: "Healthcare", ltp: 1850.00, changePct: 1.05, fiftyTwoWeekHigh: 1960.00, fiftyTwoWeekLow: 1090.00 },
  { symbol: "SUPREMEIND", tradingSymbol: "SUPREMEIND-EQ", securityId: "3363", name: "Supreme Industries", sector: "Capital Goods", ltp: 3749.0, changePct: -1.01, fiftyTwoWeekHigh: 4948.68, fiftyTwoWeekLow: 2699.28 },
  { symbol: "SUZLON", tradingSymbol: "SUZLON-EQ", securityId: "12018", name: "Suzlon Energy", sector: "Capital Goods", ltp: 78.00, changePct: 2.50, fiftyTwoWeekHigh: 86.00, fiftyTwoWeekLow: 21.00 },
  { symbol: "SWIGGY", tradingSymbol: "SWIGGY-EQ", securityId: "27066", name: "Swiggy", sector: "Consumer Services", ltp: 3137.5, changePct: -0.63, fiftyTwoWeekHigh: 4141.5, fiftyTwoWeekLow: 2259.0 },
  { symbol: "TATAPOWER", tradingSymbol: "TATAPOWER-EQ", securityId: "3426", name: "Tata Power", sector: "Power", ltp: 440.00, changePct: 1.50, fiftyTwoWeekHigh: 494.00, fiftyTwoWeekLow: 230.00 },
  { symbol: "TCS", tradingSymbol: "TCS-EQ", securityId: "11536", name: "Tata Consultancy Services", sector: "Information Technology", ltp: 4210.00, changePct: -0.45, fiftyTwoWeekHigh: 4585.00, fiftyTwoWeekLow: 3313.00 },
  { symbol: "TIINDIA", tradingSymbol: "TIINDIA-EQ", securityId: "312", name: "Tube Investment", sector: "Automobile and Auto Components", ltp: 787.0, changePct: -1.79, fiftyTwoWeekHigh: 1038.84, fiftyTwoWeekLow: 566.64 },
  { symbol: "TITAN", tradingSymbol: "TITAN-EQ", securityId: "3506", name: "Titan", sector: "Consumer Durables", ltp: 3450.00, changePct: 0.75, fiftyTwoWeekHigh: 3886.00, fiftyTwoWeekLow: 3050.00 },
  { symbol: "TVSMOTOR", tradingSymbol: "TVSMOTOR-EQ", securityId: "8479", name: "TVS Motors", sector: "Automobile and Auto Components", ltp: 2650.00, changePct: 0.80, fiftyTwoWeekHigh: 2900.00, fiftyTwoWeekLow: 1450.00 },
  { symbol: "UNIONBANK", tradingSymbol: "UNIONBANK-EQ", securityId: "10753", name: "Union Bank of India", sector: "Financial Services", ltp: 4245.0, changePct: 0.18, fiftyTwoWeekHigh: 5603.4, fiftyTwoWeekLow: 3056.4 },
  { symbol: "VBL", tradingSymbol: "VBL-EQ", securityId: "18921", name: "Varun Beverages", sector: "Fast Moving Consumer Goods", ltp: 4870.0, changePct: 0.62, fiftyTwoWeekHigh: 6428.4, fiftyTwoWeekLow: 3506.4 },
  { symbol: "VEDL", tradingSymbol: "VEDL-EQ", securityId: "3063", name: "Vedanta", sector: "Metals & Mining", ltp: 460.00, changePct: 0.90, fiftyTwoWeekHigh: 506.00, fiftyTwoWeekLow: 208.00 },
  { symbol: "ZYDUSLIFE", tradingSymbol: "ZYDUSLIFE-EQ", securityId: "7929", name: "Zydus Life Science", sector: "Healthcare", ltp: 1090.00, changePct: 0.30, fiftyTwoWeekHigh: 1320.00, fiftyTwoWeekLow: 560.00 },
  { symbol: "HEROMOTOCO", tradingSymbol: "HEROMOTOCO-EQ", securityId: "1348", name: "Hero Motocorp", sector: "Automobile and Auto Components", ltp: 5300.00, changePct: -0.16, fiftyTwoWeekHigh: 5890.00, fiftyTwoWeekLow: 2900.00 },
  { symbol: "HYUNDAI", tradingSymbol: "HYUNDAI-EQ", securityId: "25844", name: "Hyundai Motor India", sector: "Automobile and Auto Components", ltp: 1856.0, changePct: -0.19, fiftyTwoWeekHigh: 2449.92, fiftyTwoWeekLow: 1336.32 },
  { symbol: "ICICIBANK", tradingSymbol: "ICICIBANK-EQ", securityId: "4963", name: "ICICI Bank", sector: "Financial Services", ltp: 1215.30, changePct: 1.65, fiftyTwoWeekHigh: 1335.00, fiftyTwoWeekLow: 980.00 },
  { symbol: "INDIGO", tradingSymbol: "INDIGO-EQ", securityId: "11195", name: "Interglobe Aviation", sector: "Services", ltp: 4850.00, changePct: 1.10, fiftyTwoWeekHigh: 5050.00, fiftyTwoWeekLow: 2300.00 },
  { symbol: "BSE", tradingSymbol: "BSE-EQ", securityId: "19585", name: "BSE", sector: "Financial Services", ltp: 2290.5, changePct: -0.05, fiftyTwoWeekHigh: 3023.46, fiftyTwoWeekLow: 1649.16 },
  { symbol: "LICHSGFIN", tradingSymbol: "LICHSGFIN-EQ", securityId: "1997", name: "LIC Housing Finance", sector: "Financial Services", ltp: 685.00, changePct: 0.70, fiftyTwoWeekHigh: 805.00, fiftyTwoWeekLow: 420.00 },
  { symbol: "LTF", tradingSymbol: "LTF-EQ", securityId: "24948", name: "L&T Finance", sector: "Financial Services", ltp: 840.0, changePct: 0.82, fiftyTwoWeekHigh: 1108.8, fiftyTwoWeekLow: 604.8 },
  { symbol: "HDFCAMC", tradingSymbol: "HDFCAMC-EQ", securityId: "4244", name: "HDFC AMC", sector: "Financial Services", ltp: 4280.00, changePct: -1.62, fiftyTwoWeekHigh: 4550.00, fiftyTwoWeekLow: 2500.00 },
  { symbol: "MOTILALOFS", tradingSymbol: "MOTILALOFS-EQ", securityId: "14947", name: "Motilal Oswal Financial Services", sector: "Financial Services", ltp: 2037.5, changePct: -0.17, fiftyTwoWeekHigh: 2689.5, fiftyTwoWeekLow: 1467.0 },
  { symbol: "MPHASIS", tradingSymbol: "MPHASIS-EQ", securityId: "4503", name: "Mphasis", sector: "Information Technology", ltp: 2357.10, changePct: -2.68, fiftyTwoWeekHigh: 3125.00, fiftyTwoWeekLow: 2180.00 },
  { symbol: "NATIONALUM", tradingSymbol: "NATIONALUM-EQ", securityId: "6364", name: "NALCO", sector: "Metals & Mining", ltp: 195.00, changePct: 1.60, fiftyTwoWeekHigh: 210.00, fiftyTwoWeekLow: 88.00 },
  { symbol: "NBCC", tradingSymbol: "NBCC-EQ", securityId: "31415", name: "NBCC", sector: "Construction", ltp: 517.5, changePct: -1.06, fiftyTwoWeekHigh: 683.1, fiftyTwoWeekLow: 372.6 },
  { symbol: "NYKAA", tradingSymbol: "NYKAA-EQ", securityId: "6545", name: "Nykaa", sector: "Consumer Services", ltp: 215.00, changePct: 1.50, fiftyTwoWeekHigh: 235.00, fiftyTwoWeekLow: 135.00 },
  { symbol: "ICICIPRULI", tradingSymbol: "ICICIPRULI-EQ", securityId: "18652", name: "ICICI Prudential Life Insurance", sector: "Financial Services", ltp: 745.00, changePct: 0.40, fiftyTwoWeekHigh: 790.00, fiftyTwoWeekLow: 465.00 },
  { symbol: "PERSISTENT", tradingSymbol: "PERSISTENT-EQ", securityId: "18365", name: "Persistent Systems", sector: "Information Technology", ltp: 5250.00, changePct: 1.40, fiftyTwoWeekHigh: 5600.00, fiftyTwoWeekLow: 3100.00 },
  { symbol: "PNBHOUSING", tradingSymbol: "PNBHOUSING-EQ", securityId: "18908", name: "PNB Housing Finance", sector: "Financial Services", ltp: 3924.0, changePct: 0.32, fiftyTwoWeekHigh: 5179.68, fiftyTwoWeekLow: 2825.28 },
  { symbol: "POWERGRID", tradingSymbol: "POWERGRID-EQ", securityId: "14977", name: "Power Grid Corporation of India", sector: "Power", ltp: 330.00, changePct: 0.60, fiftyTwoWeekHigh: 365.00, fiftyTwoWeekLow: 185.00 },
  { symbol: "LAURUSLABS", tradingSymbol: "LAURUSLABS-EQ", securityId: "19234", name: "Laurus Labs", sector: "Healthcare", ltp: 440.00, changePct: -0.20, fiftyTwoWeekHigh: 490.00, fiftyTwoWeekLow: 340.00 },
  { symbol: "RELIANCE", tradingSymbol: "RELIANCE-EQ", securityId: "2885", name: "Reliance Industries", sector: "Oil Gas & Consumable Fuels", ltp: 2980.50, changePct: 1.25, fiftyTwoWeekHigh: 3217.90, fiftyTwoWeekLow: 2220.30 },
  { symbol: "MAZDOCK", tradingSymbol: "MAZDOCK-EQ", securityId: "509", name: "Mazagon Dock Shipbuilders", sector: "Capital Goods", ltp: 423.0, changePct: -0.6, fiftyTwoWeekHigh: 558.36, fiftyTwoWeekLow: 304.56 },
  { symbol: "SONACOMS", tradingSymbol: "SONACOMS-EQ", securityId: "4684", name: "Sona BLW Precision Forgings", sector: "Automobile and Auto Components", ltp: 690.00, changePct: 0.70, fiftyTwoWeekHigh: 760.00, fiftyTwoWeekLow: 510.00 },
  { symbol: "NAUKRI", tradingSymbol: "NAUKRI-EQ", securityId: "13751", name: "Info Edge", sector: "Consumer Services", ltp: 7850.00, changePct: 0.90, fiftyTwoWeekHigh: 8400.00, fiftyTwoWeekLow: 3950.00 },
  { symbol: "SRF", tradingSymbol: "SRF-EQ", securityId: "3273", name: "SRF", sector: "Chemicals", ltp: 2450.00, changePct: 0.80, fiftyTwoWeekHigh: 2690.00, fiftyTwoWeekLow: 2050.00 },
  { symbol: "TECHM", tradingSymbol: "TECHM-EQ", securityId: "13538", name: "Tech Mahindra", sector: "Information Technology", ltp: 1580.00, changePct: -0.50, fiftyTwoWeekHigh: 1680.00, fiftyTwoWeekLow: 1080.00 },
  { symbol: "ULTRACEMCO", tradingSymbol: "ULTRACEMCO-EQ", securityId: "11532", name: "UltraTech Cement", sector: "Construction Materials", ltp: 11200.00, changePct: 0.70, fiftyTwoWeekHigh: 12100.00, fiftyTwoWeekLow: 7900.00 },
  { symbol: "UNOMINDA", tradingSymbol: "UNOMINDA-EQ", securityId: "14154", name: "UNO Minda", sector: "Automobile and Auto Components", ltp: 308.5, changePct: 2.75, fiftyTwoWeekHigh: 407.22, fiftyTwoWeekLow: 222.12 },
  { symbol: "VMM", tradingSymbol: "VMM-EQ", securityId: "27969", name: "Vishal Mega Mart", sector: "Consumer Services", ltp: 3659.0, changePct: 1.59, fiftyTwoWeekHigh: 4829.88, fiftyTwoWeekLow: 2634.48 },
  { symbol: "WIPRO", tradingSymbol: "WIPRO-EQ", securityId: "3787", name: "Wipro", sector: "Information Technology", ltp: 540.00, changePct: 0.10, fiftyTwoWeekHigh: 580.00, fiftyTwoWeekLow: 375.00 },
  { symbol: "ASTRAL", tradingSymbol: "ASTRAL-EQ", securityId: "14418", name: "Astral", sector: "Capital Goods", ltp: 2100.00, changePct: 0.40, fiftyTwoWeekHigh: 2450.00, fiftyTwoWeekLow: 1750.00 },
  { symbol: "BAJFINANCE", tradingSymbol: "BAJFINANCE-EQ", securityId: "317", name: "Bajaj Finance", sector: "Financial Services", ltp: 7100.00, changePct: -0.75, fiftyTwoWeekHigh: 8192.00, fiftyTwoWeekLow: 6374.00 },
  { symbol: "UNITDSPR", tradingSymbol: "UNITDSPR-EQ", securityId: "10447", name: "United Spirits", sector: "Fast Moving Consumer Goods", ltp: 1450.00, changePct: 0.80, fiftyTwoWeekHigh: 1580.00, fiftyTwoWeekLow: 980.00 },
  { symbol: "ASHOKLEY", tradingSymbol: "ASHOKLEY-EQ", securityId: "212", name: "Ashok Leyland", sector: "Capital Goods", ltp: 228.00, changePct: 0.40, fiftyTwoWeekHigh: 260.00, fiftyTwoWeekLow: 157.00 },
  { symbol: "MUTHOOTFIN", tradingSymbol: "MUTHOOTFIN-EQ", securityId: "23650", name: "Muthoot Finance", sector: "Financial Services", ltp: 1890.00, changePct: 0.90, fiftyTwoWeekHigh: 2040.00, fiftyTwoWeekLow: 1200.00 },
  { symbol: "CUMMINSIND", tradingSymbol: "CUMMINSIND-EQ", securityId: "1901", name: "Cummins", sector: "Capital Goods", ltp: 3750.00, changePct: 0.70, fiftyTwoWeekHigh: 4150.00, fiftyTwoWeekLow: 1650.00 },
  { symbol: "GAIL", tradingSymbol: "GAIL-EQ", securityId: "4717", name: "GAIL", sector: "Oil Gas & Consumable Fuels", ltp: 235.00, changePct: 0.80, fiftyTwoWeekHigh: 246.00, fiftyTwoWeekLow: 115.00 },
  { symbol: "SIEMENS", tradingSymbol: "SIEMENS-EQ", securityId: "3150", name: "Siemens", sector: "Capital Goods", ltp: 6900.00, changePct: 0.80, fiftyTwoWeekHigh: 7900.00, fiftyTwoWeekLow: 3300.00 },
  { symbol: "MFSL", tradingSymbol: "MFSL-EQ", securityId: "2142", name: "Max Financial Services", sector: "Financial Services", ltp: 1140.00, changePct: 1.10, fiftyTwoWeekHigh: 1250.00, fiftyTwoWeekLow: 850.00 },
  { symbol: "NHPC", tradingSymbol: "NHPC-EQ", securityId: "17400", name: "NHPC", sector: "Power", ltp: 95.00, changePct: 0.80, fiftyTwoWeekHigh: 118.00, fiftyTwoWeekLow: 49.00 },
  { symbol: "NTPC", tradingSymbol: "NTPC-EQ", securityId: "11630", name: "NTPC", sector: "Power", ltp: 410.00, changePct: 0.90, fiftyTwoWeekHigh: 440.00, fiftyTwoWeekLow: 210.00 },
  { symbol: "TORNTPHARM", tradingSymbol: "TORNTPHARM-EQ", securityId: "3518", name: "Torrent Pharmaceuticals", sector: "Healthcare", ltp: 3350.00, changePct: 0.50, fiftyTwoWeekHigh: 3600.00, fiftyTwoWeekLow: 1800.00 },
  { symbol: "RVNL", tradingSymbol: "RVNL-EQ", securityId: "9552", name: "Rail Vikas Nigam", sector: "Construction", ltp: 580.00, changePct: 2.10, fiftyTwoWeekHigh: 640.00, fiftyTwoWeekLow: 130.00 },
  { symbol: "KOTAKBANK", tradingSymbol: "KOTAKBANK-EQ", securityId: "1922", name: "Kotak Bank", sector: "Financial Services", ltp: 1810.00, changePct: -0.30, fiftyTwoWeekHigh: 1932.00, fiftyTwoWeekLow: 1544.00 },
  { symbol: "LICI", tradingSymbol: "LICI-EQ", securityId: "9480", name: "LIC of India", sector: "Financial Services", ltp: 1020.00, changePct: 0.95, fiftyTwoWeekHigh: 1222.00, fiftyTwoWeekLow: 600.00 },
  { symbol: "AUBANK", tradingSymbol: "AUBANK-EQ", securityId: "21238", name: "AU Small Finance Bank", sector: "Financial Services", ltp: 635.00, changePct: 0.45, fiftyTwoWeekHigh: 813.00, fiftyTwoWeekLow: 554.00 },
  { symbol: "HAL", tradingSymbol: "HAL-EQ", securityId: "2303", name: "Hindustan Aeronautics", sector: "Capital Goods", ltp: 4750.00, changePct: 3.10, fiftyTwoWeekHigh: 5675.00, fiftyTwoWeekLow: 1760.00 },
  { symbol: "IDEA", tradingSymbol: "IDEA-EQ", securityId: "14366", name: "Vodafone Idea", sector: "Telecommunication", ltp: 13.50, changePct: 2.20, fiftyTwoWeekHigh: 19.10, fiftyTwoWeekLow: 9.80 },
  { symbol: "INDUSTOWER", tradingSymbol: "INDUSTOWER-EQ", securityId: "29135", name: "Indus Towers", sector: "Telecommunication", ltp: 345.00, changePct: 1.20, fiftyTwoWeekHigh: 450.00, fiftyTwoWeekLow: 170.00 },
  { symbol: "IOC", tradingSymbol: "IOC-EQ", securityId: "1624", name: "Indian Oil Corporation", sector: "Oil Gas & Consumable Fuels", ltp: 175.00, changePct: 0.30, fiftyTwoWeekHigh: 196.00, fiftyTwoWeekLow: 85.00 },
  { symbol: "IREDA", tradingSymbol: "IREDA-EQ", securityId: "20261", name: "IREDA", sector: "Financial Services", ltp: 2739.5, changePct: 0.29, fiftyTwoWeekHigh: 3616.14, fiftyTwoWeekLow: 1972.44 },
  { symbol: "TRENT", tradingSymbol: "TRENT-EQ", securityId: "1964", name: "Trent", sector: "Consumer Services", ltp: 7250.00, changePct: 2.40, fiftyTwoWeekHigh: 7600.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "SBICARD", tradingSymbol: "SBICARD-EQ", securityId: "17971", name: "SBI Cards", sector: "Financial Services", ltp: 730.00, changePct: -0.40, fiftyTwoWeekHigh: 865.00, fiftyTwoWeekLow: 670.00 },
  { symbol: "SHRIRAMFIN", tradingSymbol: "SHRIRAMFIN-EQ", securityId: "4306", name: "Shriram Finance", sector: "Financial Services", ltp: 3250.00, changePct: 1.40, fiftyTwoWeekHigh: 3410.00, fiftyTwoWeekLow: 1790.00 },
  { symbol: "CANBK", tradingSymbol: "CANBK-EQ", securityId: "10794", name: "Canara Bank", sector: "Financial Services", ltp: 104.20, changePct: 0.70, fiftyTwoWeekHigh: 129.00, fiftyTwoWeekLow: 69.00 },
  { symbol: "YESBANK", tradingSymbol: "YESBANK-EQ", securityId: "11915", name: "Yes Bank", sector: "Financial Services", ltp: 846.5, changePct: -0.49, fiftyTwoWeekHigh: 1117.38, fiftyTwoWeekLow: 609.48 },
  { symbol: "VOLTAS", tradingSymbol: "VOLTAS-EQ", securityId: "3718", name: "Voltas", sector: "Consumer Durables", ltp: 1820.00, changePct: 1.40, fiftyTwoWeekHigh: 1950.00, fiftyTwoWeekLow: 810.00 },
  { symbol: "HINDPETRO", tradingSymbol: "HINDPETRO-EQ", securityId: "1406", name: "Hindustan Petroleum", sector: "Oil Gas & Consumable Fuels", ltp: 390.00, changePct: 0.50, fiftyTwoWeekHigh: 430.00, fiftyTwoWeekLow: 190.00 },
  { symbol: "ATHERENERG", tradingSymbol: "ATHERENERG-EQ", securityId: "757645", name: "Ather Energy", sector: "Automobile and Auto Components", ltp: 4074.5, changePct: -2.21, fiftyTwoWeekHigh: 5378.34, fiftyTwoWeekLow: 2933.64 },
  { symbol: "MAHABANK", tradingSymbol: "MAHABANK-EQ", securityId: "11377", name: "Bank of Maharashtra", sector: "Financial Services", ltp: 3364.0, changePct: -0.31, fiftyTwoWeekHigh: 4440.48, fiftyTwoWeekLow: 2422.08 },
  { symbol: "SAGILITY", tradingSymbol: "SAGILITY-EQ", securityId: "27052", name: "Sagility", sector: "Information Technology", ltp: 1321.5, changePct: -1.39, fiftyTwoWeekHigh: 1744.38, fiftyTwoWeekLow: 951.48 },
];

/** @deprecated Renamed to FNO_STOCKS - the NSE F&O list is no longer 208 names. */
export const FNO_208_STOCKS = FNO_STOCKS;

// Helper to convert StockMasterEntry to WatchlistItem
function toWatchlistItem(stock: StockMasterEntry, order: number): WatchlistItem {
  const ltp = stock.ltp;
  const changePct = stock.changePct;
  const changeAbs = Number(((ltp * changePct) / 100).toFixed(2));
  return {
    symbol: stock.symbol,
    segment: stock.segment || "NSE_EQ",
    securityId: stock.securityId,
    tradingSymbol: stock.tradingSymbol,
    name: stock.name,
    sector: stock.sector,
    instrumentType: "EQUITY",
    order,
    ltp,
    changePct,
    changeAbs,
    volume: stock.volume || Math.floor(Math.random() * 2000000) + 500000,
    fiftyTwoWeekHigh: stock.fiftyTwoWeekHigh,
    fiftyTwoWeekLow: stock.fiftyTwoWeekLow,
    open: Number((ltp * 0.995).toFixed(2)),
    high: Number((ltp * 1.015).toFixed(2)),
    low: Number((ltp * 0.99).toFixed(2)),
    prevClose: Number((ltp - changeAbs).toFixed(2)),
    bid: Number((ltp - 0.05).toFixed(2)),
    ask: Number((ltp + 0.05).toFixed(2)),
  };
}

// ---------------------------------------------------------------------------
// Standard Index Stock Subsets
// ---------------------------------------------------------------------------

// Nifty 50 (50, official NSE constituents)
export const NIFTY_50_SYMBOLS = [
  "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
  "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL", "CIPLA", "COALINDIA",
  "DRREDDY", "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK",
  "HDFCLIFE", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", "INFY",
  "INDIGO", "JSWSTEEL", "JIOFIN", "KOTAKBANK", "LT", "M&M",
  "MARUTI", "MAXHEALTH", "NTPC", "NESTLEIND", "ONGC", "POWERGRID",
  "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN", "SUNPHARMA", "TCS",
  "TATACONSUM", "TMPV", "TATASTEEL", "TECHM", "TITAN", "TRENT",
  "ULTRACEMCO", "WIPRO",
];

// Nifty Next 50 (50, official NSE constituents)
export const NIFTY_NEXT_50_SYMBOLS = [
  "ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "DMART",
  "BAJAJHLDNG", "BANKBARODA", "BPCL", "BOSCHLTD", "BRITANNIA", "CGPOWER",
  "CANBK", "CHOLAFIN", "CUMMINSIND", "DLF", "DIVISLAB", "GAIL",
  "GODREJCP", "HDFCAMC", "HAL", "HINDZINC", "HYUNDAI", "INDHOTEL",
  "IOC", "IRFC", "JINDALSTEL", "LTM", "LODHA", "MAZDOCK",
  "MUTHOOTFIN", "PIDILITIND", "PFC", "PNB", "RECLTD", "MOTHERSON",
  "SHREECEM", "ENRIN", "SIEMENS", "SOLARINDS", "TVSMOTOR", "TATACAP",
  "TMCV", "TATAPOWER", "TORNTPHARM", "UNIONBANK", "UNITDSPR", "VBL",
  "VEDL", "ZYDUSLIFE",
];

// Nifty 100 (100, official NSE constituents)
export const NIFTY_100_SYMBOLS = [
  "ABB", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER",
  "AMBUJACEM", "APOLLOHOSP", "ASIANPAINT", "DMART", "AXISBANK", "BAJAJ-AUTO",
  "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG", "BANKBARODA", "BEL", "BPCL",
  "BHARTIARTL", "BOSCHLTD", "BRITANNIA", "CGPOWER", "CANBK", "CHOLAFIN",
  "CIPLA", "COALINDIA", "CUMMINSIND", "DLF", "DIVISLAB", "DRREDDY",
  "EICHERMOT", "ETERNAL", "GAIL", "GODREJCP", "GRASIM", "HCLTECH",
  "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HINDALCO", "HAL", "HINDUNILVR",
  "HINDZINC", "HYUNDAI", "ICICIBANK", "ITC", "INDHOTEL", "IOC",
  "IRFC", "INFY", "INDIGO", "JSWSTEEL", "JINDALSTEL", "JIOFIN",
  "KOTAKBANK", "LTM", "LT", "LODHA", "M&M", "MARUTI",
  "MAXHEALTH", "MAZDOCK", "MUTHOOTFIN", "NTPC", "NESTLEIND", "ONGC",
  "PIDILITIND", "PFC", "POWERGRID", "PNB", "RECLTD", "RELIANCE",
  "SBILIFE", "MOTHERSON", "SHREECEM", "SHRIRAMFIN", "ENRIN", "SIEMENS",
  "SOLARINDS", "SBIN", "SUNPHARMA", "TVSMOTOR", "TATACAP", "TCS",
  "TATACONSUM", "TMCV", "TMPV", "TATAPOWER", "TATASTEEL", "TECHM",
  "TITAN", "TORNTPHARM", "TRENT", "ULTRACEMCO", "UNIONBANK", "UNITDSPR",
  "VBL", "VEDL", "WIPRO", "ZYDUSLIFE",
];

// Nifty 200 (200, official NSE constituents)
export const NIFTY_200_SYMBOLS = [
  "360ONE", "ABB", "APLAPOLLO", "AUBANK", "ADANIENSOL", "ADANIENT",
  "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ATGL", "ABCAPITAL", "ALKEM",
  "AMBUJACEM", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUROPHARMA",
  "DMART", "AXISBANK", "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV",
  "BAJAJHLDNG", "BANKBARODA", "BANKINDIA", "BDL", "BEL", "BHARATFORG",
  "BHEL", "BPCL", "BHARTIARTL", "GROWW", "BIOCON", "BLUESTARCO",
  "BOSCHLTD", "BRITANNIA", "CGPOWER", "CANBK", "CHOLAFIN", "CIPLA",
  "COALINDIA", "COCHINSHIP", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL",
  "CUMMINSIND", "DLF", "DABUR", "DIVISLAB", "DIXON", "DRREDDY",
  "EICHERMOT", "ETERNAL", "EXIDEIND", "NYKAA", "FEDERALBNK", "FORTIS",
  "GAIL", "GVT&D", "GMRAIRPORT", "GLENMARK", "GODFRYPHLP", "GODREJCP",
  "GODREJPROP", "GRASIM", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE",
  "HAVELLS", "HEROMOTOCO", "HINDALCO", "HAL", "HINDPETRO", "HINDUNILVR",
  "HINDZINC", "POWERINDIA", "HUDCO", "HYUNDAI", "ICICIBANK", "ICICIGI",
  "ICICIAMC", "IDFCFIRSTB", "ITC", "INDIANB", "INDHOTEL", "IOC",
  "IRCTC", "IRFC", "IREDA", "INDUSTOWER", "INDUSINDBK", "NAUKRI",
  "INFY", "INDIGO", "JSWENERGY", "JSWSTEEL", "JINDALSTEL", "JIOFIN",
  "JUBLFOOD", "KEI", "KPITTECH", "KALYANKJIL", "KOTAKBANK", "LTF",
  "LGEINDIA", "LICHSGFIN", "LTM", "LT", "LAURUSLABS", "LENSKART",
  "LODHA", "LUPIN", "MRF", "M&MFIN", "M&M", "MANKIND",
  "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "MOTILALOFS",
  "MPHASIS", "MCX", "MUTHOOTFIN", "NHPC", "NMDC", "NTPC",
  "NATIONALUM", "NESTLEIND", "OBEROIRLTY", "ONGC", "OIL", "PAYTM",
  "OFSS", "POLICYBZR", "PIIND", "PAGEIND", "PATANJALI", "PERSISTENT",
  "PHOENIXLTD", "PIDILITIND", "POLYCAB", "PFC", "POWERGRID", "PREMIERENE",
  "PRESTIGE", "PNB", "RECLTD", "RADICO", "RVNL", "RELIANCE",
  "SBICARD", "SBILIFE", "SRF", "MOTHERSON", "SHREECEM", "SHRIRAMFIN",
  "ENRIN", "SIEMENS", "SOLARINDS", "SBIN", "SAIL", "SUNPHARMA",
  "SUPREMEIND", "SUZLON", "SWIGGY", "TVSMOTOR", "TATACAP", "TATACOMM",
  "TCS", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TMCV", "TMPV",
  "TATAPOWER", "TATASTEEL", "TECHM", "TITAN", "TORNTPHARM", "TRENT",
  "TIINDIA", "UPL", "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "VBL",
  "VEDL", "VMM", "IDEA", "VOLTAS", "WAAREEENER", "WIPRO",
  "YESBANK", "ZYDUSLIFE",
];

// Nifty LargeMidcap 250 (250, official NSE constituents)
export const NIFTY_LARGEMIDCAP_250_SYMBOLS = [
  "360ONE", "3MINDIA", "ABB", "ACC", "AIAENG", "APLAPOLLO",
  "AUBANK", "AWL", "ABBOTINDIA", "ADANIENSOL", "ADANIENT", "ADANIGREEN",
  "ADANIPORTS", "ADANIPOWER", "ATGL", "ABCAPITAL", "AJANTPHARM", "ALKEM",
  "AMBUJACEM", "ANTHEM", "APARINDS", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY",
  "ASIANPAINT", "ASTRAL", "AUROPHARMA", "AIIL", "DMART", "AXISBANK",
  "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG", "BAJAJHFL",
  "BALKRISIND", "BANKBARODA", "BANKINDIA", "MAHABANK", "BERGEPAINT", "BDL",
  "BEL", "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL", "BHARTIHEXA",
  "GROWW", "BIOCON", "BLUESTARCO", "BOSCHLTD", "BRITANNIA", "CGPOWER",
  "CRISIL", "CANBK", "CHOLAFIN", "CIPLA", "COALINDIA", "COCHINSHIP",
  "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CUMMINSIND", "DLF",
  "DABUR", "DALBHARAT", "DIVISLAB", "DIXON", "DRREDDY", "EICHERMOT",
  "ENDURANCE", "ESCORTS", "ETERNAL", "EXIDEIND", "NYKAA", "FEDERALBNK",
  "FORTIS", "GAIL", "GVT&D", "GMRAIRPORT", "GICRE", "GLAXO",
  "GLENMARK", "MEDANTA", "GODFRYPHLP", "GODREJCP", "GODREJIND", "GODREJPROP",
  "GRASIM", "FLUOROCHEM", "HCLTECH", "HDBFS", "HDFCAMC", "HDFCBANK",
  "HDFCLIFE", "HAVELLS", "HEROMOTOCO", "HEXT", "HINDALCO", "HAL",
  "HINDPETRO", "HINDUNILVR", "HINDZINC", "POWERINDIA", "HONAUT", "HUDCO",
  "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIAMC", "ICICIPRULI", "IDFCFIRSTB",
  "ITCHOTELS", "ITC", "INDIANB", "INDHOTEL", "IOC", "IRCTC",
  "IRFC", "IREDA", "INDUSTOWER", "INDUSINDBK", "NAUKRI", "INFY",
  "INDIGO", "IPCALAB", "JKCEMENT", "JSWENERGY", "JSWINFRA", "JSWSTEEL",
  "JSL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "KPRMILL", "KEI",
  "KPITTECH", "KALYANKJIL", "KOTAKBANK", "LTF", "LTTS", "LGEINDIA",
  "LICHSGFIN", "LTM", "LT", "LAURUSLABS", "LENSKART", "LICI",
  "LINDEINDIA", "LLOYDSME", "LODHA", "LUPIN", "MRF", "M&MFIN",
  "M&M", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH",
  "MAZDOCK", "MOTILALOFS", "MPHASIS", "MCX", "MUTHOOTFIN", "NHPC",
  "NLCINDIA", "NMDC", "NTPCGREEN", "NTPC", "NATIONALUM", "NESTLEIND",
  "NAM-INDIA", "OBEROIRLTY", "ONGC", "OIL", "PAYTM", "OFSS",
  "POLICYBZR", "PIIND", "PAGEIND", "PATANJALI", "PERSISTENT", "PETRONET",
  "PHOENIXLTD", "PIDILITIND", "POLYCAB", "PFC", "POWERGRID", "PREMIERENE",
  "PRESTIGE", "PNB", "RECLTD", "RADICO", "RVNL", "RELIANCE",
  "SBICARD", "SBILIFE", "SJVN", "SRF", "MOTHERSON", "SCHAEFFLER",
  "SHREECEM", "SHRIRAMFIN", "ENRIN", "SIEMENS", "SOLARINDS", "SBIN",
  "SAIL", "SUNPHARMA", "SUNDARMFIN", "SUPREMEIND", "SUZLON", "SWIGGY",
  "TVSMOTOR", "TATACAP", "TATACOMM", "TCS", "TATACONSUM", "TATAELXSI",
  "TATAINVEST", "TMCV", "TMPV", "TATAPOWER", "TATASTEEL", "TECHM",
  "NIACL", "THERMAX", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT",
  "TIINDIA", "UNOMINDA", "UPL", "ULTRACEMCO", "UNIONBANK", "UBL",
  "UNITDSPR", "VBL", "VEDL", "VMM", "IDEA", "VOLTAS",
  "WAAREEENER", "WIPRO", "YESBANK", "ZYDUSLIFE",
];

// Nifty Midcap 150 (150, official NSE constituents)
export const NIFTY_MIDCAP_150_SYMBOLS = [
  "360ONE", "3MINDIA", "ACC", "AIAENG", "APLAPOLLO", "AUBANK",
  "AWL", "ABBOTINDIA", "ATGL", "ABCAPITAL", "AJANTPHARM", "ALKEM",
  "ANTHEM", "APARINDS", "APOLLOTYRE", "ASHOKLEY", "ASTRAL", "AUROPHARMA",
  "AIIL", "BSE", "BAJAJHFL", "BALKRISIND", "BANKINDIA", "MAHABANK",
  "BERGEPAINT", "BDL", "BHARATFORG", "BHEL", "BHARTIHEXA", "GROWW",
  "BIOCON", "BLUESTARCO", "CRISIL", "COCHINSHIP", "COFORGE", "COLPAL",
  "CONCOR", "COROMANDEL", "DABUR", "DALBHARAT", "DIXON", "ENDURANCE",
  "ESCORTS", "EXIDEIND", "NYKAA", "FEDERALBNK", "FORTIS", "GVT&D",
  "GMRAIRPORT", "GICRE", "GLAXO", "GLENMARK", "MEDANTA", "GODFRYPHLP",
  "GODREJIND", "GODREJPROP", "FLUOROCHEM", "HDBFS", "HAVELLS", "HEROMOTOCO",
  "HEXT", "HINDPETRO", "POWERINDIA", "HONAUT", "HUDCO", "ICICIGI",
  "ICICIAMC", "ICICIPRULI", "IDFCFIRSTB", "ITCHOTELS", "INDIANB", "IRCTC",
  "IREDA", "INDUSTOWER", "INDUSINDBK", "NAUKRI", "IPCALAB", "JKCEMENT",
  "JSWENERGY", "JSWINFRA", "JSL", "JUBLFOOD", "KPRMILL", "KEI",
  "KPITTECH", "KALYANKJIL", "LTF", "LTTS", "LGEINDIA", "LICHSGFIN",
  "LAURUSLABS", "LENSKART", "LICI", "LINDEINDIA", "LLOYDSME", "LUPIN",
  "MRF", "M&MFIN", "MANKIND", "MARICO", "MFSL", "MOTILALOFS",
  "MPHASIS", "MCX", "NHPC", "NLCINDIA", "NMDC", "NTPCGREEN",
  "NATIONALUM", "NAM-INDIA", "OBEROIRLTY", "OIL", "PAYTM", "OFSS",
  "POLICYBZR", "PIIND", "PAGEIND", "PATANJALI", "PERSISTENT", "PETRONET",
  "PHOENIXLTD", "POLYCAB", "PREMIERENE", "PRESTIGE", "RADICO", "RVNL",
  "SBICARD", "SJVN", "SRF", "SCHAEFFLER", "SAIL", "SUNDARMFIN",
  "SUPREMEIND", "SUZLON", "SWIGGY", "TATACOMM", "TATAELXSI", "TATAINVEST",
  "NIACL", "THERMAX", "TORNTPOWER", "TIINDIA", "UNOMINDA", "UPL",
  "UBL", "VMM", "IDEA", "VOLTAS", "WAAREEENER", "YESBANK",
];

// Nifty Midcap Select (25, official NSE constituents)
export const NIFTY_MIDCAP_SELECT_SYMBOLS = [
  "AUBANK", "ASHOKLEY", "AUROPHARMA", "BSE", "BHARATFORG", "BHEL",
  "DIXON", "FORTIS", "HEROMOTOCO", "HINDPETRO", "INDIANB", "INDUSTOWER",
  "INDUSINDBK", "NAUKRI", "LICI", "LUPIN", "MARICO", "PAYTM",
  "POLICYBZR", "PERSISTENT", "POLYCAB", "SRF", "SUZLON", "SWIGGY",
  "YESBANK",
];

// Nifty Smallcap 250 (250, official NSE constituents)
export const NIFTY_SMALLCAP_250_SYMBOLS = [
  "ACMESOLAR", "AADHARHFC", "AARTIIND", "AAVAS", "ACE", "ACUTAAS",
  "ABFRL", "ABLBL", "ABREL", "ABSLAMC", "CPPLUS", "AEGISLOG",
  "AEGISVOPAK", "AFCONS", "AFFLE", "ABDL", "ARE&M", "AMBER",
  "ANANDRATHI", "ANANTRAJ", "ANGELONE", "ANURAS", "APTUS", "ASAHIINDIA",
  "ASTERDM", "ATHERENERG", "ATUL", "BEML", "BLS", "BALRAMCHIN",
  "BANDHANBNK", "BATAINDIA", "BAYERCROP", "BELRISE", "BIKAJI", "BSOFT",
  "BLUEDART", "BLUEJET", "BBTC", "FIRSTCRY", "BRIGADE", "MAPMYINDIA",
  "CCL", "CESC", "CIEINDIA", "CANFINHOME", "CANHLIFE", "CAPLIPOINT",
  "CGCL", "CARBORUNIV", "CARTRADE", "CASTROLIND", "CEATLTD", "CEMPRO",
  "CENTRALBK", "CDSL", "CHALET", "CHAMBLFERT", "CHENNPETRO", "CHOICEIN",
  "CHOLAHLDNG", "CUB", "CLEAN", "COHANCE", "CAMS", "CONCORDBIO",
  "CRAFTSMAN", "CREDITACC", "CROMPTON", "CYIENT", "DCMSHRIRAM", "DOMS",
  "DATAPATTNS", "DEEPAKFERT", "DEEPAKNTR", "DELHIVERY", "DEVYANI", "LALPATHLAB",
  "EIDPARRY", "EIHOTEL", "ELECON", "ELGIEQUIP", "EMAMILTD", "EMCURE",
  "EMMVEE", "ENGINERSIN", "ERIS", "FACT", "FINCABLES", "FSL",
  "FIVESTAR", "FORCEMOT", "GABRIEL", "GALLANTT", "GRSE", "GILLETTE",
  "GLAND", "GODIGIT", "GPIL", "GRANULES", "GRAPHITE", "GRAVITA",
  "GESHIP", "GMDCLTD", "HBLENGINE", "HEG", "HFCL", "HSCL",
  "HINDCOPPER", "HOMEFIRST", "HONASA", "IDBI", "IFCI", "IIFL",
  "IRB", "IRCON", "ITI", "INDGN", "INDIACEM", "INDIAMART",
  "IEX", "IOB", "IGL", "INOXWIND", "INTELLECT", "IGIL",
  "IKS", "JBMA", "JKTYRE", "JMFINANCIL", "JSWCEMENT", "JSWDULUX",
  "JAINREC", "JPPOWER", "J&KBANK", "JINDALSAW", "JUBLINGREA", "JUBLPHARMA",
  "JWL", "JYOTICNC", "KAJARIACER", "KPIL", "KARURVYSYA", "KAYNES",
  "KEC", "KFINTECH", "KIRLOSENG", "KIMS", "LTFOODS", "LATENTVIEW",
  "THELEELA", "LEMONTREE", "MMTC", "MGL", "MANAPPURAM", "MRPL",
  "MEESHO", "MINDACORP", "MSUMI", "NATCOPHARM", "NBCC", "NCC",
  "NSLNISP", "NH", "NAVA", "NAVINFLUOR", "NETWEB", "NEULANDLAB",
  "NEWGEN", "NIVABUPA", "NUVAMA", "NUVOCO", "OLAELEC", "OLECTRA",
  "ONESOURCE", "PCBL", "PGEL", "PNBHOUSING", "PTCIL", "PVRINOX",
  "PARADEEP", "PFIZER", "PWL", "PINELABS", "PIRAMALFIN", "PPLPHARMA",
  "POLYMED", "POONAWALLA", "PFOCUS", "RRKABEL", "RBLBANK", "RHIM",
  "RITES", "RAILTEL", "RAINBOW", "RKFORGE", "REDINGTON", "RPOWER",
  "SBFC", "SAGILITY", "SAILIFE", "SAMMAANCAP", "SAPPHIRE", "SARDAEN",
  "SAREGAMA", "SCHNEIDER", "SCI", "SHYAMMETL", "SIGNATURE", "SOBHA",
  "SONACOMS", "SONATSOFTW", "STARHEALTH", "SUMICHEM", "SUNTV", "SPLPETRO",
  "SWANCORP", "SYNGENE", "SYRMA", "TBOTEK", "TATACHEM", "TATATECH",
  "TTML", "TECHNOE", "TEGA", "TEJASNET", "TENNIND", "RAMCOCEM",
  "TIMKEN", "TITAGARH", "TARIL", "TRAVELFOOD", "TRIDENT", "TRITURBINE",
  "UCOBANK", "UTIAMC", "URBANCO", "USHAMART", "VTL", "VIJAYA",
  "WELCORP", "WELSPUNLIV", "WHIRLPOOL", "WOCKPHARMA", "ZFCVINDIA", "ZEEL",
  "ZENTEC", "ZENSARTECH", "ZYDUSWELL", "ECLERX",
];

// Nifty Microcap 250 (250, official NSE constituents)
export const NIFTY_MICROCAP_250_SYMBOLS = [
  "ASKAUTOLTD", "AXISCADES", "AARTIDRUGS", "AARTIPHARM", "AVL", "ADVENZYMES",
  "AEQUS", "AETHER", "AHLUCONT", "AKUMS", "APLLTD", "ALIVUS",
  "ALKYLAMINE", "ALOKINDS", "APOLLO", "ACI", "ARVINDFASN", "ARVIND",
  "ASHAPURMIN", "ASHOKA", "ASTRAMICRO", "ATLANTAELE", "AURIONPRO", "AVALON",
  "AVANTIFEED", "CCAVENUE", "AWFIS", "AZAD", "BAJAJELEC", "BALAMINES",
  "BALUFORGE", "BANCOINDIA", "BIRLACORPN", "BBOX", "BLACKBUCK", "BLUESTONE",
  "BORORENEW", "CMSINFO", "CORONA", "CSBBANK", "CAMPUS", "CRAMC",
  "CAPILLARY", "CELLO", "CENTURYPLY", "CERA", "CRIZAC", "CUPID",
  "DCBBANK", "DATAMATICS", "DIACABS", "DBL", "AGARWALEYE", "DYNAMATECH",
  "EPL", "EDELWEISS", "EMIL", "ELECTCAST", "ELLEN", "EMBDL",
  "ENTERO", "EIEL", "EQUITASBNK", "ETHOSLTD", "EUREKAFORB", "FEDFINA",
  "FIEMIND", "FINPIPE", "UTLSOLAR", "GHCL", "GMMPFAUDLR", "GMRP&UI",
  "GRWRHITECH", "GODREJAGRO", "GOKEX", "GOKULAGRO", "GREAVESCOT", "GRINDWELL",
  "GAEL", "GNFC", "GPPL", "GSFC", "HGINFRA", "HAPPSTMNDS",
  "HCG", "HEMIPROP", "HERITGFOOD", "HCC", "IFBIND", "IIFLCAPS",
  "INOXINDIA", "INDIAGLYCO", "INDIASHLTR", "IMFA", "INDIGOPNTS", "ICIL",
  "INOXGREEN", "IONEXCHANG", "JAIBALAJI", "JKLAKSHMI", "JKPAPER", "JAMNAAUTO",
  "JSFB", "JAYNECOIND", "JSLL", "JLHL", "JUSTDIAL", "JYOTHYLAB",
  "KNRCON", "KPIGREEN", "KRBL", "KRN", "KSB", "KANSAINER",
  "KTKBANK", "KSCL", "KIRLOSBROS", "KIRLPNU", "KITEX", "LXCHEM",
  "IXIGO", "LLOYDSENGG", "LLOYDSENT", "LUMAXTECH", "MOIL", "MSTCLTD",
  "MTARTECH", "MAHSCOOTER", "MAHSEAMLES", "MANORAMA", "MARKSANS", "MASTEK",
  "MEDPLUS", "METROPOLIS", "MIDHANI", "BECTORFOOD", "NEOGEN", "NESCO",
  "NFL", "NAZARA", "NETWORK18", "OPTIEMUS", "ORIENTCEM", "ORKLAINDIA",
  "OSWALPUMPS", "PNGJL", "PCJEWELLER", "PNCINFRA", "PTC", "PARAS",
  "PARKHOSPS", "PGIL", "PICCADIL", "POWERMECH", "PRAJIND", "PRICOLLTD",
  "PRSMJOHNSN", "PRIVISCL", "PRUDENT", "PURVA", "QPOWER", "QUESS",
  "RAIN", "RALLIS", "RCF", "RATEGAIN", "RATNAMANI", "RTNINDIA",
  "RTNPOWER", "RAYMONDLSL", "REDTAPE", "REFEX", "RELAXO", "RELIGARE",
  "RBA", "ROUTE", "RUBICON", "SKFINDUS", "SKFINDIA", "SKYGOLD",
  "SMLMAH", "SHRIPISTON", "LOTUSDEV", "SAATVIKGL", "SAFARI", "SAMHI",
  "SANDUMA", "SANOFICONR", "SANSERA", "SENCO", "STYL", "SHAILY",
  "SHAKTIPUMP", "SHARDACROP", "SHAREINDIA", "SFL", "SHILPAMED", "RENUKA",
  "SKIPPER", "SMARTWORKS", "SOUTHBANK", "STARCEMENT", "SWSOLAR", "STLTECH",
  "STAR", "STYRENIX", "SUBROS", "SUDARSCHEM", "SUDEEPPHRM", "SPARC",
  "SUNTECK", "SUPRIYA", "SURYAROSNI", "TARC", "TDPOWERSYS", "TSFINV",
  "TVSSCS", "TMB", "TANLA", "TEXRAIL", "THANGAMAYL", "ANUP",
  "THOMASCOOK", "THYROCARE", "TI", "TIMETECHNO", "TIPSMUSIC", "TRANSRAILL",
  "TRIVENI", "UJJIVANSFB", "VGUARD", "VMART", "VIPIND", "V2RETAIL",
  "DBREALTY", "WABAG", "VAIBHAVGBL", "VARROC", "MANYAVAR", "VIKRAMSOLR",
  "VIYASH", "VOLTAMP", "WAAREERTL", "WAKEFIT", "WEWORK", "WEBELSOLAR",
  "WELENT", "WESTLIFE", "YATHARTH", "ZAGGLE",
];

// Nifty Bank (14, official NSE constituents)
export const BANK_NIFTY_SYMBOLS = [
  "AUBANK", "AXISBANK", "BANKBARODA", "CANBK", "FEDERALBNK", "HDFCBANK",
  "ICICIBANK", "IDFCFIRSTB", "INDUSINDBK", "KOTAKBANK", "PNB", "SBIN",
  "UNIONBANK", "YESBANK",
];

// Nifty Financial Services (20, official NSE constituents)
export const NIFTY_FINNIFTY_SYMBOLS = [
  "AXISBANK", "BSE", "BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "HDFCBANK",
  "HDFCLIFE", "ICICIBANK", "ICICIGI", "JIOFIN", "KOTAKBANK", "LICHSGFIN",
  "MFSL", "MUTHOOTFIN", "PFC", "RECLTD", "SBICARD", "SBILIFE",
  "SHRIRAMFIN", "SBIN",
];

// Nifty IT (10, official NSE constituents)
export const NIFTY_IT_SYMBOLS = [
  "COFORGE", "HCLTECH", "INFY", "LTM", "MPHASIS", "OFSS",
  "PERSISTENT", "TCS", "TECHM", "WIPRO",
];

// Nifty Auto (15, official NSE constituents)
export const NIFTY_AUTO_SYMBOLS = [
  "ASHOKLEY", "BAJAJ-AUTO", "BHARATFORG", "BOSCHLTD", "EICHERMOT", "EXIDEIND",
  "HEROMOTOCO", "M&M", "MARUTI", "MOTHERSON", "SONACOMS", "TVSMOTOR",
  "TMPV", "TIINDIA", "UNOMINDA",
];

// Nifty FMCG (15, official NSE constituents)
export const NIFTY_FMCG_SYMBOLS = [
  "BRITANNIA", "COLPAL", "DABUR", "EMAMILTD", "GODREJCP", "HINDUNILVR",
  "ITC", "MARICO", "NESTLEIND", "PATANJALI", "RADICO", "TATACONSUM",
  "UBL", "UNITDSPR", "VBL",
];

// Nifty Pharma (20, official NSE constituents)
export const NIFTY_PHARMA_SYMBOLS = [
  "ABBOTINDIA", "AJANTPHARM", "ALKEM", "AUROPHARMA", "BIOCON", "CIPLA",
  "DIVISLAB", "DRREDDY", "GLAND", "GLENMARK", "IPCALAB", "LAURUSLABS",
  "LUPIN", "MANKIND", "PPLPHARMA", "SAILIFE", "SUNPHARMA", "TORNTPHARM",
  "WOCKPHARMA", "ZYDUSLIFE",
];

// Nifty Metal (15, official NSE constituents)
export const NIFTY_METAL_SYMBOLS = [
  "APLAPOLLO", "ADANIENT", "HINDALCO", "HINDCOPPER", "HINDZINC", "JSWSTEEL",
  "JSL", "JINDALSTEL", "LLOYDSME", "NMDC", "NATIONALUM", "SAIL",
  "TATASTEEL", "VEDL", "WELCORP",
];

// Nifty Realty (10, official NSE constituents)
export const NIFTY_REALTY_SYMBOLS = [
  "ABREL", "ANANTRAJ", "BRIGADE", "DLF", "GODREJPROP", "LODHA",
  "OBEROIRLTY", "PHOENIXLTD", "PRESTIGE", "SOBHA",
];

// BSE indices. BSE publishes no machine-readable constituent feed, so these two
// lists are hand-maintained; every symbol is validated against the NSE equity
// master by standardWatchlists.test.ts.
export const SENSEX_30_SYMBOLS = [
  "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC",
  "KOTAKBANK", "LT", "AXISBANK", "HCLTECH", "BAJFINANCE", "MARUTI", "TMPV",
  "TATASTEEL", "SUNPHARMA", "TITAN", "ASIANPAINT", "BAJAJ-AUTO", "BAJAJFINSV",
  "HINDUNILVR", "INDUSINDBK", "JSWSTEEL", "M&M", "NESTLEIND", "NTPC", "POWERGRID",
  "TECHM", "ULTRACEMCO",
];

export const BSE_BANKEX_SYMBOLS = [
  "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK",
  "BANKBARODA", "FEDERALBNK", "IDFCFIRSTB", "PNB",
];


// Helper to look up a stock by symbol from master catalog or synthesize if missing
const FNO_BY_SYMBOL = new Map(FNO_STOCKS.map((s) => [s.symbol, s]));

// Deterministic placeholder quote for a stock that has no curated mock price.
// Only used until the live feed populates the row; reference data (securityId,
// name, sector) always comes from the NSE/Dhan masters, never from here.
function placeholderQuote(sym: string): { ltp: number; changePct: number; hi: number; lo: number } {
  let h = 0;
  for (let i = 0; i < sym.length; i++) h += sym.charCodeAt(i) * (i + 7);
  const ltp = Number((50 + ((h * 37) % 4800) + (h % 97) * 1.5).toFixed(2));
  return {
    ltp,
    changePct: Number((((h % 701) - 350) / 100).toFixed(2)),
    hi: Number((ltp * 1.32).toFixed(2)),
    lo: Number((ltp * 0.72).toFixed(2)),
  };
}

// Resolve a symbol to reference data: the F&O master first (it carries curated
// quotes), then the full NSE stock master. Every symbol shipped in a standard
// watchlist resolves through one of the two - standardWatchlists.test.ts asserts it.
function findStock(sym: string): StockMasterEntry {
  const upper = sym.toUpperCase();
  const fno = FNO_BY_SYMBOL.get(upper);
  if (fno) return fno;

  const nse = NSE_STOCK_BY_SYMBOL.get(upper);
  const q = placeholderQuote(upper);
  if (nse) {
    return {
      symbol: nse.symbol,
      tradingSymbol: nse.tradingSymbol,
      securityId: nse.securityId,
      name: nse.name,
      sector: nse.sector,
      ltp: q.ltp,
      changePct: q.changePct,
      fiftyTwoWeekHigh: q.hi,
      fiftyTwoWeekLow: q.lo,
    };
  }
  return {
    symbol: upper,
    tradingSymbol: `${upper}-EQ`,
    securityId: "",
    name: upper,
    sector: "Other",
    ltp: q.ltp,
    changePct: q.changePct,
  };
}

// Generate items for a symbol list
function getItemsFromSymbols(symbols: string[], isGrouped: boolean = false): WatchlistItem[] {
  const entries = symbols.map(findStock);
  if (isGrouped) {
    entries.sort((a, b) => a.sector.localeCompare(b.sector) || a.symbol.localeCompare(b.symbol));
  }
  return entries.map((stock, idx) => toWatchlistItem(stock, idx));
}

// Major and Global Indices Mock Items
const MAJOR_INDICES_ITEMS: WatchlistItem[] = [
  { symbol: "NIFTY 50", tradingSymbol: "NIFTY 50", securityId: "13", segment: "IDX_I", name: "NIFTY 50 INDEX", sector: "Benchmark", instrumentType: "INDEX", order: 0, ltp: 24500.00, changePct: 0.65, changeAbs: 158.00 },
  { symbol: "NIFTY BANK", tradingSymbol: "NIFTY BANK", securityId: "25", segment: "IDX_I", name: "NIFTY BANK INDEX", sector: "Banking", instrumentType: "INDEX", order: 1, ltp: 52100.00, changePct: -0.25, changeAbs: -130.00 },
  { symbol: "SENSEX", tradingSymbol: "SENSEX", securityId: "51", segment: "IDX_I", name: "BSE SENSEX INDEX", sector: "Benchmark", instrumentType: "INDEX", order: 2, ltp: 81200.00, changePct: 0.55, changeAbs: 440.00 },
  { symbol: "NIFTY IT", tradingSymbol: "NIFTY IT", securityId: "29", segment: "IDX_I", name: "NIFTY IT INDEX", sector: "Information Technology", instrumentType: "INDEX", order: 3, ltp: 41250.00, changePct: 1.15, changeAbs: 470.00 },
  { symbol: "NIFTY MIDCAP 100", tradingSymbol: "NIFTY MIDCAP 100", securityId: "26", segment: "IDX_I", name: "NIFTY MIDCAP 100 INDEX", sector: "Midcap", instrumentType: "INDEX", order: 4, ltp: 58900.00, changePct: 0.45, changeAbs: 260.00 },
  { symbol: "NIFTY SMALLCAP 100", tradingSymbol: "NIFTY SMALLCAP 100", securityId: "27", segment: "IDX_I", name: "NIFTY SMALLCAP 100 INDEX", sector: "Smallcap", instrumentType: "INDEX", order: 5, ltp: 19100.00, changePct: 0.85, changeAbs: 160.00 },
  { symbol: "INDIA VIX", tradingSymbol: "INDIA VIX", securityId: "55", segment: "IDX_I", name: "INDIA VOLATILITY INDEX", sector: "Volatility", instrumentType: "INDEX", order: 6, ltp: 13.40, changePct: -3.20, changeAbs: -0.45 },
];

const GLOBAL_INDICES_ITEMS: WatchlistItem[] = [
  { symbol: "S&P 500", tradingSymbol: "S&P 500", securityId: "9001", segment: "IDX_I", name: "US S&P 500", sector: "US Markets", instrumentType: "INDEX", order: 0, ltp: 5580.20, changePct: 0.45, changeAbs: 25.10 },
  { symbol: "NASDAQ 100", tradingSymbol: "NASDAQ 100", securityId: "9002", segment: "IDX_I", name: "US NASDAQ 100", sector: "US Markets", instrumentType: "INDEX", order: 1, ltp: 19650.00, changePct: 0.80, changeAbs: 155.00 },
  { symbol: "DOW JONES", tradingSymbol: "DOW JONES", securityId: "9003", segment: "IDX_I", name: "US DOW JONES INDUSTRIAL", sector: "US Markets", instrumentType: "INDEX", order: 2, ltp: 40950.00, changePct: -0.10, changeAbs: -40.00 },
  { symbol: "FTSE 100", tradingSymbol: "FTSE 100", securityId: "9004", segment: "IDX_I", name: "UK FTSE 100", sector: "European Markets", instrumentType: "INDEX", order: 3, ltp: 8280.00, changePct: 0.20, changeAbs: 16.50 },
  { symbol: "DAX", tradingSymbol: "DAX", securityId: "9005", segment: "IDX_I", name: "GERMANY DAX 40", sector: "European Markets", instrumentType: "INDEX", order: 4, ltp: 18450.00, changePct: 0.35, changeAbs: 64.00 },
  { symbol: "NIKKEI 225", tradingSymbol: "NIKKEI 225", securityId: "9006", segment: "IDX_I", name: "JAPAN NIKKEI 225", sector: "Asian Markets", instrumentType: "INDEX", order: 5, ltp: 38700.00, changePct: 1.40, changeAbs: 530.00 },
  { symbol: "HANG SENG", tradingSymbol: "HANG SENG", securityId: "9007", segment: "IDX_I", name: "HONG KONG HANG SENG", sector: "Asian Markets", instrumentType: "INDEX", order: 6, ltp: 17650.00, changePct: -0.60, changeAbs: -105.00 },
  { symbol: "GIFT NIFTY", tradingSymbol: "GIFT NIFTY", securityId: "9008", segment: "IDX_I", name: "GIFT NIFTY 50 FUTURES", sector: "Indian Offshore", instrumentType: "INDEX", order: 7, ltp: 24580.00, changePct: 0.30, changeAbs: 73.00 },
];

// ---------------------------------------------------------------------------
// Standard Watchlists Library Definition (Exact Match to Zerodha Screenshots)
// ---------------------------------------------------------------------------
export const STANDARD_WATCHLISTS: StandardWatchlistDefinition[] = [
  // --- INDICES (Image 1 & 2) ---
  {
    id: "std-major-indices",
    name: "Major Indices",
    category: "INDICES",
    description: "Key benchmark and sectoral indices of Indian stock exchanges",
    itemCount: MAJOR_INDICES_ITEMS.length,
    getItems: () => MAJOR_INDICES_ITEMS,
  },
  {
    id: "std-global-indices",
    name: "Global Indices",
    category: "INDICES",
    description: "Major global market benchmarks (US, Europe, Asia)",
    itemCount: GLOBAL_INDICES_ITEMS.length,
    getItems: () => GLOBAL_INDICES_ITEMS,
  },
  {
    id: "std-nifty-50",
    name: "Nifty 50",
    category: "INDICES",
    description: "All 50 premier blue-chip companies of the NSE Nifty 50 index",
    itemCount: NIFTY_50_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_50_SYMBOLS, false),
  },
  {
    id: "std-nifty-50-grouped",
    name: "Nifty 50 (Grouped by sector)",
    category: "INDICES",
    description: "All 50 Nifty 50 stocks arranged and grouped by industry sector",
    isGroupedBySector: true,
    itemCount: NIFTY_50_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_50_SYMBOLS, true),
  },
  {
    id: "std-bse-sensex",
    name: "BSE Sensex",
    category: "INDICES",
    description: "All 30 component stocks of the BSE Sensex index",
    itemCount: SENSEX_30_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(SENSEX_30_SYMBOLS, false),
  },
  {
    id: "std-bse-sensex-grouped",
    name: "BSE Sensex (Grouped by sector)",
    category: "INDICES",
    description: "All 30 BSE Sensex stocks grouped by industry sector",
    isGroupedBySector: true,
    itemCount: SENSEX_30_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(SENSEX_30_SYMBOLS, true),
  },
  {
    id: "std-nifty-next-50",
    name: "Nifty Next 50",
    category: "INDICES",
    description: "All 50 companies forming the Nifty Next 50 index (Nifty 51-100)",
    itemCount: NIFTY_NEXT_50_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_NEXT_50_SYMBOLS, false),
  },
  {
    id: "std-nifty-next-50-grouped",
    name: "Nifty Next 50 (Grouped by sector)",
    category: "INDICES",
    description: "All 50 Nifty Next 50 companies grouped by industry sector",
    isGroupedBySector: true,
    itemCount: NIFTY_NEXT_50_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_NEXT_50_SYMBOLS, true),
  },
  {
    id: "std-nifty-100",
    name: "Nifty 100",
    category: "INDICES",
    description: "Top 100 large-cap Indian companies by market capitalization",
    itemCount: NIFTY_100_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_100_SYMBOLS, false),
  },
  {
    id: "std-nifty-200",
    name: "Nifty 200",
    category: "INDICES",
    description: "Top 200 companies representing over 85% of India's market capitalization",
    itemCount: NIFTY_200_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_200_SYMBOLS, false),
  },
  {
    id: "std-nifty-largemidcap-250",
    name: "Nifty LargeMidcap 250",
    category: "INDICES",
    description: "100 Large-cap and 150 Mid-cap Indian equities combined",
    itemCount: NIFTY_LARGEMIDCAP_250_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_LARGEMIDCAP_250_SYMBOLS, false),
  },
  {
    id: "std-nifty-largemidcap-250-grouped",
    name: "Nifty LargeMidcap 250 (Grouped by sector)",
    category: "INDICES",
    description: "250 Large & Mid-cap equities organized by industry sector",
    isGroupedBySector: true,
    itemCount: NIFTY_LARGEMIDCAP_250_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_LARGEMIDCAP_250_SYMBOLS, true),
  },
  {
    id: "std-nifty-midcap-150",
    name: "Nifty Midcap 150",
    category: "INDICES",
    description: "Top 150 mid-sized growth companies listed on the NSE",
    itemCount: NIFTY_MIDCAP_150_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_MIDCAP_150_SYMBOLS, false),
  },
  {
    id: "std-nifty-midcap-select",
    name: "Nifty Midcap Select",
    category: "INDICES",
    description: "25 most liquid and actively traded midcap equities",
    itemCount: NIFTY_MIDCAP_SELECT_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_MIDCAP_SELECT_SYMBOLS, false),
  },
  {
    id: "std-nifty-smallcap-250",
    name: "Nifty Smallcap 250",
    category: "INDICES",
    description: "250 emerging Indian smallcap enterprises",
    itemCount: NIFTY_SMALLCAP_250_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_SMALLCAP_250_SYMBOLS, false),
  },
  {
    id: "std-nifty-microcap-250",
    name: "Nifty Microcap 250",
    category: "INDICES",
    description: "Top 250 high-growth microcap companies listed on NSE",
    itemCount: NIFTY_MICROCAP_250_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_MICROCAP_250_SYMBOLS, false),
  },
  {
    id: "std-bank-nifty",
    name: "Bank Nifty",
    category: "INDICES",
    description: "The most liquid public and private Indian banking institutions",
    itemCount: BANK_NIFTY_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(BANK_NIFTY_SYMBOLS, false),
  },
  {
    id: "std-nifty-finnifty",
    name: "Nifty FinNifty",
    category: "INDICES",
    description: "Financial services companies (Banks, NBFCs, Insurance, AMC, exchanges)",
    itemCount: NIFTY_FINNIFTY_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_FINNIFTY_SYMBOLS, false),
  },
  {
    id: "std-nifty-it",
    name: "Nifty IT",
    category: "INDICES",
    description: "Indian software, consulting, and tech service leaders",
    itemCount: NIFTY_IT_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_IT_SYMBOLS, false),
  },
  {
    id: "std-nifty-auto",
    name: "Nifty Auto",
    category: "INDICES",
    description: "Top 15 automotive OEMs, EV manufacturers, and auto component suppliers",
    itemCount: NIFTY_AUTO_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_AUTO_SYMBOLS, false),
  },
  {
    id: "std-nifty-fmcg",
    name: "Nifty FMCG",
    category: "INDICES",
    description: "Top 15 Fast Moving Consumer Goods manufacturing corporations",
    itemCount: NIFTY_FMCG_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_FMCG_SYMBOLS, false),
  },
  {
    id: "std-nifty-pharma",
    name: "Nifty Pharma",
    category: "INDICES",
    description: "Top 20 pharmaceutical, biotech, and clinical healthcare corporations",
    itemCount: NIFTY_PHARMA_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_PHARMA_SYMBOLS, false),
  },
  {
    id: "std-nifty-metal",
    name: "Nifty Metal",
    category: "INDICES",
    description: "Steel, aluminium, copper, zinc, and mining producers",
    itemCount: NIFTY_METAL_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_METAL_SYMBOLS, false),
  },
  {
    id: "std-nifty-realty",
    name: "Nifty Realty",
    category: "INDICES",
    description: "Real estate, commercial, and residential infrastructure developers",
    itemCount: NIFTY_REALTY_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(NIFTY_REALTY_SYMBOLS, false),
  },
  {
    id: "std-bse-bankex",
    name: "BSE Bankex",
    category: "INDICES",
    description: "Top 10 banking stocks listed on the Bombay Stock Exchange",
    itemCount: BSE_BANKEX_SYMBOLS.length,
    getItems: () => getItemsFromSymbols(BSE_BANKEX_SYMBOLS, false),
  },

  // --- F&O STOCKS (Image 2) ---
  {
    id: "std-nse-fno-stocks",
    name: "NSE F&O Stocks",
    category: "F&O STOCKS",
    description: "Every equity eligible for Futures & Options contracts on the NSE",
    itemCount: FNO_STOCKS.length,
    getItems: () => FNO_208_STOCKS.map((stock, idx) => toWatchlistItem(stock, idx)),
  },
  {
    id: "std-nse-fno-stocks-grouped",
    name: "NSE F&O Stocks (Grouped by sector)",
    category: "F&O STOCKS",
    description: "Every NSE F&O eligible equity, organized and grouped by sector",
    isGroupedBySector: true,
    itemCount: FNO_STOCKS.length,
    getItems: () => {
      const sorted = [...FNO_208_STOCKS].sort(
        (a, b) => a.sector.localeCompare(b.sector) || a.symbol.localeCompare(b.symbol)
      );
      return sorted.map((stock, idx) => toWatchlistItem(stock, idx));
    },
  },
];

// ---------------------------------------------------------------------------
// Discovery and Lookup Functions
// ---------------------------------------------------------------------------

export function getStandardWatchlists(
  category: "ALL" | "INDICES" | "FNO" = "ALL"
): StandardWatchlistDefinition[] {
  if (category === "INDICES") {
    return STANDARD_WATCHLISTS.filter((w) => w.category === "INDICES");
  }
  if (category === "FNO") {
    return STANDARD_WATCHLISTS.filter((w) => w.category === "F&O STOCKS");
  }
  return STANDARD_WATCHLISTS;
}

export function getStandardWatchlistById(id: string): StandardWatchlistDefinition | undefined {
  const cleanId = id.trim().toLowerCase();
  return STANDARD_WATCHLISTS.find((w) => {
    const wid = w.id.toLowerCase();
    if (wid === cleanId || wid === `std-${cleanId}` || wid.replace("std-", "") === cleanId) return true;
    if ((cleanId === "fno-208" || cleanId === "std-fno-208") && wid === "std-nse-fno-stocks") return true;
    if ((cleanId === "fno-208-grouped" || cleanId === "std-fno-208-grouped") && wid === "std-nse-fno-stocks-grouped") return true;
    return false;
  });
}

export function searchStandardWatchlists(query: string): StandardWatchlistDefinition[] {
  const cleanQ = query.trim().toLowerCase();
  if (!cleanQ) return STANDARD_WATCHLISTS;

  return STANDARD_WATCHLISTS.filter((w) => {
    return (
      w.name.toLowerCase().includes(cleanQ) ||
      w.category.toLowerCase().includes(cleanQ) ||
      w.description.toLowerCase().includes(cleanQ) ||
      w.id.toLowerCase().includes(cleanQ)
    );
  });
}

export function instantiateStandardWatchlist(presetOrId: string | StandardWatchlistDefinition): Watchlist {
  const preset =
    typeof presetOrId === "string" ? getStandardWatchlistById(presetOrId) : presetOrId;
  if (!preset) {
    throw new Error(
      `Standard watchlist preset '${typeof presetOrId === "string" ? presetOrId : presetOrId?.id}' not found`
    );
  }

  const items = preset.getItems();
  return {
    id: `wl-std-${preset.id.replace("std-", "")}-${Date.now().toString(36)}`,
    name: preset.name,
    description: preset.description,
    isDefault: false,
    isGroupedBySector: preset.isGroupedBySector,
    columns: preset.columns || [
      "symbol",
      "ltp",
      "changeAbs",
      "changePct",
      "fiftyTwoWeekHigh",
      "fiftyTwoWeekLow",
      "volume",
      "highLow",
    ],
    items,
  };
}
