import { Watchlist, WatchlistItem, WatchlistColumn } from "./types";

const WATCHLISTS_STORAGE_KEY = "shreenexa_watchlists_v1";

export type InstrumentCategoryType =
  | "INDEX"
  | "EQUITY"
  | "ETF"
  | "COMMODITY"
  | "FOREX"
  | "OPTIDX"
  | "FUTIDX"
  | "OPTSTK"
  | "FUTSTK"
  | "FUTCOM"
  | "OPTCOM"
  | "FUTCUR"
  | "OPTCUR";

export interface KnownInstrumentMeta {
  securityId: string;
  tradingSymbol: string;
  ltp: number;
  segment: string;
  name: string;
  instrumentType: InstrumentCategoryType;
  lotSize?: number;
}

export interface CatalogInstrument {
  symbol: string;
  tradingSymbol: string;
  securityId: string;
  segment: string;
  instrumentType: InstrumentCategoryType;
  name: string;
  ltp: number;
  changePct?: number;
  aliases?: string[];
  expiry?: string;
  strike?: number;
  optionType?: "CE" | "PE";
  lotSize?: number;
}

export const KNOWN_EQUITY_INSTRUMENTS: Record<string, KnownInstrumentMeta> = {
  RELIANCE: { securityId: "2885", tradingSymbol: "RELIANCE-EQ", ltp: 2980.5, segment: "NSE_EQ", name: "Reliance Industries Ltd", instrumentType: "EQUITY" },
  TCS: { securityId: "11536", tradingSymbol: "TCS-EQ", ltp: 4210.0, segment: "NSE_EQ", name: "Tata Consultancy Services Ltd", instrumentType: "EQUITY" },
  HDFCBANK: { securityId: "1333", tradingSymbol: "HDFCBANK-EQ", ltp: 1640.2, segment: "NSE_EQ", name: "HDFC Bank Ltd", instrumentType: "EQUITY" },
  INFY: { securityId: "1594", tradingSymbol: "INFY-EQ", ltp: 1890.1, segment: "NSE_EQ", name: "Infosys Ltd", instrumentType: "EQUITY" },
  ICICIBANK: { securityId: "4963", tradingSymbol: "ICICIBANK-EQ", ltp: 1215.3, segment: "NSE_EQ", name: "ICICI Bank Ltd", instrumentType: "EQUITY" },
  SBIN: { securityId: "3045", tradingSymbol: "SBIN-EQ", ltp: 815.4, segment: "NSE_EQ", name: "State Bank of India", instrumentType: "EQUITY" },
  BHARTIARTL: { securityId: "10604", tradingSymbol: "BHARTIARTL-EQ", ltp: 1620.0, segment: "NSE_EQ", name: "Bharti Airtel Ltd", instrumentType: "EQUITY" },
  ITC: { securityId: "1660", tradingSymbol: "ITC-EQ", ltp: 495.0, segment: "NSE_EQ", name: "ITC Ltd", instrumentType: "EQUITY" },
  KOTAKBANK: { securityId: "1922", tradingSymbol: "KOTAKBANK-EQ", ltp: 1810.0, segment: "NSE_EQ", name: "Kotak Mahindra Bank Ltd", instrumentType: "EQUITY" },
  LT: { securityId: "11483", tradingSymbol: "LT-EQ", ltp: 3620.0, segment: "NSE_EQ", name: "Larsen & Toubro Ltd", instrumentType: "EQUITY" },
  AXISBANK: { securityId: "5900", tradingSymbol: "AXISBANK-EQ", ltp: 1180.0, segment: "NSE_EQ", name: "Axis Bank Ltd", instrumentType: "EQUITY" },
  WIPRO: { securityId: "3787", tradingSymbol: "WIPRO-EQ", ltp: 540.0, segment: "NSE_EQ", name: "Wipro Ltd", instrumentType: "EQUITY" },
  HCLTECH: { securityId: "7229", tradingSymbol: "HCLTECH-EQ", ltp: 1780.0, segment: "NSE_EQ", name: "HCL Technologies Ltd", instrumentType: "EQUITY" },
  BAJFINANCE: { securityId: "317", tradingSymbol: "BAJFINANCE-EQ", ltp: 7100.0, segment: "NSE_EQ", name: "Bajaj Finance Ltd", instrumentType: "EQUITY" },
  MARUTI: { securityId: "10999", tradingSymbol: "MARUTI-EQ", ltp: 12400.0, segment: "NSE_EQ", name: "Maruti Suzuki India Ltd", instrumentType: "EQUITY" },
  TATAMOTORS: { securityId: "3456", tradingSymbol: "TATAMOTORS-EQ", ltp: 980.0, segment: "NSE_EQ", name: "Tata Motors Ltd", instrumentType: "EQUITY" },
  TATASTEEL: { securityId: "3499", tradingSymbol: "TATASTEEL-EQ", ltp: 154.8, segment: "NSE_EQ", name: "Tata Steel Ltd", instrumentType: "EQUITY" },
  SUNPHARMA: { securityId: "3351", tradingSymbol: "SUNPHARMA-EQ", ltp: 1850.0, segment: "NSE_EQ", name: "Sun Pharmaceutical Industries Ltd", instrumentType: "EQUITY" },
  NIFTY: { securityId: "13", tradingSymbol: "NIFTY 50", ltp: 24500.0, segment: "IDX_I", name: "NIFTY 50 INDEX", instrumentType: "INDEX" },
  NIFTY50: { securityId: "13", tradingSymbol: "NIFTY 50", ltp: 24500.0, segment: "IDX_I", name: "NIFTY 50 INDEX", instrumentType: "INDEX" },
  "NIFTY 50": { securityId: "13", tradingSymbol: "NIFTY 50", ltp: 24500.0, segment: "IDX_I", name: "NIFTY 50 INDEX", instrumentType: "INDEX" },
  BANKNIFTY: { securityId: "25", tradingSymbol: "NIFTY BANK", ltp: 52100.0, segment: "IDX_I", name: "NIFTY BANK INDEX", instrumentType: "INDEX" },
  "BANK NIFTY": { securityId: "25", tradingSymbol: "NIFTY BANK", ltp: 52100.0, segment: "IDX_I", name: "NIFTY BANK INDEX", instrumentType: "INDEX" },
  FINNIFTY: { securityId: "27", tradingSymbol: "NIFTY FIN SERVICE", ltp: 23800.0, segment: "IDX_I", name: "NIFTY FINANCIAL SERVICES INDEX", instrumentType: "INDEX" },
  "FIN NIFTY": { securityId: "27", tradingSymbol: "NIFTY FIN SERVICE", ltp: 23800.0, segment: "IDX_I", name: "NIFTY FINANCIAL SERVICES INDEX", instrumentType: "INDEX" },
  MIDCPNIFTY: { securityId: "28", tradingSymbol: "NIFTY MID SELECT", ltp: 12850.0, segment: "IDX_I", name: "NIFTY MIDCAP SELECT INDEX", instrumentType: "INDEX" },
  SENSEX: { securityId: "51", tradingSymbol: "SENSEX", ltp: 81200.0, segment: "IDX_I", name: "BSE SENSEX INDEX", instrumentType: "INDEX" },
  NIFTYIT: { securityId: "29", tradingSymbol: "NIFTY IT", ltp: 41250.0, segment: "IDX_I", name: "NIFTY IT INDEX", instrumentType: "INDEX" },
  "NIFTY IT": { securityId: "29", tradingSymbol: "NIFTY IT", ltp: 41250.0, segment: "IDX_I", name: "NIFTY IT INDEX", instrumentType: "INDEX" },
  NIFTYAUTO: { securityId: "30", tradingSymbol: "NIFTY AUTO", ltp: 25400.0, segment: "IDX_I", name: "NIFTY AUTO INDEX", instrumentType: "INDEX" },
  "NIFTY AUTO": { securityId: "30", tradingSymbol: "NIFTY AUTO", ltp: 25400.0, segment: "IDX_I", name: "NIFTY AUTO INDEX", instrumentType: "INDEX" },
  NIFTYBEES: { securityId: "14418", tradingSymbol: "NIFTYBEES-EQ", ltp: 275.50, segment: "NSE_EQ", name: "NIPPON INDIA ETF NIFTY BEES", instrumentType: "ETF" },
  BANKBEES: { securityId: "14419", tradingSymbol: "BANKBEES-EQ", ltp: 532.10, segment: "NSE_EQ", name: "NIPPON INDIA ETF BANK BEES", instrumentType: "ETF" },
  GOLDBEES: { securityId: "14420", tradingSymbol: "GOLDBEES-EQ", ltp: 62.40, segment: "NSE_EQ", name: "NIPPON INDIA ETF GOLD BEES", instrumentType: "ETF" },
  SILVERBEES: { securityId: "14421", tradingSymbol: "SILVERBEES-EQ", ltp: 88.75, segment: "NSE_EQ", name: "NIPPON INDIA ETF SILVER BEES", instrumentType: "ETF" },
  ITBEES: { securityId: "14422", tradingSymbol: "ITBEES-EQ", ltp: 43.15, segment: "NSE_EQ", name: "NIPPON INDIA ETF NIFTY IT", instrumentType: "ETF" },
  JUNIORBEES: { securityId: "14423", tradingSymbol: "JUNIORBEES-EQ", ltp: 745.00, segment: "NSE_EQ", name: "NIPPON INDIA ETF JUNIOR BEES", instrumentType: "ETF" },
  LIQUIDBEES: { securityId: "14424", tradingSymbol: "LIQUIDBEES-EQ", ltp: 1000.00, segment: "NSE_EQ", name: "NIPPON INDIA ETF LIQUID BEES", instrumentType: "ETF" },
  CRUDEOIL: { securityId: "254101", tradingSymbol: "CRUDEOIL-19Sep2026-FUT", ltp: 6150.0, segment: "MCX_COMM", name: "CRUDE OIL MCX FUTURES", instrumentType: "FUTCOM", lotSize: 100 },
  GOLD: { securityId: "254102", tradingSymbol: "GOLD-05Oct2026-FUT", ltp: 72450.0, segment: "MCX_COMM", name: "GOLD 1KG MCX FUTURES", instrumentType: "FUTCOM", lotSize: 100 },
  SILVER: { securityId: "254103", tradingSymbol: "SILVER-05Sep2026-FUT", ltp: 84200.0, segment: "MCX_COMM", name: "SILVER 30KG MCX FUTURES", instrumentType: "FUTCOM", lotSize: 30 },
  NATURALGAS: { securityId: "254104", tradingSymbol: "NATURALGAS-25Sep2026-FUT", ltp: 195.50, segment: "MCX_COMM", name: "NATURAL GAS MCX FUTURES", instrumentType: "FUTCOM", lotSize: 1250 },
  COPPER: { securityId: "254105", tradingSymbol: "COPPER-30Sep2026-FUT", ltp: 825.40, segment: "MCX_COMM", name: "COPPER MCX FUTURES", instrumentType: "FUTCOM", lotSize: 2500 },
  USDINR: { securityId: "601201", tradingSymbol: "USDINR-26Aug2026-FUT", ltp: 83.92, segment: "NSE_CURRENCY", name: "USDINR CURRENCY FUTURES", instrumentType: "FUTCUR", lotSize: 1000 },
  EURINR: { securityId: "601202", tradingSymbol: "EURINR-26Aug2026-FUT", ltp: 91.45, segment: "NSE_CURRENCY", name: "EURINR CURRENCY FUTURES", instrumentType: "FUTCUR", lotSize: 1000 },
  GBPINR: { securityId: "601203", tradingSymbol: "GBPINR-26Aug2026-FUT", ltp: 109.80, segment: "NSE_CURRENCY", name: "GBPINR CURRENCY FUTURES", instrumentType: "FUTCUR", lotSize: 1000 },
  JPYINR: { securityId: "601204", tradingSymbol: "JPYINR-26Aug2026-FUT", ltp: 58.30, segment: "NSE_CURRENCY", name: "JPYINR CURRENCY FUTURES", instrumentType: "FUTCUR", lotSize: 1000 },
  COIN: { securityId: "9999", tradingSymbol: "COIN-EQ", ltp: 150.0, segment: "NSE_EQ", name: "Coin Proxy Demo Stock", instrumentType: "EQUITY" },
};

export const CATALOG_INSTRUMENTS: CatalogInstrument[] = [
  // Indices
  {
    symbol: "NIFTY",
    tradingSymbol: "NIFTY 50",
    securityId: "13",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY 50 INDEX",
    ltp: 24500.0,
    changePct: 0.65,
    aliases: ["NIFTY", "NIFTY50", "NIFTY 50", "CNX NIFTY"],
  },
  {
    symbol: "BANKNIFTY",
    tradingSymbol: "NIFTY BANK",
    securityId: "25",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY BANK INDEX",
    ltp: 52100.0,
    changePct: -0.25,
    aliases: ["BANKNIFTY", "BANK NIFTY", "NIFTY BANK"],
  },
  {
    symbol: "FINNIFTY",
    tradingSymbol: "NIFTY FIN SERVICE",
    securityId: "27",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY FINANCIAL SERVICES INDEX",
    ltp: 23800.0,
    changePct: 0.35,
    aliases: ["FINNIFTY", "FIN NIFTY", "NIFTY FIN SERVICE"],
  },
  {
    symbol: "MIDCPNIFTY",
    tradingSymbol: "NIFTY MID SELECT",
    securityId: "28",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY MIDCAP SELECT INDEX",
    ltp: 12850.0,
    changePct: 0.85,
    aliases: ["MIDCPNIFTY", "NIFTY MIDCAP", "MIDCAP NIFTY"],
  },
  {
    symbol: "SENSEX",
    tradingSymbol: "SENSEX",
    securityId: "51",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "BSE SENSEX INDEX",
    ltp: 81200.0,
    changePct: 0.55,
    aliases: ["SENSEX", "BSE SENSEX", "BSESENSEX"],
  },
  {
    symbol: "NIFTYIT",
    tradingSymbol: "NIFTY IT",
    securityId: "29",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY IT INDEX",
    ltp: 41250.0,
    changePct: 1.15,
    aliases: ["NIFTY IT", "NIFTYIT", "CNX IT"],
  },
  {
    symbol: "NIFTYAUTO",
    tradingSymbol: "NIFTY AUTO",
    securityId: "30",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY AUTO INDEX",
    ltp: 25400.0,
    changePct: -0.40,
    aliases: ["NIFTY AUTO", "NIFTYAUTO"],
  },
  // Equities
  {
    symbol: "RELIANCE",
    tradingSymbol: "RELIANCE-EQ",
    securityId: "2885",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Reliance Industries Ltd",
    ltp: 2980.5,
    changePct: 1.25,
    aliases: ["RELIANCE", "RIL"],
  },
  {
    symbol: "TCS",
    tradingSymbol: "TCS-EQ",
    securityId: "11536",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tata Consultancy Services Ltd",
    ltp: 4210.0,
    changePct: -0.45,
    aliases: ["TCS", "TATA CONSULTANCY"],
  },
  {
    symbol: "HDFCBANK",
    tradingSymbol: "HDFCBANK-EQ",
    securityId: "1333",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "HDFC Bank Ltd",
    ltp: 1640.2,
    changePct: 0.80,
    aliases: ["HDFCBANK", "HDFC BANK"],
  },
  {
    symbol: "INFY",
    tradingSymbol: "INFY-EQ",
    securityId: "1594",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Infosys Ltd",
    ltp: 1890.1,
    changePct: -1.10,
    aliases: ["INFY", "INFOSYS"],
  },
  {
    symbol: "ICICIBANK",
    tradingSymbol: "ICICIBANK-EQ",
    securityId: "4963",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "ICICI Bank Ltd",
    ltp: 1215.3,
    changePct: 1.40,
    aliases: ["ICICIBANK", "ICICI BANK"],
  },
  {
    symbol: "SBIN",
    tradingSymbol: "SBIN-EQ",
    securityId: "3045",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "State Bank of India",
    ltp: 815.4,
    changePct: 1.15,
    aliases: ["SBIN", "SBI", "STATE BANK"],
  },
  {
    symbol: "BHARTIARTL",
    tradingSymbol: "BHARTIARTL-EQ",
    securityId: "10604",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bharti Airtel Ltd",
    ltp: 1620.0,
    changePct: 0.50,
    aliases: ["BHARTIARTL", "AIRTEL"],
  },
  {
    symbol: "ITC",
    tradingSymbol: "ITC-EQ",
    securityId: "1660",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "ITC Ltd",
    ltp: 495.0,
    changePct: -0.20,
    aliases: ["ITC"],
  },
  {
    symbol: "KOTAKBANK",
    tradingSymbol: "KOTAKBANK-EQ",
    securityId: "1922",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Kotak Mahindra Bank Ltd",
    ltp: 1810.0,
    changePct: -0.30,
    aliases: ["KOTAK", "KOTAKBANK"],
  },
  {
    symbol: "LT",
    tradingSymbol: "LT-EQ",
    securityId: "11483",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Larsen & Toubro Ltd",
    ltp: 3620.0,
    changePct: 1.80,
    aliases: ["LT", "L&T"],
  },
  {
    symbol: "AXISBANK",
    tradingSymbol: "AXISBANK-EQ",
    securityId: "5900",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Axis Bank Ltd",
    ltp: 1180.0,
    changePct: 0.60,
    aliases: ["AXISBANK", "AXIS BANK"],
  },
  {
    symbol: "WIPRO",
    tradingSymbol: "WIPRO-EQ",
    securityId: "3787",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Wipro Ltd",
    ltp: 540.0,
    changePct: 0.10,
    aliases: ["WIPRO"],
  },
  {
    symbol: "HCLTECH",
    tradingSymbol: "HCLTECH-EQ",
    securityId: "7229",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "HCL Technologies Ltd",
    ltp: 1780.0,
    changePct: -0.90,
    aliases: ["HCLTECH", "HCL TECH"],
  },
  {
    symbol: "BAJFINANCE",
    tradingSymbol: "BAJFINANCE-EQ",
    securityId: "317",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bajaj Finance Ltd",
    ltp: 7100.0,
    changePct: -0.75,
    aliases: ["BAJFINANCE", "BAJAJ FINANCE"],
  },
  {
    symbol: "MARUTI",
    tradingSymbol: "MARUTI-EQ",
    securityId: "10999",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Maruti Suzuki India Ltd",
    ltp: 12400.0,
    changePct: 0.90,
    aliases: ["MARUTI", "MARUTI SUZUKI"],
  },
  {
    symbol: "TATAMOTORS",
    tradingSymbol: "TATAMOTORS-EQ",
    securityId: "3456",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tata Motors Ltd",
    ltp: 980.0,
    changePct: 2.10,
    aliases: ["TATAMOTORS", "TATA MOTORS"],
  },
  {
    symbol: "TATASTEEL",
    tradingSymbol: "TATASTEEL-EQ",
    securityId: "3499",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tata Steel Ltd",
    ltp: 154.8,
    changePct: 0.40,
    aliases: ["TATASTEEL", "TATA STEEL"],
  },
  {
    symbol: "SUNPHARMA",
    tradingSymbol: "SUNPHARMA-EQ",
    securityId: "3351",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Sun Pharmaceutical Industries Ltd",
    ltp: 1850.0,
    changePct: 1.05,
    aliases: ["SUNPHARMA", "SUN PHARMA"],
  },
  {
    symbol: "NIFTYBEES",
    tradingSymbol: "NIFTYBEES-EQ",
    securityId: "14418",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF NIFTY BEES",
    ltp: 275.50,
    changePct: 0.65,
    aliases: ["NIFTYBEES", "NIFTY BEES", "ETF"],
  },
  {
    symbol: "BANKBEES",
    tradingSymbol: "BANKBEES-EQ",
    securityId: "14419",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF BANK BEES",
    ltp: 532.10,
    changePct: -0.20,
    aliases: ["BANKBEES", "BANK BEES", "ETF"],
  },
  {
    symbol: "GOLDBEES",
    tradingSymbol: "GOLDBEES-EQ",
    securityId: "14420",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF GOLD BEES",
    ltp: 62.40,
    changePct: 0.80,
    aliases: ["GOLDBEES", "GOLD BEES", "ETF"],
  },
  {
    symbol: "SILVERBEES",
    tradingSymbol: "SILVERBEES-EQ",
    securityId: "14421",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF SILVER BEES",
    ltp: 88.75,
    changePct: 1.20,
    aliases: ["SILVERBEES", "SILVER BEES", "ETF"],
  },
  {
    symbol: "ITBEES",
    tradingSymbol: "ITBEES-EQ",
    securityId: "14422",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF NIFTY IT",
    ltp: 43.15,
    changePct: -0.40,
    aliases: ["ITBEES", "IT BEES", "ETF"],
  },
  {
    symbol: "JUNIORBEES",
    tradingSymbol: "JUNIORBEES-EQ",
    securityId: "14423",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF JUNIOR BEES",
    ltp: 745.00,
    changePct: 0.50,
    aliases: ["JUNIORBEES", "JUNIOR BEES", "ETF"],
  },
  {
    symbol: "LIQUIDBEES",
    tradingSymbol: "LIQUIDBEES-EQ",
    securityId: "14424",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "NIPPON INDIA ETF LIQUID BEES",
    ltp: 1000.00,
    changePct: 0.01,
    aliases: ["LIQUIDBEES", "LIQUID BEES", "ETF"],
  },
  // MCX Commodities
  {
    symbol: "CRUDEOIL",
    tradingSymbol: "CRUDEOIL-19Sep2026-FUT",
    securityId: "254101",
    segment: "MCX_COMM",
    instrumentType: "FUTCOM",
    name: "CRUDE OIL MCX FUTURES",
    ltp: 6150.0,
    changePct: -0.60,
    lotSize: 100,
    aliases: ["CRUDE OIL", "CRUDEOIL", "MCX CRUDE"],
  },
  {
    symbol: "GOLD",
    tradingSymbol: "GOLD-05Oct2026-FUT",
    securityId: "254102",
    segment: "MCX_COMM",
    instrumentType: "FUTCOM",
    name: "GOLD 1KG MCX FUTURES",
    ltp: 72450.0,
    changePct: 0.45,
    lotSize: 100,
    aliases: ["GOLD", "MCX GOLD", "GOLD FUT"],
  },
  {
    symbol: "SILVER",
    tradingSymbol: "SILVER-05Sep2026-FUT",
    securityId: "254103",
    segment: "MCX_COMM",
    instrumentType: "FUTCOM",
    name: "SILVER 30KG MCX FUTURES",
    ltp: 84200.0,
    changePct: 1.10,
    lotSize: 30,
    aliases: ["SILVER", "MCX SILVER", "SILVER FUT"],
  },
  {
    symbol: "NATURALGAS",
    tradingSymbol: "NATURALGAS-25Sep2026-FUT",
    securityId: "254104",
    segment: "MCX_COMM",
    instrumentType: "FUTCOM",
    name: "NATURAL GAS MCX FUTURES",
    ltp: 195.50,
    changePct: -1.80,
    lotSize: 1250,
    aliases: ["NATURAL GAS", "NATURALGAS", "MCX NG"],
  },
  {
    symbol: "COPPER",
    tradingSymbol: "COPPER-30Sep2026-FUT",
    securityId: "254105",
    segment: "MCX_COMM",
    instrumentType: "FUTCOM",
    name: "COPPER MCX FUTURES",
    ltp: 825.40,
    changePct: 0.30,
    lotSize: 2500,
    aliases: ["COPPER", "MCX COPPER"],
  },
  // Currency / Forex
  {
    symbol: "USDINR",
    tradingSymbol: "USDINR-26Aug2026-FUT",
    securityId: "601201",
    segment: "NSE_CURRENCY",
    instrumentType: "FUTCUR",
    name: "USDINR CURRENCY FUTURES",
    ltp: 83.92,
    changePct: 0.05,
    lotSize: 1000,
    aliases: ["USDINR", "USD-INR", "USD"],
  },
  {
    symbol: "EURINR",
    tradingSymbol: "EURINR-26Aug2026-FUT",
    securityId: "601202",
    segment: "NSE_CURRENCY",
    instrumentType: "FUTCUR",
    name: "EURINR CURRENCY FUTURES",
    ltp: 91.45,
    changePct: -0.12,
    lotSize: 1000,
    aliases: ["EURINR", "EUR-INR", "EUR"],
  },
  {
    symbol: "GBPINR",
    tradingSymbol: "GBPINR-26Aug2026-FUT",
    securityId: "601203",
    segment: "NSE_CURRENCY",
    instrumentType: "FUTCUR",
    name: "GBPINR CURRENCY FUTURES",
    ltp: 109.80,
    changePct: 0.22,
    lotSize: 1000,
    aliases: ["GBPINR", "GBP-INR", "GBP"],
  },
  {
    symbol: "JPYINR",
    tradingSymbol: "JPYINR-26Aug2026-FUT",
    securityId: "601204",
    segment: "NSE_CURRENCY",
    instrumentType: "FUTCUR",
    name: "JPYINR CURRENCY FUTURES",
    ltp: 58.30,
    changePct: -0.35,
    lotSize: 1000,
    aliases: ["JPYINR", "JPY-INR", "JPY"],
  },
  {
    symbol: "COIN",
    tradingSymbol: "COIN-EQ",
    securityId: "9999",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Coin Proxy Demo Stock",
    ltp: 150.0,
    changePct: 0.0,
    aliases: ["COIN"],
  },
  // F&O
  {
    symbol: "BANKNIFTY-FUT",
    tradingSymbol: "BANKNIFTY-FUT",
    securityId: "49240",
    segment: "NSE_FNO",
    instrumentType: "FUTIDX",
    name: "NIFTY BANK CURRENT EXPIRY FUTURES",
    ltp: 52180.0,
    changePct: -0.20,
    aliases: ["BANKNIFTY FUT", "BANKNIFTYFUT"],
  },
  {
    symbol: "BANKNIFTY-52000-CE",
    tradingSymbol: "BANKNIFTY-52000-CE",
    securityId: "49241",
    segment: "NSE_FNO",
    instrumentType: "OPTIDX",
    name: "NIFTY BANK 52000 CALL OPTION",
    ltp: 340.0,
    changePct: 4.5,
    strike: 52000,
    optionType: "CE",
    aliases: ["BANKNIFTY 52000 CE", "52000 CE"],
  },
  {
    symbol: "NIFTY-FUT",
    tradingSymbol: "NIFTY-FUT",
    securityId: "49230",
    segment: "NSE_FNO",
    instrumentType: "FUTIDX",
    name: "NIFTY 50 CURRENT EXPIRY FUTURES",
    ltp: 24530.0,
    changePct: 0.60,
    aliases: ["NIFTY FUT", "NIFTYFUT"],
  },
  {
    symbol: "NIFTY-24500-CE",
    tradingSymbol: "NIFTY-24500-CE",
    securityId: "49231",
    segment: "NSE_FNO",
    instrumentType: "OPTIDX",
    name: "NIFTY 24500 CALL OPTION",
    ltp: 185.0,
    changePct: 6.2,
    strike: 24500,
    optionType: "CE",
    aliases: ["NIFTY 24500 CE", "24500 CE"],
  },
  {
    symbol: "NIFTY-24500-PE",
    tradingSymbol: "NIFTY-24500-PE",
    securityId: "49232",
    segment: "NSE_FNO",
    instrumentType: "OPTIDX",
    name: "NIFTY 24500 PUT OPTION",
    ltp: 140.0,
    changePct: -8.5,
    strike: 24500,
    optionType: "PE",
    aliases: ["NIFTY 24500 PE", "24500 PE"],
  },
];

export function searchCatalogInstruments(
  query: string,
  category: "ALL" | "INDICES" | "STOCKS" | "FNO" | "ETF" | "COMMODITY" | "FOREX" = "ALL"
): CatalogInstrument[] {
  const cleanQ = query.trim().toUpperCase();
  if (!cleanQ) return [];

  const norm = (s: string) => s.toUpperCase().replace(/[\s\-_]/g, "");
  const qNorm = norm(cleanQ);

  return CATALOG_INSTRUMENTS.filter((inst) => {
    // 1. Category check
    if (category === "INDICES" && inst.instrumentType !== "INDEX" && inst.segment !== "IDX_I") {
      return false;
    }
    if (category === "STOCKS" && inst.instrumentType !== "EQUITY") {
      return false;
    }
    if (
      category === "FNO" &&
      !["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"].includes(inst.instrumentType) &&
      inst.segment !== "NSE_FNO" &&
      inst.segment !== "BSE_FNO"
    ) {
      return false;
    }
    if (category === "ETF" && inst.instrumentType !== "ETF") {
      return false;
    }
    if (
      category === "COMMODITY" &&
      !["COMMODITY", "FUTCOM", "OPTCOM"].includes(inst.instrumentType) &&
      !inst.segment.startsWith("MCX")
    ) {
      return false;
    }
    if (
      category === "FOREX" &&
      !["FOREX", "FUTCUR", "OPTCUR"].includes(inst.instrumentType) &&
      !inst.segment.includes("CURRENCY")
    ) {
      return false;
    }

    // 2. Query match: symbol, tradingSymbol, name, or aliases
    if (inst.symbol.toUpperCase().includes(cleanQ)) return true;
    if (inst.tradingSymbol.toUpperCase().includes(cleanQ)) return true;
    if (inst.name.toUpperCase().includes(cleanQ)) return true;
    if (norm(inst.symbol).includes(qNorm)) return true;
    if (norm(inst.tradingSymbol).includes(qNorm)) return true;
    if (inst.aliases?.some((a) => norm(a).includes(qNorm) || a.toUpperCase().includes(cleanQ))) {
      return true;
    }
    return false;
  });
}

export function resolveCatalogInstrument(
  query: string,
  segment?: string
): CatalogInstrument | null {
  const cleanQ = query.trim().toUpperCase();
  if (!cleanQ) return null;

  // 1. Exact or alias match in rich CATALOG_INSTRUMENTS (returns canonical symbol)
  const norm = (s: string) => s.toUpperCase().replace(/[\s\-_]/g, "");
  const qNorm = norm(cleanQ);

  for (const inst of CATALOG_INSTRUMENTS) {
    if (segment && inst.segment !== segment && segment !== "ALL") continue;
    if (inst.symbol.toUpperCase() === cleanQ || inst.tradingSymbol.toUpperCase() === cleanQ) {
      return inst;
    }
    if (norm(inst.symbol) === qNorm || norm(inst.tradingSymbol) === qNorm) {
      return inst;
    }
    if (inst.aliases?.some((a) => norm(a) === qNorm || a.toUpperCase() === cleanQ)) {
      return inst;
    }
  }

  // 2. Direct match in KNOWN_EQUITY_INSTRUMENTS
  if (KNOWN_EQUITY_INSTRUMENTS[cleanQ]) {
    const meta = KNOWN_EQUITY_INSTRUMENTS[cleanQ];
    return {
      symbol: cleanQ,
      tradingSymbol: meta.tradingSymbol,
      securityId: meta.securityId,
      segment: meta.segment,
      instrumentType: meta.instrumentType,
      name: meta.name,
      ltp: meta.ltp,
    };
  }

  return null;
}

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
      // Purge/sanitize: re-resolve missing security IDs against known instruments
      const sanitized = parsed.map((wl: Watchlist) => ({
        ...wl,
        items: (wl.items || []).map((it) => {
          if ((!it.securityId || it.securityId.trim() === "") && KNOWN_EQUITY_INSTRUMENTS[it.symbol]) {
            return {
              ...it,
              securityId: KNOWN_EQUITY_INSTRUMENTS[it.symbol].securityId,
              tradingSymbol: it.tradingSymbol || KNOWN_EQUITY_INSTRUMENTS[it.symbol].tradingSymbol,
            };
          }
          return it;
        }),
      }));
      return sanitized;
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
    id: `wl-${Date.now().toString(36)}-${(watchlists.length + 1).toString(36)}`,
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
