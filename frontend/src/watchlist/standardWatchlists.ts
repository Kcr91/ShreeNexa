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
  ltp?: number;
  changePct?: number;
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
// Only symbol, securityId, name and sector are reference data. Market values
// are deliberately absent and arrive solely from the authenticated live feed.
//
// Regenerate with: python scripts/fetch_nse_constituents.py
// ---------------------------------------------------------------------------
export const FNO_STOCKS: StockMasterEntry[] = [
  { symbol: "360ONE", tradingSymbol: "360ONE-EQ", securityId: "13061", name: "360 One WAM", sector: "Financial Services" },
  { symbol: "ABCAPITAL", tradingSymbol: "ABCAPITAL-EQ", securityId: "21614", name: "Aditya Birla Capital", sector: "Financial Services" },
  { symbol: "ADANIENSOL", tradingSymbol: "ADANIENSOL-EQ", securityId: "10217", name: "Adani Energy Solutions", sector: "Power" },
  { symbol: "ABB", tradingSymbol: "ABB-EQ", securityId: "13", name: "ABB", sector: "Capital Goods" },
  { symbol: "ADANIPORTS", tradingSymbol: "ADANIPORTS-EQ", securityId: "15083", name: "Adani Ports & SEZ", sector: "Services" },
  { symbol: "AMBER", tradingSymbol: "AMBER-EQ", securityId: "1185", name: "Amber Enterprises", sector: "Consumer Durables" },
  { symbol: "ASIANPAINT", tradingSymbol: "ASIANPAINT-EQ", securityId: "236", name: "Asian Paints", sector: "Consumer Durables" },
  { symbol: "AMBUJACEM", tradingSymbol: "AMBUJACEM-EQ", securityId: "1270", name: "Ambuja Cements", sector: "Construction Materials" },
  { symbol: "ADANIENT", tradingSymbol: "ADANIENT-EQ", securityId: "25", name: "Adani Enterprises", sector: "Metals & Mining" },
  { symbol: "BAJAJ-AUTO", tradingSymbol: "BAJAJ-AUTO-EQ", securityId: "16669", name: "Bajaj Auto", sector: "Automobile and Auto Components" },
  { symbol: "BAJAJHLDNG", tradingSymbol: "BAJAJHLDNG-EQ", securityId: "305", name: "Bajaj Holdings & Investments", sector: "Financial Services" },
  { symbol: "APLAPOLLO", tradingSymbol: "APLAPOLLO-EQ", securityId: "25780", name: "APL Apollo Tubes", sector: "Capital Goods" },
  { symbol: "ADANIGREEN", tradingSymbol: "ADANIGREEN-EQ", securityId: "3563", name: "Adani Green Energy", sector: "Power" },
  { symbol: "AUROPHARMA", tradingSymbol: "AUROPHARMA-EQ", securityId: "275", name: "Aurobindo Pharma", sector: "Healthcare" },
  { symbol: "AXISBANK", tradingSymbol: "AXISBANK-EQ", securityId: "5900", name: "Axis Bank", sector: "Financial Services" },
  { symbol: "BOSCHLTD", tradingSymbol: "BOSCHLTD-EQ", securityId: "2181", name: "Bosch", sector: "Automobile and Auto Components" },
  { symbol: "BRITANNIA", tradingSymbol: "BRITANNIA-EQ", securityId: "547", name: "Britannia Industries", sector: "Fast Moving Consumer Goods" },
  { symbol: "CDSL", tradingSymbol: "CDSL-EQ", securityId: "21174", name: "CDSL", sector: "Financial Services" },
  { symbol: "BANDHANBNK", tradingSymbol: "BANDHANBNK-EQ", securityId: "2263", name: "Bandhan Bank", sector: "Financial Services" },
  { symbol: "BANKBARODA", tradingSymbol: "BANKBARODA-EQ", securityId: "4668", name: "Bank of Baroda", sector: "Financial Services" },
  { symbol: "BDL", tradingSymbol: "BDL-EQ", securityId: "2144", name: "Bharat Dynamics", sector: "Capital Goods" },
  { symbol: "BHARATFORG", tradingSymbol: "BHARATFORG-EQ", securityId: "422", name: "Bharat Forge", sector: "Automobile and Auto Components" },
  { symbol: "COALINDIA", tradingSymbol: "COALINDIA-EQ", securityId: "20374", name: "Coal India", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "BHARTIARTL", tradingSymbol: "BHARTIARTL-EQ", securityId: "10604", name: "Bharti Airtel", sector: "Telecommunication" },
  { symbol: "BLUESTARCO", tradingSymbol: "BLUESTARCO-EQ", securityId: "8311", name: "Blue Star", sector: "Consumer Durables" },
  { symbol: "BPCL", tradingSymbol: "BPCL-EQ", securityId: "526", name: "Bharat Petroleum", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "ALKEM", tradingSymbol: "ALKEM-EQ", securityId: "11703", name: "Alkem Laboratories", sector: "Healthcare" },
  { symbol: "CAMS", tradingSymbol: "CAMS-EQ", securityId: "342", name: "CAMS", sector: "Financial Services" },
  { symbol: "CHOLAFIN", tradingSymbol: "CHOLAFIN-EQ", securityId: "19257", name: "CIFCL-7.5%-30092026-NCD", sector: "Financial Services" },
  { symbol: "CIPLA", tradingSymbol: "CIPLA-EQ", securityId: "694", name: "Cipla", sector: "Healthcare" },
  { symbol: "COCHINSHIP", tradingSymbol: "COCHINSHIP-EQ", securityId: "21508", name: "Cochin Shipyard", sector: "Capital Goods" },
  { symbol: "COLPAL", tradingSymbol: "COLPAL-EQ", securityId: "15141", name: "Colgate Palmolive", sector: "Fast Moving Consumer Goods" },
  { symbol: "COFORGE", tradingSymbol: "COFORGE-EQ", securityId: "11543", name: "Coforge", sector: "Information Technology" },
  { symbol: "CROMPTON", tradingSymbol: "CROMPTON-EQ", securityId: "17094", name: "Crompton Greaves", sector: "Consumer Durables" },
  { symbol: "CONCOR", tradingSymbol: "CONCOR-EQ", securityId: "4749", name: "Container Corporation of India", sector: "Services" },
  { symbol: "DABUR", tradingSymbol: "DABUR-EQ", securityId: "772", name: "Dabur India", sector: "Fast Moving Consumer Goods" },
  { symbol: "ANGELONE", tradingSymbol: "ANGELONE-EQ", securityId: "324", name: "Angel One", sector: "Financial Services" },
  { symbol: "APOLLOHOSP", tradingSymbol: "APOLLOHOSP-EQ", securityId: "157", name: "Apollo Hospitals", sector: "Healthcare" },
  { symbol: "DELHIVERY", tradingSymbol: "DELHIVERY-EQ", securityId: "9599", name: "Delhivery", sector: "Services" },
  { symbol: "DIVISLAB", tradingSymbol: "DIVISLAB-EQ", securityId: "10940", name: "Divis Laboratories", sector: "Healthcare" },
  { symbol: "DLF", tradingSymbol: "DLF-EQ", securityId: "14732", name: "DLF", sector: "Realty" },
  { symbol: "DMART", tradingSymbol: "DMART-EQ", securityId: "19913", name: "Avenue Supermarts DMart", sector: "Consumer Services" },
  { symbol: "DRREDDY", tradingSymbol: "DRREDDY-EQ", securityId: "881", name: "Dr Reddys Laboratories", sector: "Healthcare" },
  { symbol: "DIXON", tradingSymbol: "DIXON-EQ", securityId: "21690", name: "Dixon Technologies", sector: "Consumer Durables" },
  { symbol: "ETERNAL", tradingSymbol: "ETERNAL-EQ", securityId: "5097", name: "Eternal", sector: "Consumer Services" },
  { symbol: "FORCEMOT", tradingSymbol: "FORCEMOT-EQ", securityId: "11573", name: "Force Motors", sector: "Automobile and Auto Components" },
  { symbol: "FORTIS", tradingSymbol: "FORTIS-EQ", securityId: "14592", name: "Fortis Healthcare", sector: "Healthcare" },
  { symbol: "GLENMARK", tradingSymbol: "GLENMARK-EQ", securityId: "7406", name: "Glenmark Pharmaceuticals", sector: "Healthcare" },
  { symbol: "GODFRYPHLP", tradingSymbol: "GODFRYPHLP-EQ", securityId: "1181", name: "Godfrey Phillips", sector: "Fast Moving Consumer Goods" },
  { symbol: "BANKINDIA", tradingSymbol: "BANKINDIA-EQ", securityId: "4745", name: "Bank of India", sector: "Financial Services" },
  { symbol: "GODREJPROP", tradingSymbol: "GODREJPROP-EQ", securityId: "17875", name: "Godrej Properties", sector: "Realty" },
  { symbol: "GODREJCP", tradingSymbol: "GODREJCP-EQ", securityId: "10099", name: "Godrej Consumer Products", sector: "Fast Moving Consumer Goods" },
  { symbol: "HCLTECH", tradingSymbol: "HCLTECH-EQ", securityId: "7229", name: "HCL Technologies", sector: "Information Technology" },
  { symbol: "HDFCBANK", tradingSymbol: "HDFCBANK-EQ", securityId: "1333", name: "HDFC Bank", sector: "Financial Services" },
  { symbol: "GRASIM", tradingSymbol: "GRASIM-EQ", securityId: "1232", name: "Grasim Industries", sector: "Construction Materials" },
  { symbol: "GVT&D", tradingSymbol: "GVT&D-EQ", securityId: "16783", name: "GE Vernova T&D", sector: "Capital Goods" },
  { symbol: "HAVELLS", tradingSymbol: "HAVELLS-EQ", securityId: "9819", name: "Havells", sector: "Consumer Durables" },
  { symbol: "HDFCLIFE", tradingSymbol: "HDFCLIFE-EQ", securityId: "467", name: "HDFC Life Insurance", sector: "Financial Services" },
  { symbol: "BEL", tradingSymbol: "BEL-EQ", securityId: "383", name: "Bharat Electronics", sector: "Capital Goods" },
  { symbol: "BHEL", tradingSymbol: "BHEL-EQ", securityId: "438", name: "Bharat Heavy Electricals", sector: "Capital Goods" },
  { symbol: "HINDALCO", tradingSymbol: "HINDALCO-EQ", securityId: "1363", name: "Hindalco Industries", sector: "Metals & Mining" },
  { symbol: "BIOCON", tradingSymbol: "BIOCON-EQ", securityId: "11373", name: "Biocon", sector: "Healthcare" },
  { symbol: "HINDUNILVR", tradingSymbol: "HINDUNILVR-EQ", securityId: "1394", name: "Hindustan Unilever", sector: "Fast Moving Consumer Goods" },
  { symbol: "HINDZINC", tradingSymbol: "HINDZINC-EQ", securityId: "1424", name: "Hindustan Zinc", sector: "Metals & Mining" },
  { symbol: "IDFCFIRSTB", tradingSymbol: "IDFCFIRSTB-EQ", securityId: "11184", name: "IDFC First Bank", sector: "Financial Services" },
  { symbol: "INDUSINDBK", tradingSymbol: "INDUSINDBK-EQ", securityId: "5258", name: "Indusind Bank", sector: "Financial Services" },
  { symbol: "ICICIGI", tradingSymbol: "ICICIGI-EQ", securityId: "21770", name: "ICICI Lombard General Insurance", sector: "Financial Services" },
  { symbol: "CGPOWER", tradingSymbol: "CGPOWER-EQ", securityId: "760", name: "CG Power & Industrial Solutions", sector: "Capital Goods" },
  { symbol: "IRFC", tradingSymbol: "IRFC-EQ", securityId: "2029", name: "IRFC", sector: "Financial Services" },
  { symbol: "JINDALSTEL", tradingSymbol: "JINDALSTEL-EQ", securityId: "6733", name: "Jindal Steel", sector: "Metals & Mining" },
  { symbol: "JIOFIN", tradingSymbol: "JIOFIN-EQ", securityId: "18143", name: "Jio Financial Services", sector: "Financial Services" },
  { symbol: "IEX", tradingSymbol: "IEX-EQ", securityId: "220", name: "Indian Energy Exchange", sector: "Financial Services" },
  { symbol: "INDHOTEL", tradingSymbol: "INDHOTEL-EQ", securityId: "1512", name: "Indian Hotels Company", sector: "Consumer Services" },
  { symbol: "INDIANB", tradingSymbol: "INDIANB-EQ", securityId: "14309", name: "Indian Bank", sector: "Financial Services" },
  { symbol: "JSWENERGY", tradingSymbol: "JSWENERGY-EQ", securityId: "17869", name: "JSW Energy", sector: "Power" },
  { symbol: "JSWSTEEL", tradingSymbol: "JSWSTEEL-EQ", securityId: "11723", name: "JSW Steel", sector: "Metals & Mining" },
  { symbol: "KAYNES", tradingSymbol: "KAYNES-EQ", securityId: "12092", name: "Kaynes Technology India", sector: "Capital Goods" },
  { symbol: "KEI", tradingSymbol: "KEI-EQ", securityId: "13310", name: "KEI Industries", sector: "Capital Goods" },
  { symbol: "INFY", tradingSymbol: "INFY-EQ", securityId: "1594", name: "Infosys", sector: "Information Technology" },
  { symbol: "INOXWIND", tradingSymbol: "INOXWIND-EQ", securityId: "7852", name: "Inox Wind", sector: "Capital Goods" },
  { symbol: "ITC", tradingSymbol: "ITC-EQ", securityId: "1660", name: "ITC", sector: "Fast Moving Consumer Goods" },
  { symbol: "KPITTECH", tradingSymbol: "KPITTECH-EQ", securityId: "9683", name: "KPIT Technologies", sector: "Information Technology" },
  { symbol: "JUBLFOOD", tradingSymbol: "JUBLFOOD-EQ", securityId: "18096", name: "Jubilant FoodWorks", sector: "Consumer Services" },
  { symbol: "LT", tradingSymbol: "LT-EQ", securityId: "11483", name: "Larsen & Toubro", sector: "Construction" },
  { symbol: "M&M", tradingSymbol: "M&M-EQ", securityId: "2031", name: "Mahindra & Mahindra", sector: "Automobile and Auto Components" },
  { symbol: "KALYANKJIL", tradingSymbol: "KALYANKJIL-EQ", securityId: "2955", name: "Kalyan Jewellers", sector: "Consumer Durables" },
  { symbol: "MANKIND", tradingSymbol: "MANKIND-EQ", securityId: "15380", name: "Mankind Pharma", sector: "Healthcare" },
  { symbol: "MARICO", tradingSymbol: "MARICO-EQ", securityId: "4067", name: "Marico", sector: "Fast Moving Consumer Goods" },
  { symbol: "ADANIPOWER", tradingSymbol: "ADANIPOWER-EQ", securityId: "17388", name: "Adani Power", sector: "Power" },
  { symbol: "MCX", tradingSymbol: "MCX-EQ", securityId: "31181", name: "MCX", sector: "Financial Services" },
  { symbol: "NAM-INDIA", tradingSymbol: "NAM-INDIA-EQ", securityId: "357", name: "Nippon Life India AMC", sector: "Financial Services" },
  { symbol: "KFINTECH", tradingSymbol: "KFINTECH-EQ", securityId: "13359", name: "KFin Technologies", sector: "Financial Services" },
  { symbol: "NESTLEIND", tradingSymbol: "NESTLEIND-EQ", securityId: "17963", name: "Nestle", sector: "Fast Moving Consumer Goods" },
  { symbol: "EICHERMOT", tradingSymbol: "EICHERMOT-EQ", securityId: "910", name: "Eicher Motors", sector: "Automobile and Auto Components" },
  { symbol: "LODHA", tradingSymbol: "LODHA-EQ", securityId: "3220", name: "Lodha Developers", sector: "Realty" },
  { symbol: "FEDERALBNK", tradingSymbol: "FEDERALBNK-EQ", securityId: "1023", name: "Federal Bank", sector: "Financial Services" },
  { symbol: "OBEROIRLTY", tradingSymbol: "OBEROIRLTY-EQ", securityId: "20242", name: "Oberoi Realty", sector: "Realty" },
  { symbol: "LTM", tradingSymbol: "LTM-EQ", securityId: "17818", name: "LTM", sector: "Information Technology" },
  { symbol: "LUPIN", tradingSymbol: "LUPIN-EQ", securityId: "10440", name: "Lupin", sector: "Healthcare" },
  { symbol: "PAGEIND", tradingSymbol: "PAGEIND-EQ", securityId: "14413", name: "Page Industries", sector: "Textiles" },
  { symbol: "MANAPPURAM", tradingSymbol: "MANAPPURAM-EQ", securityId: "19061", name: "Manappuram Finance", sector: "Financial Services" },
  { symbol: "PAYTM", tradingSymbol: "PAYTM-EQ", securityId: "6705", name: "One 97 Communications", sector: "Financial Services" },
  { symbol: "PFC", tradingSymbol: "PFC-EQ", securityId: "14299", name: "Power Finance Corporation", sector: "Financial Services" },
  { symbol: "PGEL", tradingSymbol: "PGEL-EQ", securityId: "25358", name: "PG Electroplast", sector: "Consumer Durables" },
  { symbol: "MARUTI", tradingSymbol: "MARUTI-EQ", securityId: "10999", name: "Maruti Suzuki", sector: "Automobile and Auto Components" },
  { symbol: "MAXHEALTH", tradingSymbol: "MAXHEALTH-EQ", securityId: "22377", name: "Max Healthcare Institute", sector: "Healthcare" },
  { symbol: "PHOENIXLTD", tradingSymbol: "PHOENIXLTD-EQ", securityId: "14552", name: "Phoenix Mills", sector: "Realty" },
  { symbol: "PNB", tradingSymbol: "PNB-EQ", securityId: "10666", name: "Punjab National Bank", sector: "Financial Services" },
  { symbol: "MOTHERSON", tradingSymbol: "MOTHERSON-EQ", securityId: "25510", name: "SMIL-6.5%-20092027-NCD", sector: "Automobile and Auto Components" },
  { symbol: "POLYCAB", tradingSymbol: "POLYCAB-EQ", securityId: "9590", name: "Polycab", sector: "Capital Goods" },
  { symbol: "POWERINDIA", tradingSymbol: "POWERINDIA-EQ", securityId: "18457", name: "Hitachi Energy", sector: "Capital Goods" },
  { symbol: "NMDC", tradingSymbol: "NMDC-EQ", securityId: "15332", name: "NMDC", sector: "Metals & Mining" },
  { symbol: "OFSS", tradingSymbol: "OFSS-EQ", securityId: "10738", name: "Oracle Financial Services Software", sector: "Information Technology" },
  { symbol: "PRESTIGE", tradingSymbol: "PRESTIGE-EQ", securityId: "20302", name: "Prestige Estates Projects", sector: "Realty" },
  { symbol: "OIL", tradingSymbol: "OIL-EQ", securityId: "17438", name: "Oil India", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "ONGC", tradingSymbol: "ONGC-EQ", securityId: "2475", name: "Oil & Natural Gas Corporation", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "PATANJALI", tradingSymbol: "PATANJALI-EQ", securityId: "17029", name: "Patanjali Foods", sector: "Fast Moving Consumer Goods" },
  { symbol: "RECLTD", tradingSymbol: "RECLTD-EQ", securityId: "15355", name: "REC", sector: "Financial Services" },
  { symbol: "SBILIFE", tradingSymbol: "SBILIFE-EQ", securityId: "21808", name: "SBI Life Insurance", sector: "Financial Services" },
  { symbol: "GMRAIRPORT", tradingSymbol: "GMRAIRPORT-EQ", securityId: "13528", name: "GMR Airports", sector: "Services" },
  { symbol: "SBIN", tradingSymbol: "SBIN-EQ", securityId: "3045", name: "State Bank of India", sector: "Financial Services" },
  { symbol: "SHREECEM", tradingSymbol: "SHREECEM-EQ", securityId: "3103", name: "Shree Cement", sector: "Construction Materials" },
  { symbol: "TATACONSUM", tradingSymbol: "TATACONSUM-EQ", securityId: "3432", name: "Tata Consumer Products", sector: "Fast Moving Consumer Goods" },
  { symbol: "PETRONET", tradingSymbol: "PETRONET-EQ", securityId: "11351", name: "Petronet LNG", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "TATAELXSI", tradingSymbol: "TATAELXSI-EQ", securityId: "3411", name: "Tata Elxsi", sector: "Information Technology" },
  { symbol: "TATASTEEL", tradingSymbol: "TATASTEEL-EQ", securityId: "3499", name: "Tata Steel", sector: "Metals & Mining" },
  { symbol: "TMPV", tradingSymbol: "TMPV-EQ", securityId: "3456", name: "Tata Motors Passenger Vehicles", sector: "Automobile and Auto Components" },
  { symbol: "UPL", tradingSymbol: "UPL-EQ", securityId: "11287", name: "UPL", sector: "Chemicals" },
  { symbol: "PIDILITIND", tradingSymbol: "PIDILITIND-EQ", securityId: "2664", name: "Pidilite Industries", sector: "Chemicals" },
  { symbol: "WAAREEENER", tradingSymbol: "WAAREEENER-EQ", securityId: "25907", name: "Waaree Energies", sector: "Capital Goods" },
  { symbol: "PIIND", tradingSymbol: "PIIND-EQ", securityId: "24184", name: "PI Industries", sector: "Chemicals" },
  { symbol: "BAJAJFINSV", tradingSymbol: "BAJAJFINSV-EQ", securityId: "16675", name: "Bajaj Finserv", sector: "Financial Services" },
  { symbol: "POLICYBZR", tradingSymbol: "POLICYBZR-EQ", securityId: "6656", name: "PB FinTech", sector: "Financial Services" },
  { symbol: "PREMIERENE", tradingSymbol: "PREMIERENE-EQ", securityId: "25049", name: "Premier Energies", sector: "Capital Goods" },
  { symbol: "RADICO", tradingSymbol: "RADICO-EQ", securityId: "10990", name: "Radico Khaitan", sector: "Fast Moving Consumer Goods" },
  { symbol: "RBLBANK", tradingSymbol: "RBLBANK-EQ", securityId: "18391", name: "RBL Bank", sector: "Financial Services" },
  { symbol: "SAIL", tradingSymbol: "SAIL-EQ", securityId: "2963", name: "Steel Authority of India", sector: "Metals & Mining" },
  { symbol: "SOLARINDS", tradingSymbol: "SOLARINDS-EQ", securityId: "13332", name: "Solar Industries", sector: "Chemicals" },
  { symbol: "SUNPHARMA", tradingSymbol: "SUNPHARMA-EQ", securityId: "3351", name: "Sun Pharmaceutical", sector: "Healthcare" },
  { symbol: "SUPREMEIND", tradingSymbol: "SUPREMEIND-EQ", securityId: "3363", name: "Supreme Industries", sector: "Capital Goods" },
  { symbol: "SUZLON", tradingSymbol: "SUZLON-EQ", securityId: "12018", name: "Suzlon Energy", sector: "Capital Goods" },
  { symbol: "SWIGGY", tradingSymbol: "SWIGGY-EQ", securityId: "27066", name: "Swiggy", sector: "Consumer Services" },
  { symbol: "TATAPOWER", tradingSymbol: "TATAPOWER-EQ", securityId: "3426", name: "Tata Power", sector: "Power" },
  { symbol: "TCS", tradingSymbol: "TCS-EQ", securityId: "11536", name: "Tata Consultancy Services", sector: "Information Technology" },
  { symbol: "TIINDIA", tradingSymbol: "TIINDIA-EQ", securityId: "312", name: "Tube Investment", sector: "Automobile and Auto Components" },
  { symbol: "TITAN", tradingSymbol: "TITAN-EQ", securityId: "3506", name: "Titan", sector: "Consumer Durables" },
  { symbol: "TVSMOTOR", tradingSymbol: "TVSMOTOR-EQ", securityId: "8479", name: "TVS Motors", sector: "Automobile and Auto Components" },
  { symbol: "UNIONBANK", tradingSymbol: "UNIONBANK-EQ", securityId: "10753", name: "Union Bank of India", sector: "Financial Services" },
  { symbol: "VBL", tradingSymbol: "VBL-EQ", securityId: "18921", name: "Varun Beverages", sector: "Fast Moving Consumer Goods" },
  { symbol: "VEDL", tradingSymbol: "VEDL-EQ", securityId: "3063", name: "Vedanta", sector: "Metals & Mining" },
  { symbol: "ZYDUSLIFE", tradingSymbol: "ZYDUSLIFE-EQ", securityId: "7929", name: "Zydus Life Science", sector: "Healthcare" },
  { symbol: "HEROMOTOCO", tradingSymbol: "HEROMOTOCO-EQ", securityId: "1348", name: "Hero Motocorp", sector: "Automobile and Auto Components" },
  { symbol: "HYUNDAI", tradingSymbol: "HYUNDAI-EQ", securityId: "25844", name: "Hyundai Motor India", sector: "Automobile and Auto Components" },
  { symbol: "ICICIBANK", tradingSymbol: "ICICIBANK-EQ", securityId: "4963", name: "ICICI Bank", sector: "Financial Services" },
  { symbol: "INDIGO", tradingSymbol: "INDIGO-EQ", securityId: "11195", name: "Interglobe Aviation", sector: "Services" },
  { symbol: "BSE", tradingSymbol: "BSE-EQ", securityId: "19585", name: "BSE", sector: "Financial Services" },
  { symbol: "LICHSGFIN", tradingSymbol: "LICHSGFIN-EQ", securityId: "1997", name: "LIC Housing Finance", sector: "Financial Services" },
  { symbol: "LTF", tradingSymbol: "LTF-EQ", securityId: "24948", name: "L&T Finance", sector: "Financial Services" },
  { symbol: "HDFCAMC", tradingSymbol: "HDFCAMC-EQ", securityId: "4244", name: "HDFC AMC", sector: "Financial Services" },
  { symbol: "MOTILALOFS", tradingSymbol: "MOTILALOFS-EQ", securityId: "14947", name: "Motilal Oswal Financial Services", sector: "Financial Services" },
  { symbol: "MPHASIS", tradingSymbol: "MPHASIS-EQ", securityId: "4503", name: "Mphasis", sector: "Information Technology" },
  { symbol: "NATIONALUM", tradingSymbol: "NATIONALUM-EQ", securityId: "6364", name: "NALCO", sector: "Metals & Mining" },
  { symbol: "NBCC", tradingSymbol: "NBCC-EQ", securityId: "31415", name: "NBCC", sector: "Construction" },
  { symbol: "NYKAA", tradingSymbol: "NYKAA-EQ", securityId: "6545", name: "Nykaa", sector: "Consumer Services" },
  { symbol: "ICICIPRULI", tradingSymbol: "ICICIPRULI-EQ", securityId: "18652", name: "ICICI Prudential Life Insurance", sector: "Financial Services" },
  { symbol: "PERSISTENT", tradingSymbol: "PERSISTENT-EQ", securityId: "18365", name: "Persistent Systems", sector: "Information Technology" },
  { symbol: "PNBHOUSING", tradingSymbol: "PNBHOUSING-EQ", securityId: "18908", name: "PNB Housing Finance", sector: "Financial Services" },
  { symbol: "POWERGRID", tradingSymbol: "POWERGRID-EQ", securityId: "14977", name: "Power Grid Corporation of India", sector: "Power" },
  { symbol: "LAURUSLABS", tradingSymbol: "LAURUSLABS-EQ", securityId: "19234", name: "Laurus Labs", sector: "Healthcare" },
  { symbol: "RELIANCE", tradingSymbol: "RELIANCE-EQ", securityId: "2885", name: "Reliance Industries", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "MAZDOCK", tradingSymbol: "MAZDOCK-EQ", securityId: "509", name: "Mazagon Dock Shipbuilders", sector: "Capital Goods" },
  { symbol: "SONACOMS", tradingSymbol: "SONACOMS-EQ", securityId: "4684", name: "Sona BLW Precision Forgings", sector: "Automobile and Auto Components" },
  { symbol: "NAUKRI", tradingSymbol: "NAUKRI-EQ", securityId: "13751", name: "Info Edge", sector: "Consumer Services" },
  { symbol: "SRF", tradingSymbol: "SRF-EQ", securityId: "3273", name: "SRF", sector: "Chemicals" },
  { symbol: "TECHM", tradingSymbol: "TECHM-EQ", securityId: "13538", name: "Tech Mahindra", sector: "Information Technology" },
  { symbol: "ULTRACEMCO", tradingSymbol: "ULTRACEMCO-EQ", securityId: "11532", name: "UltraTech Cement", sector: "Construction Materials" },
  { symbol: "UNOMINDA", tradingSymbol: "UNOMINDA-EQ", securityId: "14154", name: "UNO Minda", sector: "Automobile and Auto Components" },
  { symbol: "VMM", tradingSymbol: "VMM-EQ", securityId: "27969", name: "Vishal Mega Mart", sector: "Consumer Services" },
  { symbol: "WIPRO", tradingSymbol: "WIPRO-EQ", securityId: "3787", name: "Wipro", sector: "Information Technology" },
  { symbol: "ASTRAL", tradingSymbol: "ASTRAL-EQ", securityId: "14418", name: "Astral", sector: "Capital Goods" },
  { symbol: "BAJFINANCE", tradingSymbol: "BAJFINANCE-EQ", securityId: "317", name: "Bajaj Finance", sector: "Financial Services" },
  { symbol: "UNITDSPR", tradingSymbol: "UNITDSPR-EQ", securityId: "10447", name: "United Spirits", sector: "Fast Moving Consumer Goods" },
  { symbol: "ASHOKLEY", tradingSymbol: "ASHOKLEY-EQ", securityId: "212", name: "Ashok Leyland", sector: "Capital Goods" },
  { symbol: "MUTHOOTFIN", tradingSymbol: "MUTHOOTFIN-EQ", securityId: "23650", name: "Muthoot Finance", sector: "Financial Services" },
  { symbol: "CUMMINSIND", tradingSymbol: "CUMMINSIND-EQ", securityId: "1901", name: "Cummins", sector: "Capital Goods" },
  { symbol: "GAIL", tradingSymbol: "GAIL-EQ", securityId: "4717", name: "GAIL", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "SIEMENS", tradingSymbol: "SIEMENS-EQ", securityId: "3150", name: "Siemens", sector: "Capital Goods" },
  { symbol: "MFSL", tradingSymbol: "MFSL-EQ", securityId: "2142", name: "Max Financial Services", sector: "Financial Services" },
  { symbol: "NHPC", tradingSymbol: "NHPC-EQ", securityId: "17400", name: "NHPC", sector: "Power" },
  { symbol: "NTPC", tradingSymbol: "NTPC-EQ", securityId: "11630", name: "NTPC", sector: "Power" },
  { symbol: "TORNTPHARM", tradingSymbol: "TORNTPHARM-EQ", securityId: "3518", name: "Torrent Pharmaceuticals", sector: "Healthcare" },
  { symbol: "RVNL", tradingSymbol: "RVNL-EQ", securityId: "9552", name: "Rail Vikas Nigam", sector: "Construction" },
  { symbol: "KOTAKBANK", tradingSymbol: "KOTAKBANK-EQ", securityId: "1922", name: "Kotak Bank", sector: "Financial Services" },
  { symbol: "LICI", tradingSymbol: "LICI-EQ", securityId: "9480", name: "LIC of India", sector: "Financial Services" },
  { symbol: "AUBANK", tradingSymbol: "AUBANK-EQ", securityId: "21238", name: "AU Small Finance Bank", sector: "Financial Services" },
  { symbol: "HAL", tradingSymbol: "HAL-EQ", securityId: "2303", name: "Hindustan Aeronautics", sector: "Capital Goods" },
  { symbol: "IDEA", tradingSymbol: "IDEA-EQ", securityId: "14366", name: "Vodafone Idea", sector: "Telecommunication" },
  { symbol: "INDUSTOWER", tradingSymbol: "INDUSTOWER-EQ", securityId: "29135", name: "Indus Towers", sector: "Telecommunication" },
  { symbol: "IOC", tradingSymbol: "IOC-EQ", securityId: "1624", name: "Indian Oil Corporation", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "IREDA", tradingSymbol: "IREDA-EQ", securityId: "20261", name: "IREDA", sector: "Financial Services" },
  { symbol: "TRENT", tradingSymbol: "TRENT-EQ", securityId: "1964", name: "Trent", sector: "Consumer Services" },
  { symbol: "SBICARD", tradingSymbol: "SBICARD-EQ", securityId: "17971", name: "SBI Cards", sector: "Financial Services" },
  { symbol: "SHRIRAMFIN", tradingSymbol: "SHRIRAMFIN-EQ", securityId: "4306", name: "Shriram Finance", sector: "Financial Services" },
  { symbol: "CANBK", tradingSymbol: "CANBK-EQ", securityId: "10794", name: "Canara Bank", sector: "Financial Services" },
  { symbol: "YESBANK", tradingSymbol: "YESBANK-EQ", securityId: "11915", name: "Yes Bank", sector: "Financial Services" },
  { symbol: "VOLTAS", tradingSymbol: "VOLTAS-EQ", securityId: "3718", name: "Voltas", sector: "Consumer Durables" },
  { symbol: "HINDPETRO", tradingSymbol: "HINDPETRO-EQ", securityId: "1406", name: "Hindustan Petroleum", sector: "Oil Gas & Consumable Fuels" },
  { symbol: "ATHERENERG", tradingSymbol: "ATHERENERG-EQ", securityId: "757645", name: "Ather Energy", sector: "Automobile and Auto Components" },
  { symbol: "MAHABANK", tradingSymbol: "MAHABANK-EQ", securityId: "11377", name: "Bank of Maharashtra", sector: "Financial Services" },
  { symbol: "SAGILITY", tradingSymbol: "SAGILITY-EQ", securityId: "27052", name: "Sagility", sector: "Information Technology" },
];

/** @deprecated Renamed to FNO_STOCKS - the NSE F&O list is no longer 208 names. */
export const FNO_208_STOCKS = FNO_STOCKS;

// Helper to convert StockMasterEntry to WatchlistItem
function toWatchlistItem(stock: StockMasterEntry, order: number): WatchlistItem {
  return {
    symbol: stock.symbol,
    segment: stock.segment || "NSE_EQ",
    securityId: stock.securityId,
    tradingSymbol: stock.tradingSymbol,
    name: stock.name,
    sector: stock.sector,
    instrumentType: "EQUITY",
    order,
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


// Helper to look up a stock by symbol from the identity catalogs.
const FNO_BY_SYMBOL = new Map(FNO_STOCKS.map((s) => [s.symbol, s]));

// Resolve a symbol to reference data: the F&O master first, then the full NSE
// stock master. Every symbol shipped in a standard
// watchlist resolves through one of the two - standardWatchlists.test.ts asserts it.
function findStock(sym: string): StockMasterEntry {
  const upper = sym.toUpperCase();
  const fno = FNO_BY_SYMBOL.get(upper);
  if (fno) return fno;

  const nse = NSE_STOCK_BY_SYMBOL.get(upper);
  if (nse) {
    return {
      symbol: nse.symbol,
      tradingSymbol: nse.tradingSymbol,
      securityId: nse.securityId,
      name: nse.name,
      sector: nse.sector,
    };
  }
  return {
    symbol: upper,
    tradingSymbol: `${upper}-EQ`,
    securityId: "",
    name: upper,
    sector: "Other",
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
  { symbol: "NIFTY 50", tradingSymbol: "NIFTY 50", securityId: "13", segment: "IDX_I", name: "NIFTY 50 INDEX", sector: "Benchmark", instrumentType: "INDEX", order: 0 },
  { symbol: "NIFTY BANK", tradingSymbol: "NIFTY BANK", securityId: "25", segment: "IDX_I", name: "NIFTY BANK INDEX", sector: "Banking", instrumentType: "INDEX", order: 1 },
  { symbol: "SENSEX", tradingSymbol: "SENSEX", securityId: "51", segment: "IDX_I", name: "BSE SENSEX INDEX", sector: "Benchmark", instrumentType: "INDEX", order: 2 },
  { symbol: "NIFTY IT", tradingSymbol: "NIFTY IT", securityId: "29", segment: "IDX_I", name: "NIFTY IT INDEX", sector: "Information Technology", instrumentType: "INDEX", order: 3 },
  { symbol: "NIFTY MIDCAP 100", tradingSymbol: "NIFTY MIDCAP 100", securityId: "26", segment: "IDX_I", name: "NIFTY MIDCAP 100 INDEX", sector: "Midcap", instrumentType: "INDEX", order: 4 },
  { symbol: "NIFTY SMALLCAP 100", tradingSymbol: "NIFTY SMALLCAP 100", securityId: "27", segment: "IDX_I", name: "NIFTY SMALLCAP 100 INDEX", sector: "Smallcap", instrumentType: "INDEX", order: 5 },
  { symbol: "INDIA VIX", tradingSymbol: "INDIA VIX", securityId: "55", segment: "IDX_I", name: "INDIA VOLATILITY INDEX", sector: "Volatility", instrumentType: "INDEX", order: 6 },
];

const GLOBAL_INDICES_ITEMS: WatchlistItem[] = [
  { symbol: "S&P 500", tradingSymbol: "S&P 500", securityId: "9001", segment: "IDX_I", name: "US S&P 500", sector: "US Markets", instrumentType: "INDEX", order: 0 },
  { symbol: "NASDAQ 100", tradingSymbol: "NASDAQ 100", securityId: "9002", segment: "IDX_I", name: "US NASDAQ 100", sector: "US Markets", instrumentType: "INDEX", order: 1 },
  { symbol: "DOW JONES", tradingSymbol: "DOW JONES", securityId: "9003", segment: "IDX_I", name: "US DOW JONES INDUSTRIAL", sector: "US Markets", instrumentType: "INDEX", order: 2 },
  { symbol: "FTSE 100", tradingSymbol: "FTSE 100", securityId: "9004", segment: "IDX_I", name: "UK FTSE 100", sector: "European Markets", instrumentType: "INDEX", order: 3 },
  { symbol: "DAX", tradingSymbol: "DAX", securityId: "9005", segment: "IDX_I", name: "GERMANY DAX 40", sector: "European Markets", instrumentType: "INDEX", order: 4 },
  { symbol: "NIKKEI 225", tradingSymbol: "NIKKEI 225", securityId: "9006", segment: "IDX_I", name: "JAPAN NIKKEI 225", sector: "Asian Markets", instrumentType: "INDEX", order: 5 },
  { symbol: "HANG SENG", tradingSymbol: "HANG SENG", securityId: "9007", segment: "IDX_I", name: "HONG KONG HANG SENG", sector: "Asian Markets", instrumentType: "INDEX", order: 6 },
  { symbol: "GIFT NIFTY", tradingSymbol: "GIFT NIFTY", securityId: "9008", segment: "IDX_I", name: "GIFT NIFTY 50 FUTURES", sector: "Indian Offshore", instrumentType: "INDEX", order: 7 },
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
