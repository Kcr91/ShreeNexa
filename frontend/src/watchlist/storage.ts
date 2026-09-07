import { Watchlist, WatchlistItem, WatchlistColumn } from "./types";

export const WATCHLISTS_STORAGE_KEY_V2 = "shreenexa_watchlists_v2";
export const WATCHLISTS_STORAGE_KEY_V1 = "shreenexa_watchlists_v1";
export const WATCHLISTS_STORAGE_KEY = WATCHLISTS_STORAGE_KEY_V2;

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
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
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
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
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
  // Additional Indices from Image 2
  "NIFTY MIDCAP 100": { securityId: "26", tradingSymbol: "NIFTY MIDCAP 100", ltp: 58900.0, segment: "IDX_I", name: "NIFTY MIDCAP 100 INDEX", instrumentType: "INDEX" },
  BANKEX: { securityId: "52", tradingSymbol: "BSE INDEX BANKEX", ltp: 58200.0, segment: "IDX_I", name: "BSE BANKEX INDEX", instrumentType: "INDEX" },
  ALLCAP: { securityId: "53", tradingSymbol: "BSE INDEX ALLCAP", ltp: 10400.0, segment: "IDX_I", name: "BSE ALLCAP INDEX", instrumentType: "INDEX" },
  "NIFTY 100": { securityId: "31", tradingSymbol: "NIFTY 100", ltp: 25100.0, segment: "IDX_I", name: "NIFTY 100 INDEX", instrumentType: "INDEX" },
  "NIFTY DIV OPPS 50": { securityId: "32", tradingSymbol: "NIFTY DIV OPPS 50", ltp: 6800.0, segment: "IDX_I", name: "NIFTY DIVIDEND OPPORTUNITIES 50 INDEX", instrumentType: "INDEX" },
  "NIFTY COMMODITIES": { securityId: "33", tradingSymbol: "NIFTY COMMODITIES", ltp: 9200.0, segment: "IDX_I", name: "NIFTY COMMODITIES INDEX", instrumentType: "INDEX" },
  "NIFTY CONSUMPTION": { securityId: "34", tradingSymbol: "NIFTY CONSUMPTION", ltp: 11400.0, segment: "IDX_I", name: "NIFTY CONSUMPTION INDEX", instrumentType: "INDEX" },
  "NIFTY50 PR 2X LEV": { securityId: "35", tradingSymbol: "NIFTY50 PR 2X LEV", ltp: 15400.0, segment: "IDX_I", name: "NIFTY50 PR 2X LEVERAGED INDEX", instrumentType: "INDEX" },
  "NIFTY50 PR 1X INV": { securityId: "36", tradingSymbol: "NIFTY50 PR 1X INV", ltp: 3200.0, segment: "IDX_I", name: "NIFTY50 PR 1X INVERSE INDEX", instrumentType: "INDEX" },
  "NIFTY50 TR 2X LEV": { securityId: "37", tradingSymbol: "NIFTY50 TR 2X LEV", ltp: 16200.0, segment: "IDX_I", name: "NIFTY50 TR 2X LEVERAGED INDEX", instrumentType: "INDEX" },
  "NIFTY50 TR 1X INV": { securityId: "38", tradingSymbol: "NIFTY50 TR 1X INV", ltp: 3100.0, segment: "IDX_I", name: "NIFTY50 TR 1X INVERSE INDEX", instrumentType: "INDEX" },
  "NIFTY MIDCAP 50": { securityId: "39", tradingSymbol: "NIFTY MIDCAP 50", ltp: 16100.0, segment: "IDX_I", name: "NIFTY MIDCAP 50 INDEX", instrumentType: "INDEX" },
  "NIFTY REALTY": { securityId: "40", tradingSymbol: "NIFTY REALTY", ltp: 1050.0, segment: "IDX_I", name: "NIFTY REALTY INDEX", instrumentType: "INDEX" },
  "NIFTY INFRA": { securityId: "41", tradingSymbol: "NIFTY INFRA", ltp: 9100.0, segment: "IDX_I", name: "NIFTY INFRASTRUCTURE INDEX", instrumentType: "INDEX" },
  // Image 3 Equities
  HEROMOTOCO: { securityId: "1348", tradingSymbol: "HEROMOTOCO-EQ", ltp: 5300.0, segment: "NSE_EQ", name: "Hero MotoCorp Ltd", instrumentType: "EQUITY" },
  MPHASIS: { securityId: "4503", tradingSymbol: "MPHASIS-EQ", ltp: 2357.10, segment: "NSE_EQ", name: "Mphasis Ltd", instrumentType: "EQUITY", fiftyTwoWeekHigh: 3125.00, fiftyTwoWeekLow: 2180.00 },
  CIPLA: { securityId: "694", tradingSymbol: "CIPLA-EQ", ltp: 1385.0, segment: "NSE_EQ", name: "Cipla Ltd", instrumentType: "EQUITY" },
  COALINDIA: { securityId: "20374", tradingSymbol: "COALINDIA-EQ", ltp: 415.35, segment: "NSE_EQ", name: "Coal India Ltd", instrumentType: "EQUITY" },
  GODFRYPHLP: { securityId: "1232", tradingSymbol: "GODFRYPHLP-EQ", ltp: 2051.0, segment: "NSE_EQ", name: "Godfrey Phillips India Ltd", instrumentType: "EQUITY" },
  TECHNOE: { securityId: "14880", tradingSymbol: "TECHNOE-EQ", ltp: 979.50, segment: "NSE_EQ", name: "Techno Electric & Engineering Co Ltd", instrumentType: "EQUITY" },
  LTTS: { securityId: "18564", tradingSymbol: "LTTS-EQ", ltp: 3493.30, segment: "NSE_EQ", name: "L&T Technology Services Ltd", instrumentType: "EQUITY" },
  // Image 1 & 2 Holdings
  MANAPPURAM: { securityId: "19000", tradingSymbol: "MANAPPURAM-EQ", ltp: 339.70, segment: "NSE_EQ", name: "Manappuram Finance Ltd", instrumentType: "EQUITY" },
  BODALCHEM: { securityId: "19001", tradingSymbol: "BODALCHEM-EQ", ltp: 155.62, segment: "NSE_EQ", name: "Bodal Chemicals Ltd", instrumentType: "EQUITY" },
  BLSE: { securityId: "19002", tradingSymbol: "BLSE-EQ", ltp: 320.05, segment: "NSE_EQ", name: "BLS E-Services Ltd", instrumentType: "EQUITY" },
  MOREPENLAB: { securityId: "19003", tradingSymbol: "MOREPENLAB-EQ", ltp: 113.74, segment: "NSE_EQ", name: "Morepen Laboratories Ltd", instrumentType: "EQUITY" },
  MON100: { securityId: "19004", tradingSymbol: "MON100-EQ", ltp: 324.67, segment: "NSE_EQ", name: "Motilal Oswal Nasdaq 100 ETF", instrumentType: "ETF" },
  TMCV: { securityId: "19005", tradingSymbol: "TMCV-EQ", ltp: 458.20, segment: "NSE_EQ", name: "Tata Motors Commercial Vehicles", instrumentType: "EQUITY" },
  CAMS: { securityId: "19006", tradingSymbol: "CAMS-EQ", ltp: 748.80, segment: "NSE_EQ", name: "Computer Age Management Services Ltd", instrumentType: "EQUITY" },
  DELTACORP: { securityId: "19007", tradingSymbol: "DELTACORP-EQ", ltp: 56.15, segment: "NSE_EQ", name: "Delta Corp Ltd", instrumentType: "EQUITY" },
  HDFCAMC: { securityId: "19008", tradingSymbol: "HDFCAMC-EQ", ltp: 2463.00, segment: "NSE_EQ", name: "HDFC Asset Management Co Ltd", instrumentType: "EQUITY" },
  AARTIIND: { securityId: "19009", tradingSymbol: "AARTIIND-EQ", ltp: 492.05, segment: "NSE_EQ", name: "Aarti Industries Ltd", instrumentType: "EQUITY" },
  IGL: { securityId: "19010", tradingSymbol: "IGL-EQ", ltp: 158.05, segment: "NSE_EQ", name: "Indraprastha Gas Ltd", instrumentType: "EQUITY" },
  // Image 1 Scrips & ETFs
  SILVERCASF: { securityId: "20001", tradingSymbol: "SILVERCASF", ltp: 88.50, segment: "BSE_EQ", name: "ZERODHA SILVER ETF", instrumentType: "ETF" },
  SILCASINAV: { securityId: "20002", tradingSymbol: "SILCASINAV", ltp: 88.20, segment: "NSE_EQ", name: "ZERODHA AMC - SILCASINAV", instrumentType: "ETF" },
  SML100INAV: { securityId: "20003", tradingSymbol: "SML100INAV", ltp: 55.40, segment: "NSE_EQ", name: "ZERODHA AMC - SML100NAV", instrumentType: "ETF" },
  SML100CASE: { securityId: "20004", tradingSymbol: "SML100CASE", ltp: 55.70, segment: "NSE_EQ", name: "ZERODHA NIFTY SMALLCAP 100 ETF", instrumentType: "ETF" },
  STYRFNIX: { securityId: "20005", tradingSymbol: "STYRFNIX-EQ", ltp: 2150.0, segment: "NSE_EQ", name: "STYRENIX PERFORMANCE", instrumentType: "EQUITY" },
  SHAREINDIA: { securityId: "20006", tradingSymbol: "SHAREINDIA-EQ", ltp: 1420.0, segment: "NSE_EQ", name: "SHARE IND. SECURITIES", instrumentType: "EQUITY" },
  SINTERCOM: { securityId: "20007", tradingSymbol: "SINTERCOM-EQ", ltp: 145.0, segment: "NSE_EQ", name: "SINTERCOM INDIA", instrumentType: "EQUITY" },
  SHRADHA: { securityId: "20008", tradingSymbol: "SHRADHA-EQ", ltp: 72.50, segment: "NSE_EQ", name: "SHRADHA REALTY", instrumentType: "EQUITY" },
  SHALBY: { securityId: "20009", tradingSymbol: "SHALBY-EQ", ltp: 245.0, segment: "NSE_EQ", name: "SHALBY LTD", instrumentType: "EQUITY" },
  SUDARCOLOR: { securityId: "20010", tradingSymbol: "SUDARCOLOR-EQ", ltp: 680.0, segment: "NSE_EQ", name: "SUDARSHAN COLORANT IND", instrumentType: "EQUITY" },
  SBIETFPB: { securityId: "20011", tradingSymbol: "SBIETFPB-EQ", ltp: 450.0, segment: "NSE_EQ", name: "SBI PRIVATE BANK ETF", instrumentType: "ETF" },
  SBIETFIT: { securityId: "20012", tradingSymbol: "SBIETFIT-EQ", ltp: 42.80, segment: "NSE_EQ", name: "SBI ETF IT ETF", instrumentType: "ETF" },
  SHIVATEX: { securityId: "20013", tradingSymbol: "SHIVATEX-EQ", ltp: 195.0, segment: "NSE_EQ", name: "SHIVA TEXYARN", instrumentType: "EQUITY" },
  SUBEXLTD: { securityId: "20014", tradingSymbol: "SUBEXLTD-EQ", ltp: 32.50, segment: "NSE_EQ", name: "SUBEX INDIA", instrumentType: "EQUITY" },
  SCHAEFFLER: { securityId: "20015", tradingSymbol: "SCHAEFFLER-EQ", ltp: 3850.0, segment: "NSE_EQ", name: "SCHAEFFLER INDIA", instrumentType: "EQUITY" },
  SDBL: { securityId: "20016", tradingSymbol: "SDBL-EQ", ltp: 310.0, segment: "NSE_EQ", name: "SOM DIST & BREW", instrumentType: "EQUITY" },
  SANOFI: { securityId: "20017", tradingSymbol: "SANOFI-EQ", ltp: 6800.0, segment: "NSE_EQ", name: "SANOFI INDIA", instrumentType: "EQUITY" },
  // Additional Nifty 50 & Top Equities
  TITAN: { securityId: "3506", tradingSymbol: "TITAN-EQ", ltp: 3450.0, segment: "NSE_EQ", name: "Titan Company Ltd", instrumentType: "EQUITY" },
  ADANIENT: { securityId: "25", tradingSymbol: "ADANIENT-EQ", ltp: 3020.0, segment: "NSE_EQ", name: "Adani Enterprises Ltd", instrumentType: "EQUITY" },
  ADANIPORTS: { securityId: "15083", tradingSymbol: "ADANIPORTS-EQ", ltp: 1450.0, segment: "NSE_EQ", name: "Adani Ports & SEZ Ltd", instrumentType: "EQUITY" },
  ASIANPAINT: { securityId: "236", tradingSymbol: "ASIANPAINT-EQ", ltp: 3180.0, segment: "NSE_EQ", name: "Asian Paints Ltd", instrumentType: "EQUITY" },
  "BAJAJ-AUTO": { securityId: "16669", tradingSymbol: "BAJAJ-AUTO-EQ", ltp: 10400.0, segment: "NSE_EQ", name: "Bajaj Auto Ltd", instrumentType: "EQUITY" },
  BAJAJFINSV: { securityId: "16675", tradingSymbol: "BAJAJFINSV-EQ", ltp: 1720.0, segment: "NSE_EQ", name: "Bajaj Finserv Ltd", instrumentType: "EQUITY" },
  BPCL: { securityId: "526", tradingSymbol: "BPCL-EQ", ltp: 350.0, segment: "NSE_EQ", name: "Bharat Petroleum Corporation Ltd", instrumentType: "EQUITY" },
  BRITANNIA: { securityId: "547", tradingSymbol: "BRITANNIA-EQ", ltp: 5800.0, segment: "NSE_EQ", name: "Britannia Industries Ltd", instrumentType: "EQUITY" },
  DRREDDY: { securityId: "881", tradingSymbol: "DRREDDY-EQ", ltp: 6600.0, segment: "NSE_EQ", name: "Dr. Reddy's Laboratories Ltd", instrumentType: "EQUITY" },
  EICHERMOT: { securityId: "910", tradingSymbol: "EICHERMOT-EQ", ltp: 4900.0, segment: "NSE_EQ", name: "Eicher Motors Ltd", instrumentType: "EQUITY" },
  GRASIM: { securityId: "1232", tradingSymbol: "GRASIM-EQ", ltp: 2650.0, segment: "NSE_EQ", name: "Grasim Industries Ltd", instrumentType: "EQUITY" },
  HDFCLIFE: { securityId: "467", tradingSymbol: "HDFCLIFE-EQ", ltp: 710.0, segment: "NSE_EQ", name: "HDFC Life Insurance Co Ltd", instrumentType: "EQUITY" },
  HINDALCO: { securityId: "1363", tradingSymbol: "HINDALCO-EQ", ltp: 670.0, segment: "NSE_EQ", name: "Hindalco Industries Ltd", instrumentType: "EQUITY" },
  HINDUNILVR: { securityId: "1394", tradingSymbol: "HINDUNILVR-EQ", ltp: 2780.0, segment: "NSE_EQ", name: "Hindustan Unilever Ltd", instrumentType: "EQUITY" },
  INDUSINDBK: { securityId: "5258", tradingSymbol: "INDUSINDBK-EQ", ltp: 1420.0, segment: "NSE_EQ", name: "IndusInd Bank Ltd", instrumentType: "EQUITY" },
  JSWSTEEL: { securityId: "11723", tradingSymbol: "JSWSTEEL-EQ", ltp: 940.0, segment: "NSE_EQ", name: "JSW Steel Ltd", instrumentType: "EQUITY" },
  "M&M": { securityId: "2031", tradingSymbol: "M&M-EQ", ltp: 2850.0, segment: "NSE_EQ", name: "Mahindra & Mahindra Ltd", instrumentType: "EQUITY" },
  NESTLEIND: { securityId: "17963", tradingSymbol: "NESTLEIND-EQ", ltp: 2500.0, segment: "NSE_EQ", name: "Nestle India Ltd", instrumentType: "EQUITY" },
  NTPC: { securityId: "11630", tradingSymbol: "NTPC-EQ", ltp: 410.0, segment: "NSE_EQ", name: "NTPC Ltd", instrumentType: "EQUITY" },
  ONGC: { securityId: "2475", tradingSymbol: "ONGC-EQ", ltp: 320.0, segment: "NSE_EQ", name: "Oil & Natural Gas Corporation Ltd", instrumentType: "EQUITY" },
  POWERGRID: { securityId: "14977", tradingSymbol: "POWERGRID-EQ", ltp: 330.0, segment: "NSE_EQ", name: "Power Grid Corporation of India Ltd", instrumentType: "EQUITY" },
  SBILIFE: { securityId: "21808", tradingSymbol: "SBILIFE-EQ", ltp: 1780.0, segment: "NSE_EQ", name: "SBI Life Insurance Co Ltd", instrumentType: "EQUITY" },
  TATACONSUM: { securityId: "3432", tradingSymbol: "TATACONSUM-EQ", ltp: 1180.0, segment: "NSE_EQ", name: "Tata Consumer Products Ltd", instrumentType: "EQUITY" },
  TECHM: { securityId: "13538", tradingSymbol: "TECHM-EQ", ltp: 1580.0, segment: "NSE_EQ", name: "Tech Mahindra Ltd", instrumentType: "EQUITY" },
  ULTRACEMCO: { securityId: "11532", tradingSymbol: "ULTRACEMCO-EQ", ltp: 11200.0, segment: "NSE_EQ", name: "UltraTech Cement Ltd", instrumentType: "EQUITY" },
  ZOMATO: { securityId: "5097", tradingSymbol: "ZOMATO-EQ", ltp: 255.0, segment: "NSE_EQ", name: "Zomato Ltd", instrumentType: "EQUITY" },
  PAYTM: { securityId: "543396", tradingSymbol: "PAYTM-EQ", ltp: 645.0, segment: "NSE_EQ", name: "One 97 Communications Ltd (Paytm)", instrumentType: "EQUITY" },
  TATAPOWER: { securityId: "3426", tradingSymbol: "TATAPOWER-EQ", ltp: 440.0, segment: "NSE_EQ", name: "Tata Power Co Ltd", instrumentType: "EQUITY" },
  IRCTC: { securityId: "13611", tradingSymbol: "IRCTC-EQ", ltp: 920.0, segment: "NSE_EQ", name: "Indian Railway Catering & Tourism Corp", instrumentType: "EQUITY" },
  HAL: { securityId: "2303", tradingSymbol: "HAL-EQ", ltp: 4750.0, segment: "NSE_EQ", name: "Hindustan Aeronautics Ltd", instrumentType: "EQUITY" },
  BEL: { securityId: "383", tradingSymbol: "BEL-EQ", ltp: 305.0, segment: "NSE_EQ", name: "Bharat Electronics Ltd", instrumentType: "EQUITY" },
  VEDL: { securityId: "3063", tradingSymbol: "VEDL-EQ", ltp: 460.0, segment: "NSE_EQ", name: "Vedanta Ltd", instrumentType: "EQUITY" },
  PIDILITIND: { securityId: "2664", tradingSymbol: "PIDILITIND-EQ", ltp: 3150.0, segment: "NSE_EQ", name: "Pidilite Industries Ltd", instrumentType: "EQUITY" },
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
  {
    symbol: "NIFTY MIDCAP 100",
    tradingSymbol: "NIFTY MIDCAP 100",
    securityId: "26",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY MIDCAP 100 INDEX",
    ltp: 58900.0,
    changePct: 0.45,
    aliases: ["NIFTY MIDCAP 100", "NIFTY MIDCAP", "MIDCAP 100", "INDICES"],
  },
  {
    symbol: "BANKEX",
    tradingSymbol: "BSE INDEX BANKEX",
    securityId: "52",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "BSE BANKEX INDEX",
    ltp: 58200.0,
    changePct: -0.15,
    aliases: ["BANKEX", "BSE BANKEX", "INDICES"],
  },
  {
    symbol: "ALLCAP",
    tradingSymbol: "BSE INDEX ALLCAP",
    securityId: "53",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "BSE ALLCAP INDEX",
    ltp: 10400.0,
    changePct: 0.30,
    aliases: ["ALLCAP", "BSE ALLCAP", "INDICES"],
  },
  {
    symbol: "NIFTY 100",
    tradingSymbol: "NIFTY 100",
    securityId: "31",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY 100 INDEX",
    ltp: 25100.0,
    changePct: 0.55,
    aliases: ["NIFTY 100", "NIFTY100", "INDICES"],
  },
  {
    symbol: "NIFTY DIV OPPS 50",
    tradingSymbol: "NIFTY DIV OPPS 50",
    securityId: "32",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY DIVIDEND OPPORTUNITIES 50 INDEX",
    ltp: 6800.0,
    changePct: 0.10,
    aliases: ["NIFTY DIV OPPS 50", "DIV OPPS", "INDICES"],
  },
  {
    symbol: "NIFTY COMMODITIES",
    tradingSymbol: "NIFTY COMMODITIES",
    securityId: "33",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY COMMODITIES INDEX",
    ltp: 9200.0,
    changePct: -0.25,
    aliases: ["NIFTY COMMODITIES", "INDICES"],
  },
  {
    symbol: "NIFTY CONSUMPTION",
    tradingSymbol: "NIFTY CONSUMPTION",
    securityId: "34",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY CONSUMPTION INDEX",
    ltp: 11400.0,
    changePct: 0.40,
    aliases: ["NIFTY CONSUMPTION", "INDICES"],
  },
  {
    symbol: "NIFTY50 PR 2X LEV",
    tradingSymbol: "NIFTY50 PR 2X LEV",
    securityId: "35",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY50 PR 2X LEVERAGED INDEX",
    ltp: 15400.0,
    changePct: 1.30,
    aliases: ["NIFTY50 PR 2X LEV", "INDICES"],
  },
  {
    symbol: "NIFTY50 PR 1X INV",
    tradingSymbol: "NIFTY50 PR 1X INV",
    securityId: "36",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY50 PR 1X INVERSE INDEX",
    ltp: 3200.0,
    changePct: -0.65,
    aliases: ["NIFTY50 PR 1X INV", "INDICES"],
  },
  {
    symbol: "NIFTY50 TR 2X LEV",
    tradingSymbol: "NIFTY50 TR 2X LEV",
    securityId: "37",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY50 TR 2X LEVERAGED INDEX",
    ltp: 16200.0,
    changePct: 1.30,
    aliases: ["NIFTY50 TR 2X LEV", "INDICES"],
  },
  {
    symbol: "NIFTY50 TR 1X INV",
    tradingSymbol: "NIFTY50 TR 1X INV",
    securityId: "38",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY50 TR 1X INVERSE INDEX",
    ltp: 3100.0,
    changePct: -0.65,
    aliases: ["NIFTY50 TR 1X INV", "INDICES"],
  },
  {
    symbol: "NIFTY MIDCAP 50",
    tradingSymbol: "NIFTY MIDCAP 50",
    securityId: "39",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY MIDCAP 50 INDEX",
    ltp: 16100.0,
    changePct: 0.70,
    aliases: ["NIFTY MIDCAP 50", "INDICES"],
  },
  {
    symbol: "NIFTY REALTY",
    tradingSymbol: "NIFTY REALTY",
    securityId: "40",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY REALTY INDEX",
    ltp: 1050.0,
    changePct: 1.85,
    aliases: ["NIFTY REALTY", "INDICES"],
  },
  {
    symbol: "NIFTY INFRA",
    tradingSymbol: "NIFTY INFRA",
    securityId: "41",
    segment: "IDX_I",
    instrumentType: "INDEX",
    name: "NIFTY INFRASTRUCTURE INDEX",
    ltp: 9100.0,
    changePct: 0.35,
    aliases: ["NIFTY INFRA", "INDICES"],
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
    symbol: "HEROMOTOCO",
    tradingSymbol: "HEROMOTOCO-EQ",
    securityId: "1348",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Hero MotoCorp Ltd",
    ltp: 5300.0,
    changePct: -0.16,
    aliases: ["HEROMOTOCO", "HERO"],
  },
  {
    symbol: "MPHASIS",
    tradingSymbol: "MPHASIS-EQ",
    securityId: "4503",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Mphasis Ltd",
    ltp: 3012.0,
    changePct: 0.85,
    aliases: ["MPHASIS"],
  },
  {
    symbol: "CIPLA",
    tradingSymbol: "CIPLA-EQ",
    securityId: "694",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Cipla Ltd",
    ltp: 1385.0,
    changePct: -0.70,
    aliases: ["CIPLA"],
  },
  {
    symbol: "COALINDIA",
    tradingSymbol: "COALINDIA-EQ",
    securityId: "20374",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Coal India Ltd",
    ltp: 415.35,
    changePct: -1.12,
    aliases: ["COALINDIA", "COAL INDIA"],
  },
  {
    symbol: "GODFRYPHLP",
    tradingSymbol: "GODFRYPHLP-EQ",
    securityId: "1232",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Godfrey Phillips India Ltd",
    ltp: 2051.0,
    changePct: 0.29,
    aliases: ["GODFRYPHLP", "GODFREY"],
  },
  {
    symbol: "TECHNOE",
    tradingSymbol: "TECHNOE-EQ",
    securityId: "14880",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Techno Electric & Engineering Co Ltd",
    ltp: 979.50,
    changePct: 0.60,
    aliases: ["TECHNOE", "TECHNO ELECTRIC"],
  },
  {
    symbol: "LTTS",
    tradingSymbol: "LTTS-EQ",
    securityId: "18564",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "L&T Technology Services Ltd",
    ltp: 3493.30,
    changePct: -0.23,
    aliases: ["LTTS"],
  },
  {
    symbol: "MANAPPURAM",
    tradingSymbol: "MANAPPURAM-EQ",
    securityId: "19000",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Manappuram Finance Ltd",
    ltp: 339.70,
    changePct: -0.38,
    aliases: ["MANAPPURAM"],
  },
  {
    symbol: "BODALCHEM",
    tradingSymbol: "BODALCHEM-EQ",
    securityId: "19001",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bodal Chemicals Ltd",
    ltp: 155.62,
    changePct: 3.22,
    aliases: ["BODALCHEM"],
  },
  {
    symbol: "BLSE",
    tradingSymbol: "BLSE-EQ",
    securityId: "19002",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "BLS E-Services Ltd",
    ltp: 320.05,
    changePct: -1.11,
    aliases: ["BLSE"],
  },
  {
    symbol: "MOREPENLAB",
    tradingSymbol: "MOREPENLAB-EQ",
    securityId: "19003",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Morepen Laboratories Ltd",
    ltp: 113.74,
    changePct: -3.16,
    aliases: ["MOREPENLAB"],
  },
  {
    symbol: "TMCV",
    tradingSymbol: "TMCV-EQ",
    securityId: "19005",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tata Motors Commercial Vehicles",
    ltp: 458.20,
    changePct: -0.47,
    aliases: ["TMCV"],
  },
  {
    symbol: "CAMS",
    tradingSymbol: "CAMS-EQ",
    securityId: "19006",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Computer Age Management Services Ltd",
    ltp: 748.80,
    changePct: 0.19,
    aliases: ["CAMS"],
  },
  {
    symbol: "DELTACORP",
    tradingSymbol: "DELTACORP-EQ",
    securityId: "19007",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Delta Corp Ltd",
    ltp: 56.15,
    changePct: -0.34,
    aliases: ["DELTACORP", "DELTA CORP"],
  },
  {
    symbol: "HDFCAMC",
    tradingSymbol: "HDFCAMC-EQ",
    securityId: "19008",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "HDFC Asset Management Co Ltd",
    ltp: 2463.00,
    changePct: -1.62,
    aliases: ["HDFCAMC", "HDFC AMC"],
  },
  {
    symbol: "AARTIIND",
    tradingSymbol: "AARTIIND-EQ",
    securityId: "19009",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Aarti Industries Ltd",
    ltp: 492.05,
    changePct: -1.96,
    aliases: ["AARTIIND", "AARTI"],
  },
  {
    symbol: "IGL",
    tradingSymbol: "IGL-EQ",
    securityId: "19010",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Indraprastha Gas Ltd",
    ltp: 158.05,
    changePct: 5.75,
    aliases: ["IGL"],
  },
  {
    symbol: "STYRFNIX",
    tradingSymbol: "STYRFNIX-EQ",
    securityId: "20005",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "STYRENIX PERFORMANCE",
    ltp: 2150.0,
    changePct: 1.20,
    aliases: ["STYRFNIX"],
  },
  {
    symbol: "SHAREINDIA",
    tradingSymbol: "SHAREINDIA-EQ",
    securityId: "20006",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SHARE IND. SECURITIES",
    ltp: 1420.0,
    changePct: -0.30,
    aliases: ["SHAREINDIA"],
  },
  {
    symbol: "SINTERCOM",
    tradingSymbol: "SINTERCOM-EQ",
    securityId: "20007",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SINTERCOM INDIA",
    ltp: 145.0,
    changePct: 0.80,
    aliases: ["SINTERCOM"],
  },
  {
    symbol: "SHRADHA",
    tradingSymbol: "SHRADHA-EQ",
    securityId: "20008",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SHRADHA REALTY",
    ltp: 72.50,
    changePct: -0.50,
    aliases: ["SHRADHA"],
  },
  {
    symbol: "SHALBY",
    tradingSymbol: "SHALBY-EQ",
    securityId: "20009",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SHALBY LTD",
    ltp: 245.0,
    changePct: 0.60,
    aliases: ["SHALBY"],
  },
  {
    symbol: "SUDARCOLOR",
    tradingSymbol: "SUDARCOLOR-EQ",
    securityId: "20010",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SUDARSHAN COLORANT IND",
    ltp: 680.0,
    changePct: -1.10,
    aliases: ["SUDARCOLOR"],
  },
  {
    symbol: "SHIVATEX",
    tradingSymbol: "SHIVATEX-EQ",
    securityId: "20013",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SHIVA TEXYARN",
    ltp: 195.0,
    changePct: 0.20,
    aliases: ["SHIVATEX"],
  },
  {
    symbol: "SUBEXLTD",
    tradingSymbol: "SUBEXLTD-EQ",
    securityId: "20014",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SUBEX INDIA",
    ltp: 32.50,
    changePct: -0.15,
    aliases: ["SUBEXLTD", "SUBEX"],
  },
  {
    symbol: "SCHAEFFLER",
    tradingSymbol: "SCHAEFFLER-EQ",
    securityId: "20015",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SCHAEFFLER INDIA",
    ltp: 3850.0,
    changePct: 1.40,
    aliases: ["SCHAEFFLER"],
  },
  {
    symbol: "SDBL",
    tradingSymbol: "SDBL-EQ",
    securityId: "20016",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SOM DIST & BREW",
    ltp: 310.0,
    changePct: 0.50,
    aliases: ["SDBL"],
  },
  {
    symbol: "SANOFI",
    tradingSymbol: "SANOFI-EQ",
    securityId: "20017",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SANOFI INDIA",
    ltp: 6800.0,
    changePct: -0.25,
    aliases: ["SANOFI"],
  },
  {
    symbol: "TITAN",
    tradingSymbol: "TITAN-EQ",
    securityId: "3506",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Titan Company Ltd",
    ltp: 3450.0,
    changePct: 0.75,
    aliases: ["TITAN"],
  },
  {
    symbol: "ADANIENT",
    tradingSymbol: "ADANIENT-EQ",
    securityId: "25",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Adani Enterprises Ltd",
    ltp: 3020.0,
    changePct: -0.40,
    aliases: ["ADANIENT", "ADANI"],
  },
  {
    symbol: "ADANIPORTS",
    tradingSymbol: "ADANIPORTS-EQ",
    securityId: "15083",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Adani Ports & SEZ Ltd",
    ltp: 1450.0,
    changePct: 0.90,
    aliases: ["ADANIPORTS"],
  },
  {
    symbol: "ASIANPAINT",
    tradingSymbol: "ASIANPAINT-EQ",
    securityId: "236",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Asian Paints Ltd",
    ltp: 3180.0,
    changePct: -0.30,
    aliases: ["ASIANPAINT", "ASIAN PAINTS"],
  },
  {
    symbol: "BAJAJ-AUTO",
    tradingSymbol: "BAJAJ-AUTO-EQ",
    securityId: "16669",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bajaj Auto Ltd",
    ltp: 10400.0,
    changePct: 1.15,
    aliases: ["BAJAJ AUTO", "BAJAJ-AUTO"],
  },
  {
    symbol: "BAJAJFINSV",
    tradingSymbol: "BAJAJFINSV-EQ",
    securityId: "16675",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bajaj Finserv Ltd",
    ltp: 1720.0,
    changePct: 0.25,
    aliases: ["BAJAJFINSV", "BAJAJ FINSERV"],
  },
  {
    symbol: "BPCL",
    tradingSymbol: "BPCL-EQ",
    securityId: "526",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bharat Petroleum Corporation Ltd",
    ltp: 350.0,
    changePct: -0.60,
    aliases: ["BPCL"],
  },
  {
    symbol: "BRITANNIA",
    tradingSymbol: "BRITANNIA-EQ",
    securityId: "547",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Britannia Industries Ltd",
    ltp: 5800.0,
    changePct: 0.35,
    aliases: ["BRITANNIA"],
  },
  {
    symbol: "DRREDDY",
    tradingSymbol: "DRREDDY-EQ",
    securityId: "881",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Dr. Reddy's Laboratories Ltd",
    ltp: 6600.0,
    changePct: 0.85,
    aliases: ["DRREDDY", "DR REDDY"],
  },
  {
    symbol: "EICHERMOT",
    tradingSymbol: "EICHERMOT-EQ",
    securityId: "910",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Eicher Motors Ltd",
    ltp: 4900.0,
    changePct: 1.40,
    aliases: ["EICHERMOT", "EICHER"],
  },
  {
    symbol: "GRASIM",
    tradingSymbol: "GRASIM-EQ",
    securityId: "1232",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Grasim Industries Ltd",
    ltp: 2650.0,
    changePct: -0.20,
    aliases: ["GRASIM"],
  },
  {
    symbol: "HDFCLIFE",
    tradingSymbol: "HDFCLIFE-EQ",
    securityId: "467",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "HDFC Life Insurance Co Ltd",
    ltp: 710.0,
    changePct: 0.15,
    aliases: ["HDFCLIFE", "HDFC LIFE"],
  },
  {
    symbol: "HINDALCO",
    tradingSymbol: "HINDALCO-EQ",
    securityId: "1363",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Hindalco Industries Ltd",
    ltp: 670.0,
    changePct: 1.10,
    aliases: ["HINDALCO"],
  },
  {
    symbol: "HINDUNILVR",
    tradingSymbol: "HINDUNILVR-EQ",
    securityId: "1394",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Hindustan Unilever Ltd",
    ltp: 2780.0,
    changePct: -0.45,
    aliases: ["HINDUNILVR", "HUL", "HINDUSTAN UNILEVER"],
  },
  {
    symbol: "INDUSINDBK",
    tradingSymbol: "INDUSINDBK-EQ",
    securityId: "5258",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "IndusInd Bank Ltd",
    ltp: 1420.0,
    changePct: -0.80,
    aliases: ["INDUSINDBK", "INDUSIND"],
  },
  {
    symbol: "JSWSTEEL",
    tradingSymbol: "JSWSTEEL-EQ",
    securityId: "11723",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "JSW Steel Ltd",
    ltp: 940.0,
    changePct: 0.50,
    aliases: ["JSWSTEEL", "JSW STEEL"],
  },
  {
    symbol: "M&M",
    tradingSymbol: "M&M-EQ",
    securityId: "2031",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Mahindra & Mahindra Ltd",
    ltp: 2850.0,
    changePct: 1.70,
    aliases: ["M&M", "MAHINDRA"],
  },
  {
    symbol: "NESTLEIND",
    tradingSymbol: "NESTLEIND-EQ",
    securityId: "17963",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Nestle India Ltd",
    ltp: 2500.0,
    changePct: -0.10,
    aliases: ["NESTLEIND", "NESTLE"],
  },
  {
    symbol: "NTPC",
    tradingSymbol: "NTPC-EQ",
    securityId: "11630",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "NTPC Ltd",
    ltp: 410.0,
    changePct: 0.90,
    aliases: ["NTPC"],
  },
  {
    symbol: "ONGC",
    tradingSymbol: "ONGC-EQ",
    securityId: "2475",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Oil & Natural Gas Corporation Ltd",
    ltp: 320.0,
    changePct: 0.40,
    aliases: ["ONGC"],
  },
  {
    symbol: "POWERGRID",
    tradingSymbol: "POWERGRID-EQ",
    securityId: "14977",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Power Grid Corporation of India Ltd",
    ltp: 330.0,
    changePct: 0.60,
    aliases: ["POWERGRID", "POWER GRID"],
  },
  {
    symbol: "SBILIFE",
    tradingSymbol: "SBILIFE-EQ",
    securityId: "21808",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "SBI Life Insurance Co Ltd",
    ltp: 1780.0,
    changePct: -0.25,
    aliases: ["SBILIFE", "SBI LIFE"],
  },
  {
    symbol: "TATACONSUM",
    tradingSymbol: "TATACONSUM-EQ",
    securityId: "3432",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tata Consumer Products Ltd",
    ltp: 1180.0,
    changePct: 0.10,
    aliases: ["TATACONSUM", "TATA CONSUMER"],
  },
  {
    symbol: "TECHM",
    tradingSymbol: "TECHM-EQ",
    securityId: "13538",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tech Mahindra Ltd",
    ltp: 1580.0,
    changePct: -0.50,
    aliases: ["TECHM", "TECH MAHINDRA"],
  },
  {
    symbol: "ULTRACEMCO",
    tradingSymbol: "ULTRACEMCO-EQ",
    securityId: "11532",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "UltraTech Cement Ltd",
    ltp: 11200.0,
    changePct: 0.70,
    aliases: ["ULTRACEMCO", "ULTRATECH"],
  },
  {
    symbol: "ZOMATO",
    tradingSymbol: "ZOMATO-EQ",
    securityId: "5097",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Zomato Ltd",
    ltp: 255.0,
    changePct: 2.30,
    aliases: ["ZOMATO"],
  },
  {
    symbol: "PAYTM",
    tradingSymbol: "PAYTM-EQ",
    securityId: "543396",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "One 97 Communications Ltd (Paytm)",
    ltp: 645.0,
    changePct: -1.20,
    aliases: ["PAYTM", "ONE 97"],
  },
  {
    symbol: "TATAPOWER",
    tradingSymbol: "TATAPOWER-EQ",
    securityId: "3426",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Tata Power Co Ltd",
    ltp: 440.0,
    changePct: 1.50,
    aliases: ["TATAPOWER", "TATA POWER"],
  },
  {
    symbol: "IRCTC",
    tradingSymbol: "IRCTC-EQ",
    securityId: "13611",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Indian Railway Catering & Tourism Corp",
    ltp: 920.0,
    changePct: 0.40,
    aliases: ["IRCTC"],
  },
  {
    symbol: "HAL",
    tradingSymbol: "HAL-EQ",
    securityId: "2303",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Hindustan Aeronautics Ltd",
    ltp: 4750.0,
    changePct: 3.10,
    aliases: ["HAL"],
  },
  {
    symbol: "BEL",
    tradingSymbol: "BEL-EQ",
    securityId: "383",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Bharat Electronics Ltd",
    ltp: 305.0,
    changePct: 1.80,
    aliases: ["BEL"],
  },
  {
    symbol: "VEDL",
    tradingSymbol: "VEDL-EQ",
    securityId: "3063",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Vedanta Ltd",
    ltp: 460.0,
    changePct: 0.90,
    aliases: ["VEDL", "VEDANTA"],
  },
  {
    symbol: "PIDILITIND",
    tradingSymbol: "PIDILITIND-EQ",
    securityId: "2664",
    segment: "NSE_EQ",
    instrumentType: "EQUITY",
    name: "Pidilite Industries Ltd",
    ltp: 3150.0,
    changePct: -0.30,
    aliases: ["PIDILITIND", "PIDILITE"],
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
  {
    symbol: "SILVERCASF",
    tradingSymbol: "SILVERCASF",
    securityId: "20001",
    segment: "BSE_EQ",
    instrumentType: "ETF",
    name: "ZERODHA SILVER ETF",
    ltp: 88.50,
    changePct: 0.50,
    aliases: ["SILVERCASF", "ZERODHA SILVER ETF", "ETF"],
  },
  {
    symbol: "SILCASINAV",
    tradingSymbol: "SILCASINAV",
    securityId: "20002",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "ZERODHA AMC - SILCASINAV",
    ltp: 88.20,
    changePct: 0.40,
    aliases: ["SILCASINAV", "ETF"],
  },
  {
    symbol: "SML100INAV",
    tradingSymbol: "SML100INAV",
    securityId: "20003",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "ZERODHA AMC - SML100NAV",
    ltp: 55.40,
    changePct: 0.15,
    aliases: ["SML100INAV", "ETF"],
  },
  {
    symbol: "SML100CASE",
    tradingSymbol: "SML100CASE",
    securityId: "20004",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "ZERODHA NIFTY SMALLCAP 100 ETF",
    ltp: 55.70,
    changePct: 0.20,
    aliases: ["SML100CASE", "ETF"],
  },
  {
    symbol: "SBIETFPB",
    tradingSymbol: "SBIETFPB-EQ",
    securityId: "20011",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "SBI PRIVATE BANK ETF",
    ltp: 450.0,
    changePct: 0.35,
    aliases: ["SBIETFPB", "ETF"],
  },
  {
    symbol: "SBIETFIT",
    tradingSymbol: "SBIETFIT-EQ",
    securityId: "20012",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "SBI ETF IT ETF",
    ltp: 42.80,
    changePct: -0.45,
    aliases: ["SBIETFIT", "ETF"],
  },
  {
    symbol: "MON100",
    tradingSymbol: "MON100-EQ",
    securityId: "19004",
    segment: "NSE_EQ",
    instrumentType: "ETF",
    name: "Motilal Oswal Nasdaq 100 ETF",
    ltp: 324.67,
    changePct: 0.25,
    aliases: ["MON100", "ETF"],
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
    columns: ["symbol", "ltp", "changeAbs", "changePct", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "volume", "highLow"],
    items: [
      {
        symbol: "MPHASIS",
        segment: "NSE_EQ",
        securityId: "4503",
        tradingSymbol: "MPHASIS-EQ",
        name: "Mphasis Ltd",
        order: 0,
        ltp: 2357.10,
        changePct: -2.68,
        changeAbs: -64.90,
        volume: 366195,
        open: 2409.90,
        prevClose: 2422.00,
        high: 2409.90,
        low: 2340.30,
        avgPrice: 2359.56,
        lowerCircuit: 2179.80,
        upperCircuit: 2664.20,
        ltq: 3,
        ltt: "2026-09-07 11:40:03",
        fiftyTwoWeekHigh: 3125.00,
        fiftyTwoWeekLow: 2180.00,
        bid: 2357.10,
        ask: 2357.50,
      },
      {
        symbol: "RELIANCE",
        segment: "NSE_EQ",
        securityId: "2885",
        tradingSymbol: "RELIANCE-EQ",
        name: "Reliance Industries Ltd",
        order: 1,
        ltp: 2980.50,
        changePct: 1.25,
        changeAbs: 36.75,
        volume: 4250000,
        open: 2955.00,
        prevClose: 2943.75,
        high: 2995.00,
        low: 2950.00,
        avgPrice: 2972.40,
        lowerCircuit: 2649.35,
        upperCircuit: 3238.10,
        ltq: 15,
        ltt: "2026-09-07 11:40:03",
        fiftyTwoWeekHigh: 3217.90,
        fiftyTwoWeekLow: 2220.30,
        bid: 2980.00,
        ask: 2981.00,
      },
      {
        symbol: "TCS",
        segment: "NSE_EQ",
        securityId: "11536",
        tradingSymbol: "TCS-EQ",
        name: "Tata Consultancy Services Ltd",
        order: 2,
        ltp: 4210.00,
        changePct: -0.45,
        changeAbs: -19.00,
        volume: 1850000,
        open: 4235.00,
        prevClose: 4229.00,
        high: 4240.00,
        low: 4195.00,
        avgPrice: 4218.10,
        lowerCircuit: 3806.10,
        upperCircuit: 4651.90,
        ltq: 4,
        ltt: "2026-09-07 11:40:03",
        fiftyTwoWeekHigh: 4585.00,
        fiftyTwoWeekLow: 3313.00,
        bid: 4209.50,
        ask: 4210.50,
      },
      {
        symbol: "HDFCBANK",
        segment: "NSE_EQ",
        securityId: "1333",
        tradingSymbol: "HDFCBANK-EQ",
        name: "HDFC Bank Ltd",
        order: 3,
        ltp: 1640.20,
        changePct: 0.80,
        changeAbs: 13.00,
        volume: 6800000,
        open: 1632.00,
        prevClose: 1627.20,
        high: 1655.00,
        low: 1630.00,
        avgPrice: 1642.50,
        lowerCircuit: 1464.50,
        upperCircuit: 1789.90,
        ltq: 10,
        ltt: "2026-09-07 11:40:03",
        fiftyTwoWeekHigh: 1794.00,
        fiftyTwoWeekLow: 1363.55,
        bid: 1640.00,
        ask: 1640.50,
      },
      {
        symbol: "INFY",
        segment: "NSE_EQ",
        securityId: "1594",
        tradingSymbol: "INFY-EQ",
        name: "Infosys Ltd",
        order: 4,
        ltp: 1890.10,
        changePct: -1.10,
        changeAbs: -21.00,
        volume: 3100000,
        open: 1912.00,
        prevClose: 1911.10,
        high: 1915.00,
        low: 1882.00,
        avgPrice: 1898.30,
        lowerCircuit: 1720.00,
        upperCircuit: 2102.20,
        ltq: 25,
        ltt: "2026-09-07 11:40:03",
        fiftyTwoWeekHigh: 1991.45,
        fiftyTwoWeekLow: 1358.35,
        bid: 1889.50,
        ask: 1890.50,
      },
      {
        symbol: "ICICIBANK",
        segment: "NSE_EQ",
        securityId: "4963",
        tradingSymbol: "ICICIBANK-EQ",
        name: "ICICI Bank Ltd",
        order: 5,
        ltp: 1215.30,
        changePct: 1.65,
        changeAbs: 19.70,
        volume: 5400000,
        open: 1205.00,
        prevClose: 1195.60,
        high: 1222.00,
        low: 1201.00,
        avgPrice: 1211.20,
        lowerCircuit: 1076.00,
        upperCircuit: 1315.15,
        ltq: 50,
        ltt: "2026-09-07 11:40:03",
        fiftyTwoWeekHigh: 1335.00,
        fiftyTwoWeekLow: 980.00,
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
    columns: ["symbol", "ltp", "changeAbs", "changePct", "oi", "oiChangePct", "volume"],
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
    columns: ["symbol", "ltp", "changeAbs", "changePct", "volume", "highLow"],
    items: [
      {
        symbol: "TATASTEEL",
        segment: "NSE_EQ",
        securityId: "3499",
        tradingSymbol: "TATASTEEL-EQ",
        name: "Tata Steel Ltd",
        order: 0,
        ltp: 154.80,
        changePct: 2.85,
        changeAbs: 4.30,
        volume: 12400000,
        high: 156.50,
        low: 150.20,
        open: 151.00,
        prevClose: 150.50,
        fiftyTwoWeekHigh: 184.60,
        fiftyTwoWeekLow: 114.60,
      },
      {
        symbol: "SBIN",
        segment: "NSE_EQ",
        securityId: "3045",
        tradingSymbol: "SBIN-EQ",
        name: "State Bank of India",
        order: 1,
        ltp: 815.40,
        changePct: 1.15,
        changeAbs: 9.25,
        volume: 7600000,
        high: 822.00,
        low: 808.00,
        open: 810.00,
        prevClose: 806.15,
        fiftyTwoWeekHigh: 912.00,
        fiftyTwoWeekLow: 555.00,
      },
    ],
  },
];

export function loadWatchlists(): Watchlist[] {
  try {
    let raw = localStorage.getItem(WATCHLISTS_STORAGE_KEY_V2);
    let isMigratingV1 = false;
    if (!raw) {
      raw = localStorage.getItem(WATCHLISTS_STORAGE_KEY_V1);
      if (raw) isMigratingV1 = true;
    }
    if (!raw) {
      saveWatchlists(DEFAULT_WATCHLISTS);
      return DEFAULT_WATCHLISTS;
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      // Purge/sanitize: re-resolve missing security IDs and ensure new default columns & 52w metrics
      const sanitized = parsed.map((wl: Watchlist) => {
        let cols = [...(wl.columns || ["symbol", "ltp", "changePct", "volume"])];
        if (isMigratingV1) {
          // If migrating from v1, ensure changeAbs and 52w columns are enabled
          const pctIdx = cols.indexOf("changePct");
          if (pctIdx !== -1 && !cols.includes("changeAbs")) {
            cols.splice(pctIdx, 0, "changeAbs");
          }
          if (!cols.includes("fiftyTwoWeekHigh")) cols.push("fiftyTwoWeekHigh");
          if (!cols.includes("fiftyTwoWeekLow")) cols.push("fiftyTwoWeekLow");
        }
        return {
          ...wl,
          columns: cols,
          items: (wl.items || []).map((it) => {
            const known = KNOWN_EQUITY_INSTRUMENTS[it.symbol];
            return {
              ...it,
              securityId:
                (!it.securityId || it.securityId.trim() === "") && known
                  ? known.securityId
                  : it.securityId,
              tradingSymbol: it.tradingSymbol || known?.tradingSymbol,
              fiftyTwoWeekHigh: it.fiftyTwoWeekHigh ?? known?.fiftyTwoWeekHigh,
              fiftyTwoWeekLow: it.fiftyTwoWeekLow ?? known?.fiftyTwoWeekLow,
            };
          }),
        };
      });
      if (isMigratingV1) {
        saveWatchlists(sanitized);
      }
      return sanitized;
    }
  } catch {
    // Fall back gracefully on corrupt storage
  }
  return DEFAULT_WATCHLISTS;
}

export function saveWatchlists(watchlists: Watchlist[]): void {
  try {
    localStorage.setItem(WATCHLISTS_STORAGE_KEY_V2, JSON.stringify(watchlists));
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
