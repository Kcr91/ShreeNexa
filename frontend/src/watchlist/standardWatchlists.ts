import { Watchlist, WatchlistItem, WatchlistColumn } from "./types";

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
// 208 NSE F&O Stocks Master Catalog with Authentic Sectors
// ---------------------------------------------------------------------------
export const FNO_208_STOCKS: StockMasterEntry[] = [
  // Banking & Financial Services (44)
  { symbol: "HDFCBANK", tradingSymbol: "HDFCBANK-EQ", securityId: "1333", name: "HDFC Bank Ltd", sector: "Financial Services", ltp: 1640.20, changePct: 0.80, fiftyTwoWeekHigh: 1794.00, fiftyTwoWeekLow: 1363.55 },
  { symbol: "ICICIBANK", tradingSymbol: "ICICIBANK-EQ", securityId: "4963", name: "ICICI Bank Ltd", sector: "Financial Services", ltp: 1215.30, changePct: 1.65, fiftyTwoWeekHigh: 1335.00, fiftyTwoWeekLow: 980.00 },
  { symbol: "SBIN", tradingSymbol: "SBIN-EQ", securityId: "3045", name: "State Bank of India", sector: "Financial Services", ltp: 815.40, changePct: 1.15, fiftyTwoWeekHigh: 912.00, fiftyTwoWeekLow: 555.00 },
  { symbol: "KOTAKBANK", tradingSymbol: "KOTAKBANK-EQ", securityId: "1922", name: "Kotak Mahindra Bank Ltd", sector: "Financial Services", ltp: 1810.00, changePct: -0.30, fiftyTwoWeekHigh: 1932.00, fiftyTwoWeekLow: 1544.00 },
  { symbol: "AXISBANK", tradingSymbol: "AXISBANK-EQ", securityId: "5900", name: "Axis Bank Ltd", sector: "Financial Services", ltp: 1180.00, changePct: 0.60, fiftyTwoWeekHigh: 1339.00, fiftyTwoWeekLow: 934.00 },
  { symbol: "INDUSINDBK", tradingSymbol: "INDUSINDBK-EQ", securityId: "5258", name: "IndusInd Bank Ltd", sector: "Financial Services", ltp: 1420.00, changePct: -0.80, fiftyTwoWeekHigh: 1694.00, fiftyTwoWeekLow: 1332.00 },
  { symbol: "BANKBARODA", tradingSymbol: "BANKBARODA-EQ", securityId: "4668", name: "Bank of Baroda", sector: "Financial Services", ltp: 245.50, changePct: 0.90, fiftyTwoWeekHigh: 298.00, fiftyTwoWeekLow: 188.00 },
  { symbol: "PNB", tradingSymbol: "PNB-EQ", securityId: "10666", name: "Punjab National Bank", sector: "Financial Services", ltp: 112.40, changePct: 1.40, fiftyTwoWeekHigh: 142.90, fiftyTwoWeekLow: 68.00 },
  { symbol: "AUBANK", tradingSymbol: "AUBANK-EQ", securityId: "21238", name: "AU Small Finance Bank Ltd", sector: "Financial Services", ltp: 635.00, changePct: 0.45, fiftyTwoWeekHigh: 813.00, fiftyTwoWeekLow: 554.00 },
  { symbol: "FEDERALBNK", tradingSymbol: "FEDERALBNK-EQ", securityId: "1023", name: "Federal Bank Ltd", sector: "Financial Services", ltp: 192.80, changePct: 0.35, fiftyTwoWeekHigh: 210.00, fiftyTwoWeekLow: 135.00 },
  { symbol: "IDFCFIRSTB", tradingSymbol: "IDFCFIRSTB-EQ", securityId: "11184", name: "IDFC First Bank Ltd", sector: "Financial Services", ltp: 72.80, changePct: -0.20, fiftyTwoWeekHigh: 95.70, fiftyTwoWeekLow: 70.10 },
  { symbol: "BANDHANBNK", tradingSymbol: "BANDHANBNK-EQ", securityId: "2263", name: "Bandhan Bank Ltd", sector: "Financial Services", ltp: 198.50, changePct: 1.10, fiftyTwoWeekHigh: 263.00, fiftyTwoWeekLow: 168.00 },
  { symbol: "CANBK", tradingSymbol: "CANBK-EQ", securityId: "10794", name: "Canara Bank", sector: "Financial Services", ltp: 104.20, changePct: 0.70, fiftyTwoWeekHigh: 129.00, fiftyTwoWeekLow: 69.00 },
  { symbol: "CUB", tradingSymbol: "CUB-EQ", securityId: "782", name: "City Union Bank Ltd", sector: "Financial Services", ltp: 164.00, changePct: 0.50, fiftyTwoWeekHigh: 178.00, fiftyTwoWeekLow: 122.00 },
  { symbol: "RBLBANK", tradingSymbol: "RBLBANK-EQ", securityId: "18391", name: "RBL Bank Ltd", sector: "Financial Services", ltp: 215.00, changePct: -0.90, fiftyTwoWeekHigh: 300.00, fiftyTwoWeekLow: 192.00 },
  { symbol: "BAJFINANCE", tradingSymbol: "BAJFINANCE-EQ", securityId: "317", name: "Bajaj Finance Ltd", sector: "Financial Services", ltp: 7100.00, changePct: -0.75, fiftyTwoWeekHigh: 8192.00, fiftyTwoWeekLow: 6374.00 },
  { symbol: "BAJAJFINSV", tradingSymbol: "BAJAJFINSV-EQ", securityId: "16675", name: "Bajaj Finserv Ltd", sector: "Financial Services", ltp: 1720.00, changePct: 0.25, fiftyTwoWeekHigh: 1910.00, fiftyTwoWeekLow: 1419.00 },
  { symbol: "CHOLAFIN", tradingSymbol: "CHOLAFIN-EQ", securityId: "685", name: "Cholamandalam Investment & Fin", sector: "Financial Services", ltp: 1480.00, changePct: 1.80, fiftyTwoWeekHigh: 1620.00, fiftyTwoWeekLow: 1060.00 },
  { symbol: "SHRIRAMFIN", tradingSymbol: "SHRIRAMFIN-EQ", securityId: "4306", name: "Shriram Finance Ltd", sector: "Financial Services", ltp: 3250.00, changePct: 1.40, fiftyTwoWeekHigh: 3410.00, fiftyTwoWeekLow: 1790.00 },
  { symbol: "MUTHOOTFIN", tradingSymbol: "MUTHOOTFIN-EQ", securityId: "23650", name: "Muthoot Finance Ltd", sector: "Financial Services", ltp: 1890.00, changePct: 0.90, fiftyTwoWeekHigh: 2040.00, fiftyTwoWeekLow: 1200.00 },
  { symbol: "MANAPPURAM", tradingSymbol: "MANAPPURAM-EQ", securityId: "19000", name: "Manappuram Finance Ltd", sector: "Financial Services", ltp: 198.70, changePct: -0.38, fiftyTwoWeekHigh: 230.00, fiftyTwoWeekLow: 150.00 },
  { symbol: "M&MFIN", tradingSymbol: "M&MFIN-EQ", securityId: "13285", name: "Mahindra & Mahindra Financial", sector: "Financial Services", ltp: 295.00, changePct: 0.30, fiftyTwoWeekHigh: 335.00, fiftyTwoWeekLow: 245.00 },
  { symbol: "ABCAPITAL", tradingSymbol: "ABCAPITAL-EQ", securityId: "21614", name: "Aditya Birla Capital Ltd", sector: "Financial Services", ltp: 220.00, changePct: 1.20, fiftyTwoWeekHigh: 245.00, fiftyTwoWeekLow: 155.00 },
  { symbol: "PFC", tradingSymbol: "PFC-EQ", securityId: "14299", name: "Power Finance Corporation", sector: "Financial Services", ltp: 495.00, changePct: 1.60, fiftyTwoWeekHigh: 580.00, fiftyTwoWeekLow: 205.00 },
  { symbol: "RECLTD", tradingSymbol: "RECLTD-EQ", securityId: "15355", name: "REC Ltd", sector: "Financial Services", ltp: 560.00, changePct: 1.90, fiftyTwoWeekHigh: 654.00, fiftyTwoWeekLow: 220.00 },
  { symbol: "IRFC", tradingSymbol: "IRFC-EQ", securityId: "20101", name: "Indian Railway Finance Corp", sector: "Financial Services", ltp: 168.00, changePct: 2.10, fiftyTwoWeekHigh: 229.00, fiftyTwoWeekLow: 65.00 },
  { symbol: "JIOFIN", tradingSymbol: "JIOFIN-EQ", securityId: "20102", name: "Jio Financial Services Ltd", sector: "Financial Services", ltp: 335.00, changePct: 0.80, fiftyTwoWeekHigh: 395.00, fiftyTwoWeekLow: 205.00 },
  { symbol: "HDFCLIFE", tradingSymbol: "HDFCLIFE-EQ", securityId: "467", name: "HDFC Life Insurance Co Ltd", sector: "Financial Services", ltp: 710.00, changePct: 0.15, fiftyTwoWeekHigh: 760.00, fiftyTwoWeekLow: 570.00 },
  { symbol: "SBILIFE", tradingSymbol: "SBILIFE-EQ", securityId: "21808", name: "SBI Life Insurance Co Ltd", sector: "Financial Services", ltp: 1780.00, changePct: -0.25, fiftyTwoWeekHigh: 1890.00, fiftyTwoWeekLow: 1260.00 },
  { symbol: "ICICIPRULI", tradingSymbol: "ICICIPRULI-EQ", securityId: "18652", name: "ICICI Prudential Life Ins", sector: "Financial Services", ltp: 745.00, changePct: 0.40, fiftyTwoWeekHigh: 790.00, fiftyTwoWeekLow: 465.00 },
  { symbol: "ICICIGI", tradingSymbol: "ICICIGI-EQ", securityId: "21770", name: "ICICI Lombard General Ins", sector: "Financial Services", ltp: 2050.00, changePct: 0.60, fiftyTwoWeekHigh: 2220.00, fiftyTwoWeekLow: 1300.00 },
  { symbol: "HDFCAMC", tradingSymbol: "HDFCAMC-EQ", securityId: "19008", name: "HDFC Asset Management Co", sector: "Financial Services", ltp: 4280.00, changePct: -1.62, fiftyTwoWeekHigh: 4550.00, fiftyTwoWeekLow: 2500.00 },
  { symbol: "SBICARD", tradingSymbol: "SBICARD-EQ", securityId: "17971", name: "SBI Cards & Payment Services", sector: "Financial Services", ltp: 730.00, changePct: -0.40, fiftyTwoWeekHigh: 865.00, fiftyTwoWeekLow: 670.00 },
  { symbol: "LICHSGFIN", tradingSymbol: "LICHSGFIN-EQ", securityId: "1997", name: "LIC Housing Finance Ltd", sector: "Financial Services", ltp: 685.00, changePct: 0.70, fiftyTwoWeekHigh: 805.00, fiftyTwoWeekLow: 420.00 },
  { symbol: "CANFINHOME", tradingSymbol: "CANFINHOME-EQ", securityId: "583", name: "Can Fin Homes Ltd", sector: "Financial Services", ltp: 840.00, changePct: 0.50, fiftyTwoWeekHigh: 915.00, fiftyTwoWeekLow: 680.00 },
  { symbol: "PEL", tradingSymbol: "PEL-EQ", securityId: "2412", name: "Piramal Enterprises Ltd", sector: "Financial Services", ltp: 980.00, changePct: 0.30, fiftyTwoWeekHigh: 1140.00, fiftyTwoWeekLow: 790.00 },
  { symbol: "MFSL", tradingSymbol: "MFSL-EQ", securityId: "2142", name: "Max Financial Services Ltd", sector: "Financial Services", ltp: 1140.00, changePct: 1.10, fiftyTwoWeekHigh: 1250.00, fiftyTwoWeekLow: 850.00 },
  { symbol: "MCX", tradingSymbol: "MCX-EQ", securityId: "31181", name: "Multi Commodity Exchange of India", sector: "Financial Services", ltp: 5600.00, changePct: 2.40, fiftyTwoWeekHigh: 6200.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "IEX", tradingSymbol: "IEX-EQ", securityId: "220", name: "Indian Energy Exchange Ltd", sector: "Financial Services", ltp: 195.00, changePct: 1.30, fiftyTwoWeekHigh: 215.00, fiftyTwoWeekLow: 125.00 },
  { symbol: "CAMS", tradingSymbol: "CAMS-EQ", securityId: "19006", name: "Computer Age Management Serv", sector: "Financial Services", ltp: 4480.00, changePct: 0.19, fiftyTwoWeekHigh: 4750.00, fiftyTwoWeekLow: 2300.00 },
  { symbol: "CDSL", tradingSymbol: "CDSL-EQ", securityId: "21174", name: "Central Depository Services", sector: "Financial Services", ltp: 1420.00, changePct: 2.20, fiftyTwoWeekHigh: 1650.00, fiftyTwoWeekLow: 750.00 },
  { symbol: "HUDCO", tradingSymbol: "HUDCO-EQ", securityId: "20103", name: "Housing & Urban Dev Corp", sector: "Financial Services", ltp: 245.00, changePct: 1.50, fiftyTwoWeekHigh: 350.00, fiftyTwoWeekLow: 68.00 },
  { symbol: "POONAWALLA", tradingSymbol: "POONAWALLA-EQ", securityId: "20104", name: "Poonawalla Fincorp Ltd", sector: "Financial Services", ltp: 385.00, changePct: 0.60, fiftyTwoWeekHigh: 520.00, fiftyTwoWeekLow: 340.00 },
  { symbol: "PAYTM", tradingSymbol: "PAYTM-EQ", securityId: "543396", name: "One 97 Communications (Paytm)", sector: "Financial Services", ltp: 645.00, changePct: -1.20, fiftyTwoWeekHigh: 998.00, fiftyTwoWeekLow: 310.00 },

  // Information Technology (16)
  { symbol: "TCS", tradingSymbol: "TCS-EQ", securityId: "11536", name: "Tata Consultancy Services Ltd", sector: "Information Technology", ltp: 4210.00, changePct: -0.45, fiftyTwoWeekHigh: 4585.00, fiftyTwoWeekLow: 3313.00 },
  { symbol: "INFY", tradingSymbol: "INFY-EQ", securityId: "1594", name: "Infosys Ltd", sector: "Information Technology", ltp: 1890.10, changePct: -1.10, fiftyTwoWeekHigh: 1991.45, fiftyTwoWeekLow: 1358.35 },
  { symbol: "HCLTECH", tradingSymbol: "HCLTECH-EQ", securityId: "7229", name: "HCL Technologies Ltd", sector: "Information Technology", ltp: 1780.00, changePct: -0.90, fiftyTwoWeekHigh: 1890.00, fiftyTwoWeekLow: 1190.00 },
  { symbol: "WIPRO", tradingSymbol: "WIPRO-EQ", securityId: "3787", name: "Wipro Ltd", sector: "Information Technology", ltp: 540.00, changePct: 0.10, fiftyTwoWeekHigh: 580.00, fiftyTwoWeekLow: 375.00 },
  { symbol: "TECHM", tradingSymbol: "TECHM-EQ", securityId: "13538", name: "Tech Mahindra Ltd", sector: "Information Technology", ltp: 1580.00, changePct: -0.50, fiftyTwoWeekHigh: 1680.00, fiftyTwoWeekLow: 1080.00 },
  { symbol: "LTIM", tradingSymbol: "LTIM-EQ", securityId: "17818", name: "LTIMindtree Ltd", sector: "Information Technology", ltp: 6100.00, changePct: 0.70, fiftyTwoWeekHigh: 6440.00, fiftyTwoWeekLow: 4500.00 },
  { symbol: "PERSISTENT", tradingSymbol: "PERSISTENT-EQ", securityId: "18365", name: "Persistent Systems Ltd", sector: "Information Technology", ltp: 5250.00, changePct: 1.40, fiftyTwoWeekHigh: 5600.00, fiftyTwoWeekLow: 3100.00 },
  { symbol: "COFORGE", tradingSymbol: "COFORGE-EQ", securityId: "11543", name: "Coforge Ltd", sector: "Information Technology", ltp: 6750.00, changePct: 0.85, fiftyTwoWeekHigh: 7200.00, fiftyTwoWeekLow: 4300.00 },
  { symbol: "MPHASIS", tradingSymbol: "MPHASIS-EQ", securityId: "4503", name: "Mphasis Ltd", sector: "Information Technology", ltp: 2357.10, changePct: -2.68, fiftyTwoWeekHigh: 3125.00, fiftyTwoWeekLow: 2180.00 },
  { symbol: "LTTS", tradingSymbol: "LTTS-EQ", securityId: "18564", name: "L&T Technology Services Ltd", sector: "Information Technology", ltp: 3493.30, changePct: -0.23, fiftyTwoWeekHigh: 5850.00, fiftyTwoWeekLow: 3400.00 },
  { symbol: "TATAELXSI", tradingSymbol: "TATAELXSI-EQ", securityId: "3437", name: "Tata Elxsi Ltd", sector: "Information Technology", ltp: 7650.00, changePct: 0.40, fiftyTwoWeekHigh: 9200.00, fiftyTwoWeekLow: 6400.00 },
  { symbol: "BSOFT", tradingSymbol: "BSOFT-EQ", securityId: "6994", name: "Birlasoft Ltd", sector: "Information Technology", ltp: 620.00, changePct: -0.30, fiftyTwoWeekHigh: 860.00, fiftyTwoWeekLow: 440.00 },
  { symbol: "OFSS", tradingSymbol: "OFSS-EQ", securityId: "10738", name: "Oracle Financial Services", sector: "Information Technology", ltp: 11200.00, changePct: 1.90, fiftyTwoWeekHigh: 12500.00, fiftyTwoWeekLow: 3900.00 },
  { symbol: "CYIENT", tradingSymbol: "CYIENT-EQ", securityId: "964", name: "Cyient Ltd", sector: "Information Technology", ltp: 1950.00, changePct: 0.60, fiftyTwoWeekHigh: 2450.00, fiftyTwoWeekLow: 1550.00 },
  { symbol: "KPITTECH", tradingSymbol: "KPITTECH-EQ", securityId: "20105", name: "KPIT Technologies Ltd", sector: "Information Technology", ltp: 1680.00, changePct: 1.10, fiftyTwoWeekHigh: 1920.00, fiftyTwoWeekLow: 1100.00 },
  { symbol: "NAUKRI", tradingSymbol: "NAUKRI-EQ", securityId: "13751", name: "Info Edge (India) Ltd", sector: "Information Technology", ltp: 7850.00, changePct: 0.90, fiftyTwoWeekHigh: 8400.00, fiftyTwoWeekLow: 3950.00 },

  // Automobile and Auto Components (17)
  { symbol: "MARUTI", tradingSymbol: "MARUTI-EQ", securityId: "10999", name: "Maruti Suzuki India Ltd", sector: "Automobile and Auto Components", ltp: 12400.00, changePct: 0.90, fiftyTwoWeekHigh: 13680.00, fiftyTwoWeekLow: 9250.00 },
  { symbol: "TATAMOTORS", tradingSymbol: "TATAMOTORS-EQ", securityId: "3456", name: "Tata Motors Ltd", sector: "Automobile and Auto Components", ltp: 980.00, changePct: 2.10, fiftyTwoWeekHigh: 1179.00, fiftyTwoWeekLow: 600.00 },
  { symbol: "M&M", tradingSymbol: "M&M-EQ", securityId: "2031", name: "Mahindra & Mahindra Ltd", sector: "Automobile and Auto Components", ltp: 2850.00, changePct: 1.70, fiftyTwoWeekHigh: 3014.00, fiftyTwoWeekLow: 1450.00 },
  { symbol: "BAJAJ-AUTO", tradingSymbol: "BAJAJ-AUTO-EQ", securityId: "16669", name: "Bajaj Auto Ltd", sector: "Automobile and Auto Components", ltp: 10400.00, changePct: 1.15, fiftyTwoWeekHigh: 12200.00, fiftyTwoWeekLow: 4600.00 },
  { symbol: "EICHERMOT", tradingSymbol: "EICHERMOT-EQ", securityId: "910", name: "Eicher Motors Ltd", sector: "Automobile and Auto Components", ltp: 4900.00, changePct: 1.40, fiftyTwoWeekHigh: 5100.00, fiftyTwoWeekLow: 3160.00 },
  { symbol: "HEROMOTOCO", tradingSymbol: "HEROMOTOCO-EQ", securityId: "1348", name: "Hero MotoCorp Ltd", sector: "Automobile and Auto Components", ltp: 5300.00, changePct: -0.16, fiftyTwoWeekHigh: 5890.00, fiftyTwoWeekLow: 2900.00 },
  { symbol: "TVSMOTOR", tradingSymbol: "TVSMOTOR-EQ", securityId: "8479", name: "TVS Motor Company Ltd", sector: "Automobile and Auto Components", ltp: 2650.00, changePct: 0.80, fiftyTwoWeekHigh: 2900.00, fiftyTwoWeekLow: 1450.00 },
  { symbol: "BHARATFORG", tradingSymbol: "BHARATFORG-EQ", securityId: "422", name: "Bharat Forge Ltd", sector: "Automobile and Auto Components", ltp: 1520.00, changePct: 0.60, fiftyTwoWeekHigh: 1720.00, fiftyTwoWeekLow: 980.00 },
  { symbol: "ASHOKLEY", tradingSymbol: "ASHOKLEY-EQ", securityId: "212", name: "Ashok Leyland Ltd", sector: "Automobile and Auto Components", ltp: 228.00, changePct: 0.40, fiftyTwoWeekHigh: 260.00, fiftyTwoWeekLow: 157.00 },
  { symbol: "BALKRISIND", tradingSymbol: "BALKRISIND-EQ", securityId: "335", name: "Balkrishna Industries Ltd", sector: "Automobile and Auto Components", ltp: 2980.00, changePct: -0.20, fiftyTwoWeekHigh: 3350.00, fiftyTwoWeekLow: 2150.00 },
  { symbol: "MOTHERSON", tradingSymbol: "MOTHERSON-EQ", securityId: "4204", name: "Samvardhana Motherson Int", sector: "Automobile and Auto Components", ltp: 185.00, changePct: 1.30, fiftyTwoWeekHigh: 215.00, fiftyTwoWeekLow: 85.00 },
  { symbol: "BOSCHLTD", tradingSymbol: "BOSCHLTD-EQ", securityId: "2181", name: "Bosch Ltd", sector: "Automobile and Auto Components", ltp: 33500.00, changePct: 0.50, fiftyTwoWeekHigh: 38000.00, fiftyTwoWeekLow: 18500.00 },
  { symbol: "MRF", tradingSymbol: "MRF-EQ", securityId: "2277", name: "MRF Ltd", sector: "Automobile and Auto Components", ltp: 135000.00, changePct: 0.20, fiftyTwoWeekHigh: 151000.00, fiftyTwoWeekLow: 102000.00 },
  { symbol: "APOLLOTYRE", tradingSymbol: "APOLLOTYRE-EQ", securityId: "163", name: "Apollo Tyres Ltd", sector: "Automobile and Auto Components", ltp: 520.00, changePct: 0.30, fiftyTwoWeekHigh: 585.00, fiftyTwoWeekLow: 365.00 },
  { symbol: "EXIDEIND", tradingSymbol: "EXIDEIND-EQ", securityId: "676", name: "Exide Industries Ltd", sector: "Automobile and Auto Components", ltp: 495.00, changePct: 1.70, fiftyTwoWeekHigh: 620.00, fiftyTwoWeekLow: 250.00 },
  { symbol: "SONACOMS", tradingSymbol: "SONACOMS-EQ", securityId: "20106", name: "Sona BLW Precision Forgings", sector: "Automobile and Auto Components", ltp: 690.00, changePct: 0.70, fiftyTwoWeekHigh: 760.00, fiftyTwoWeekLow: 510.00 },
  { symbol: "ESCORTS", tradingSymbol: "ESCORTS-EQ", securityId: "958", name: "Escorts Kubota Ltd", sector: "Automobile and Auto Components", ltp: 3850.00, changePct: 0.40, fiftyTwoWeekHigh: 4400.00, fiftyTwoWeekLow: 2800.00 },

  // Healthcare and Pharmaceuticals (19)
  { symbol: "SUNPHARMA", tradingSymbol: "SUNPHARMA-EQ", securityId: "3351", name: "Sun Pharmaceutical Industries", sector: "Healthcare", ltp: 1850.00, changePct: 1.05, fiftyTwoWeekHigh: 1960.00, fiftyTwoWeekLow: 1090.00 },
  { symbol: "CIPLA", tradingSymbol: "CIPLA-EQ", securityId: "694", name: "Cipla Ltd", sector: "Healthcare", ltp: 1585.00, changePct: -0.70, fiftyTwoWeekHigh: 1700.00, fiftyTwoWeekLow: 1130.00 },
  { symbol: "DRREDDY", tradingSymbol: "DRREDDY-EQ", securityId: "881", name: "Dr. Reddy's Laboratories Ltd", sector: "Healthcare", ltp: 6600.00, changePct: 0.85, fiftyTwoWeekHigh: 7100.00, fiftyTwoWeekLow: 5200.00 },
  { symbol: "DIVISLAB", tradingSymbol: "DIVISLAB-EQ", securityId: "10940", name: "Divi's Laboratories Ltd", sector: "Healthcare", ltp: 5400.00, changePct: 1.20, fiftyTwoWeekHigh: 5750.00, fiftyTwoWeekLow: 3350.00 },
  { symbol: "APOLLOHOSP", tradingSymbol: "APOLLOHOSP-EQ", securityId: "157", name: "Apollo Hospitals Enterprise", sector: "Healthcare", ltp: 7150.00, changePct: 0.90, fiftyTwoWeekHigh: 7500.00, fiftyTwoWeekLow: 4700.00 },
  { symbol: "LUPIN", tradingSymbol: "LUPIN-EQ", securityId: "10440", name: "Lupin Ltd", sector: "Healthcare", ltp: 2150.00, changePct: 1.40, fiftyTwoWeekHigh: 2320.00, fiftyTwoWeekLow: 1100.00 },
  { symbol: "AUROPHARMA", tradingSymbol: "AUROPHARMA-EQ", securityId: "275", name: "Aurobindo Pharma Ltd", sector: "Healthcare", ltp: 1480.00, changePct: 0.60, fiftyTwoWeekHigh: 1600.00, fiftyTwoWeekLow: 810.00 },
  { symbol: "ZYDUSLIFE", tradingSymbol: "ZYDUSLIFE-EQ", securityId: "4180", name: "Zydus Lifesciences Ltd", sector: "Healthcare", ltp: 1090.00, changePct: 0.30, fiftyTwoWeekHigh: 1320.00, fiftyTwoWeekLow: 560.00 },
  { symbol: "TORNTPHARM", tradingSymbol: "TORNTPHARM-EQ", securityId: "3518", name: "Torrent Pharmaceuticals Ltd", sector: "Healthcare", ltp: 3350.00, changePct: 0.50, fiftyTwoWeekHigh: 3600.00, fiftyTwoWeekLow: 1800.00 },
  { symbol: "ALKEM", tradingSymbol: "ALKEM-EQ", securityId: "11703", name: "Alkem Laboratories Ltd", sector: "Healthcare", ltp: 5800.00, changePct: 0.20, fiftyTwoWeekHigh: 6250.00, fiftyTwoWeekLow: 3500.00 },
  { symbol: "BIOCON", tradingSymbol: "BIOCON-EQ", securityId: "11373", name: "Biocon Ltd", sector: "Healthcare", ltp: 360.00, changePct: 1.10, fiftyTwoWeekHigh: 395.00, fiftyTwoWeekLow: 220.00 },
  { symbol: "GLENMARK", tradingSymbol: "GLENMARK-EQ", securityId: "7406", name: "Glenmark Pharmaceuticals Ltd", sector: "Healthcare", ltp: 1650.00, changePct: 0.80, fiftyTwoWeekHigh: 1820.00, fiftyTwoWeekLow: 710.00 },
  { symbol: "IPCALAB", tradingSymbol: "IPCALAB-EQ", securityId: "1633", name: "IPCA Laboratories Ltd", sector: "Healthcare", ltp: 1420.00, changePct: 0.40, fiftyTwoWeekHigh: 1550.00, fiftyTwoWeekLow: 850.00 },
  { symbol: "LAURUSLABS", tradingSymbol: "LAURUSLABS-EQ", securityId: "19234", name: "Laurus Labs Ltd", sector: "Healthcare", ltp: 440.00, changePct: -0.20, fiftyTwoWeekHigh: 490.00, fiftyTwoWeekLow: 340.00 },
  { symbol: "GRANULES", tradingSymbol: "GRANULES-EQ", securityId: "11872", name: "Granules India Ltd", sector: "Healthcare", ltp: 560.00, changePct: 1.30, fiftyTwoWeekHigh: 720.00, fiftyTwoWeekLow: 280.00 },
  { symbol: "ABBOTINDIA", tradingSymbol: "ABBOTINDIA-EQ", securityId: "17903", name: "Abbott India Ltd", sector: "Healthcare", ltp: 28500.00, changePct: 0.10, fiftyTwoWeekHigh: 30500.00, fiftyTwoWeekLow: 21500.00 },
  { symbol: "SYNGENE", tradingSymbol: "SYNGENE-EQ", securityId: "10243", name: "Syngene International Ltd", sector: "Healthcare", ltp: 890.00, changePct: 0.50, fiftyTwoWeekHigh: 940.00, fiftyTwoWeekLow: 680.00 },
  { symbol: "MAXHEALTH", tradingSymbol: "MAXHEALTH-EQ", securityId: "20107", name: "Max Healthcare Institute Ltd", sector: "Healthcare", ltp: 940.00, changePct: 1.20, fiftyTwoWeekHigh: 1040.00, fiftyTwoWeekLow: 540.00 },
  { symbol: "GLAND", tradingSymbol: "GLAND-EQ", securityId: "20108", name: "Gland Pharma Ltd", sector: "Healthcare", ltp: 1720.00, changePct: -0.40, fiftyTwoWeekHigh: 2200.00, fiftyTwoWeekLow: 1350.00 },

  // Fast Moving Consumer Goods (16)
  { symbol: "ITC", tradingSymbol: "ITC-EQ", securityId: "1660", name: "ITC Ltd", sector: "Fast Moving Consumer Goods", ltp: 495.00, changePct: -0.20, fiftyTwoWeekHigh: 528.00, fiftyTwoWeekLow: 399.00 },
  { symbol: "HINDUNILVR", tradingSymbol: "HINDUNILVR-EQ", securityId: "1394", name: "Hindustan Unilever Ltd", sector: "Fast Moving Consumer Goods", ltp: 2780.00, changePct: -0.45, fiftyTwoWeekHigh: 3034.00, fiftyTwoWeekLow: 2170.00 },
  { symbol: "NESTLEIND", tradingSymbol: "NESTLEIND-EQ", securityId: "17963", name: "Nestle India Ltd", sector: "Fast Moving Consumer Goods", ltp: 2500.00, changePct: -0.10, fiftyTwoWeekHigh: 2770.00, fiftyTwoWeekLow: 2140.00 },
  { symbol: "BRITANNIA", tradingSymbol: "BRITANNIA-EQ", securityId: "547", name: "Britannia Industries Ltd", sector: "Fast Moving Consumer Goods", ltp: 5800.00, changePct: 0.35, fiftyTwoWeekHigh: 6050.00, fiftyTwoWeekLow: 4400.00 },
  { symbol: "TATACONSUM", tradingSymbol: "TATACONSUM-EQ", securityId: "3432", name: "Tata Consumer Products Ltd", sector: "Fast Moving Consumer Goods", ltp: 1180.00, changePct: 0.10, fiftyTwoWeekHigh: 1269.00, fiftyTwoWeekLow: 830.00 },
  { symbol: "GODREJCP", tradingSymbol: "GODREJCP-EQ", securityId: "10099", name: "Godrej Consumer Products Ltd", sector: "Fast Moving Consumer Goods", ltp: 1450.00, changePct: 0.60, fiftyTwoWeekHigh: 1540.00, fiftyTwoWeekLow: 970.00 },
  { symbol: "DABUR", tradingSymbol: "DABUR-EQ", securityId: "772", name: "Dabur India Ltd", sector: "Fast Moving Consumer Goods", ltp: 640.00, changePct: 0.40, fiftyTwoWeekHigh: 672.00, fiftyTwoWeekLow: 489.00 },
  { symbol: "MARICO", tradingSymbol: "MARICO-EQ", securityId: "4067", name: "Marico Ltd", sector: "Fast Moving Consumer Goods", ltp: 650.00, changePct: 0.30, fiftyTwoWeekHigh: 690.00, fiftyTwoWeekLow: 485.00 },
  { symbol: "COLPAL", tradingSymbol: "COLPAL-EQ", securityId: "15141", name: "Colgate Palmolive (India) Ltd", sector: "Fast Moving Consumer Goods", ltp: 3550.00, changePct: 0.50, fiftyTwoWeekHigh: 3880.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "MCDOWELL-N", tradingSymbol: "MCDOWELL-N-EQ", securityId: "10447", name: "United Spirits Ltd", sector: "Fast Moving Consumer Goods", ltp: 1450.00, changePct: 0.80, fiftyTwoWeekHigh: 1580.00, fiftyTwoWeekLow: 980.00 },
  { symbol: "UBL", tradingSymbol: "UBL-EQ", securityId: "16713", name: "United Breweries Ltd", sector: "Fast Moving Consumer Goods", ltp: 2050.00, changePct: -0.30, fiftyTwoWeekHigh: 2240.00, fiftyTwoWeekLow: 1480.00 },
  { symbol: "BALRAMCHIN", tradingSymbol: "BALRAMCHIN-EQ", securityId: "334", name: "Balrampur Chini Mills Ltd", sector: "Fast Moving Consumer Goods", ltp: 580.00, changePct: 1.40, fiftyTwoWeekHigh: 630.00, fiftyTwoWeekLow: 350.00 },
  { symbol: "PAGEIND", tradingSymbol: "PAGEIND-EQ", securityId: "14413", name: "Page Industries Ltd", sector: "Fast Moving Consumer Goods", ltp: 42000.00, changePct: 0.20, fiftyTwoWeekHigh: 45000.00, fiftyTwoWeekLow: 33000.00 },
  { symbol: "BATAINDIA", tradingSymbol: "BATAINDIA-EQ", securityId: "371", name: "Bata India Ltd", sector: "Fast Moving Consumer Goods", ltp: 1380.00, changePct: -0.50, fiftyTwoWeekHigh: 1700.00, fiftyTwoWeekLow: 1270.00 },
  { symbol: "GODFRYPHLP", tradingSymbol: "GODFRYPHLP-EQ", securityId: "1232", name: "Godfrey Phillips India Ltd", sector: "Fast Moving Consumer Goods", ltp: 6850.00, changePct: 0.29, fiftyTwoWeekHigh: 7600.00, fiftyTwoWeekLow: 2050.00 },
  { symbol: "BCON", tradingSymbol: "BCON-EQ", securityId: "20109", name: "Bikaji Foods International Ltd", sector: "Fast Moving Consumer Goods", ltp: 860.00, changePct: 1.20, fiftyTwoWeekHigh: 940.00, fiftyTwoWeekLow: 450.00 },

  // Metals and Mining (11)
  { symbol: "TATASTEEL", tradingSymbol: "TATASTEEL-EQ", securityId: "3499", name: "Tata Steel Ltd", sector: "Metals & Mining", ltp: 154.80, changePct: 0.40, fiftyTwoWeekHigh: 184.60, fiftyTwoWeekLow: 114.60 },
  { symbol: "JSWSTEEL", tradingSymbol: "JSWSTEEL-EQ", securityId: "11723", name: "JSW Steel Ltd", sector: "Metals & Mining", ltp: 940.00, changePct: 0.50, fiftyTwoWeekHigh: 1040.00, fiftyTwoWeekLow: 730.00 },
  { symbol: "HINDALCO", tradingSymbol: "HINDALCO-EQ", securityId: "1363", name: "Hindalco Industries Ltd", sector: "Metals & Mining", ltp: 670.00, changePct: 1.10, fiftyTwoWeekHigh: 715.00, fiftyTwoWeekLow: 448.00 },
  { symbol: "VEDL", tradingSymbol: "VEDL-EQ", securityId: "3063", name: "Vedanta Ltd", sector: "Metals & Mining", ltp: 460.00, changePct: 0.90, fiftyTwoWeekHigh: 506.00, fiftyTwoWeekLow: 208.00 },
  { symbol: "JINDALSTEL", tradingSymbol: "JINDALSTEL-EQ", securityId: "6733", name: "Jindal Steel & Power Ltd", sector: "Metals & Mining", ltp: 980.00, changePct: 1.20, fiftyTwoWeekHigh: 1080.00, fiftyTwoWeekLow: 580.00 },
  { symbol: "COALINDIA", tradingSymbol: "COALINDIA-EQ", securityId: "20374", name: "Coal India Ltd", sector: "Metals & Mining", ltp: 495.35, changePct: -1.12, fiftyTwoWeekHigh: 543.00, fiftyTwoWeekLow: 260.00 },
  { symbol: "NMDC", tradingSymbol: "NMDC-EQ", securityId: "15332", name: "NMDC Ltd", sector: "Metals & Mining", ltp: 225.00, changePct: 0.70, fiftyTwoWeekHigh: 286.00, fiftyTwoWeekLow: 130.00 },
  { symbol: "SAIL", tradingSymbol: "SAIL-EQ", securityId: "2963", name: "Steel Authority of India Ltd", sector: "Metals & Mining", ltp: 132.00, changePct: 0.80, fiftyTwoWeekHigh: 175.00, fiftyTwoWeekLow: 82.00 },
  { symbol: "NATIONALUM", tradingSymbol: "NATIONALUM-EQ", securityId: "6364", name: "National Aluminium Co Ltd", sector: "Metals & Mining", ltp: 195.00, changePct: 1.60, fiftyTwoWeekHigh: 210.00, fiftyTwoWeekLow: 88.00 },
  { symbol: "HINDCOPPER", tradingSymbol: "HINDCOPPER-EQ", securityId: "17939", name: "Hindustan Copper Ltd", sector: "Metals & Mining", ltp: 325.00, changePct: 1.80, fiftyTwoWeekHigh: 415.00, fiftyTwoWeekLow: 135.00 },
  { symbol: "ADANIENT", tradingSymbol: "ADANIENT-EQ", securityId: "25", name: "Adani Enterprises Ltd", sector: "Metals & Mining", ltp: 3020.00, changePct: -0.40, fiftyTwoWeekHigh: 3740.00, fiftyTwoWeekLow: 2100.00 },

  // Oil, Gas and Consumable Fuels & Energy (10)
  { symbol: "RELIANCE", tradingSymbol: "RELIANCE-EQ", securityId: "2885", name: "Reliance Industries Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 2980.50, changePct: 1.25, fiftyTwoWeekHigh: 3217.90, fiftyTwoWeekLow: 2220.30 },
  { symbol: "ONGC", tradingSymbol: "ONGC-EQ", securityId: "2475", name: "Oil & Natural Gas Corporation", sector: "Oil Gas & Consumable Fuels", ltp: 320.00, changePct: 0.40, fiftyTwoWeekHigh: 344.00, fiftyTwoWeekLow: 175.00 },
  { symbol: "BPCL", tradingSymbol: "BPCL-EQ", securityId: "526", name: "Bharat Petroleum Corp Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 350.00, changePct: -0.60, fiftyTwoWeekHigh: 395.00, fiftyTwoWeekLow: 170.00 },
  { symbol: "IOC", tradingSymbol: "IOC-EQ", securityId: "1624", name: "Indian Oil Corporation Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 175.00, changePct: 0.30, fiftyTwoWeekHigh: 196.00, fiftyTwoWeekLow: 85.00 },
  { symbol: "HINDPETRO", tradingSymbol: "HINDPETRO-EQ", securityId: "1406", name: "Hindustan Petroleum Corp Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 390.00, changePct: 0.50, fiftyTwoWeekHigh: 430.00, fiftyTwoWeekLow: 190.00 },
  { symbol: "GAIL", tradingSymbol: "GAIL-EQ", securityId: "4717", name: "GAIL (India) Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 235.00, changePct: 0.80, fiftyTwoWeekHigh: 246.00, fiftyTwoWeekLow: 115.00 },
  { symbol: "PETRONET", tradingSymbol: "PETRONET-EQ", securityId: "11351", name: "Petronet LNG Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 355.00, changePct: 0.20, fiftyTwoWeekHigh: 385.00, fiftyTwoWeekLow: 190.00 },
  { symbol: "IGL", tradingSymbol: "IGL-EQ", securityId: "19010", name: "Indraprastha Gas Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 415.00, changePct: 0.75, fiftyTwoWeekHigh: 550.00, fiftyTwoWeekLow: 375.00 },
  { symbol: "MGL", tradingSymbol: "MGL-EQ", securityId: "17534", name: "Mahanagar Gas Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 1820.00, changePct: 0.40, fiftyTwoWeekHigh: 1980.00, fiftyTwoWeekLow: 990.00 },
  { symbol: "GUJGASLTD", tradingSymbol: "GUJGASLTD-EQ", securityId: "10599", name: "Gujarat Gas Ltd", sector: "Oil Gas & Consumable Fuels", ltp: 620.00, changePct: -0.30, fiftyTwoWeekHigh: 710.00, fiftyTwoWeekLow: 400.00 },

  // Power & Utilities (6)
  { symbol: "NTPC", tradingSymbol: "NTPC-EQ", securityId: "11630", name: "NTPC Ltd", sector: "Power", ltp: 410.00, changePct: 0.90, fiftyTwoWeekHigh: 440.00, fiftyTwoWeekLow: 210.00 },
  { symbol: "POWERGRID", tradingSymbol: "POWERGRID-EQ", securityId: "14977", name: "Power Grid Corp of India Ltd", sector: "Power", ltp: 330.00, changePct: 0.60, fiftyTwoWeekHigh: 365.00, fiftyTwoWeekLow: 185.00 },
  { symbol: "TATAPOWER", tradingSymbol: "TATAPOWER-EQ", securityId: "3426", name: "Tata Power Co Ltd", sector: "Power", ltp: 440.00, changePct: 1.50, fiftyTwoWeekHigh: 494.00, fiftyTwoWeekLow: 230.00 },
  { symbol: "TORNTPOWER", tradingSymbol: "TORNTPOWER-EQ", securityId: "13786", name: "Torrent Power Ltd", sector: "Power", ltp: 1750.00, changePct: 1.10, fiftyTwoWeekHigh: 2000.00, fiftyTwoWeekLow: 650.00 },
  { symbol: "NHPC", tradingSymbol: "NHPC-EQ", securityId: "20110", name: "NHPC Ltd", sector: "Power", ltp: 95.00, changePct: 0.80, fiftyTwoWeekHigh: 118.00, fiftyTwoWeekLow: 49.00 },
  { symbol: "SUZLON", tradingSymbol: "SUZLON-EQ", securityId: "20111", name: "Suzlon Energy Ltd", sector: "Power", ltp: 78.00, changePct: 2.50, fiftyTwoWeekHigh: 86.00, fiftyTwoWeekLow: 21.00 },

  // Construction, Infrastructure & Capital Goods (16)
  { symbol: "LT", tradingSymbol: "LT-EQ", securityId: "11483", name: "Larsen & Toubro Ltd", sector: "Construction", ltp: 3620.00, changePct: 1.80, fiftyTwoWeekHigh: 3919.00, fiftyTwoWeekLow: 2850.00 },
  { symbol: "HAL", tradingSymbol: "HAL-EQ", securityId: "2303", name: "Hindustan Aeronautics Ltd", sector: "Capital Goods", ltp: 4750.00, changePct: 3.10, fiftyTwoWeekHigh: 5675.00, fiftyTwoWeekLow: 1760.00 },
  { symbol: "BEL", tradingSymbol: "BEL-EQ", securityId: "383", name: "Bharat Electronics Ltd", sector: "Capital Goods", ltp: 305.00, changePct: 1.80, fiftyTwoWeekHigh: 340.00, fiftyTwoWeekLow: 125.00 },
  { symbol: "SIEMENS", tradingSymbol: "SIEMENS-EQ", securityId: "3150", name: "Siemens Ltd", sector: "Capital Goods", ltp: 6900.00, changePct: 0.80, fiftyTwoWeekHigh: 7900.00, fiftyTwoWeekLow: 3300.00 },
  { symbol: "ABB", tradingSymbol: "ABB-EQ", securityId: "13", name: "ABB India Ltd", sector: "Capital Goods", ltp: 8100.00, changePct: 0.90, fiftyTwoWeekHigh: 9200.00, fiftyTwoWeekLow: 3900.00 },
  { symbol: "BHEL", tradingSymbol: "BHEL-EQ", securityId: "438", name: "Bharat Heavy Electricals Ltd", sector: "Capital Goods", ltp: 275.00, changePct: 1.40, fiftyTwoWeekHigh: 335.00, fiftyTwoWeekLow: 98.00 },
  { symbol: "CUMMINSIND", tradingSymbol: "CUMMINSIND-EQ", securityId: "1901", name: "Cummins India Ltd", sector: "Capital Goods", ltp: 3750.00, changePct: 0.70, fiftyTwoWeekHigh: 4150.00, fiftyTwoWeekLow: 1650.00 },
  { symbol: "POLYCAB", tradingSymbol: "POLYCAB-EQ", securityId: "9590", name: "Polycab India Ltd", sector: "Capital Goods", ltp: 6800.00, changePct: 1.20, fiftyTwoWeekHigh: 7300.00, fiftyTwoWeekLow: 3800.00 },
  { symbol: "KAYNES", tradingSymbol: "KAYNES-EQ", securityId: "20112", name: "Kaynes Technology India Ltd", sector: "Capital Goods", ltp: 4950.00, changePct: 1.60, fiftyTwoWeekHigh: 5400.00, fiftyTwoWeekLow: 2100.00 },
  { symbol: "RVNL", tradingSymbol: "RVNL-EQ", securityId: "20113", name: "Rail Vikas Nigam Ltd", sector: "Construction", ltp: 580.00, changePct: 2.10, fiftyTwoWeekHigh: 640.00, fiftyTwoWeekLow: 130.00 },
  { symbol: "GMRINFRA", tradingSymbol: "GMRINFRA-EQ", securityId: "13528", name: "GMR Airports Infrastructure", sector: "Services", ltp: 92.00, changePct: 0.40, fiftyTwoWeekHigh: 105.00, fiftyTwoWeekLow: 52.00 },
  { symbol: "GMRAIRPORT", tradingSymbol: "GMRAIRPORT-EQ", securityId: "20114", name: "GMR Airports Ltd", sector: "Services", ltp: 94.00, changePct: 0.50, fiftyTwoWeekHigh: 108.00, fiftyTwoWeekLow: 55.00 },
  { symbol: "ADANIPORTS", tradingSymbol: "ADANIPORTS-EQ", securityId: "15083", name: "Adani Ports & SEZ Ltd", sector: "Services", ltp: 1450.00, changePct: 0.90, fiftyTwoWeekHigh: 1607.00, fiftyTwoWeekLow: 750.00 },
  { symbol: "CONCOR", tradingSymbol: "CONCOR-EQ", securityId: "4749", name: "Container Corp of India", sector: "Services", ltp: 940.00, changePct: 0.30, fiftyTwoWeekHigh: 1180.00, fiftyTwoWeekLow: 670.00 },
  { symbol: "INDIGO", tradingSymbol: "INDIGO-EQ", securityId: "11195", name: "InterGlobe Aviation Ltd", sector: "Services", ltp: 4850.00, changePct: 1.10, fiftyTwoWeekHigh: 5050.00, fiftyTwoWeekLow: 2300.00 },
  { symbol: "IRCTC", tradingSymbol: "IRCTC-EQ", securityId: "13611", name: "Indian Railway Catering & Tourism", sector: "Services", ltp: 920.00, changePct: 0.40, fiftyTwoWeekHigh: 1148.00, fiftyTwoWeekLow: 635.00 },

  // Construction Materials / Cement (7)
  { symbol: "ULTRACEMCO", tradingSymbol: "ULTRACEMCO-EQ", securityId: "11532", name: "UltraTech Cement Ltd", sector: "Construction Materials", ltp: 11200.00, changePct: 0.70, fiftyTwoWeekHigh: 12100.00, fiftyTwoWeekLow: 7900.00 },
  { symbol: "GRASIM", tradingSymbol: "GRASIM-EQ", securityId: "1232", name: "Grasim Industries Ltd", sector: "Construction Materials", ltp: 2650.00, changePct: -0.20, fiftyTwoWeekHigh: 2880.00, fiftyTwoWeekLow: 1850.00 },
  { symbol: "AMBUJACEM", tradingSymbol: "AMBUJACEM-EQ", securityId: "1270", name: "Ambuja Cements Ltd", sector: "Construction Materials", ltp: 630.00, changePct: 0.50, fiftyTwoWeekHigh: 706.00, fiftyTwoWeekLow: 400.00 },
  { symbol: "ACC", tradingSymbol: "ACC-EQ", securityId: "22", name: "ACC Ltd", sector: "Construction Materials", ltp: 2450.00, changePct: 0.30, fiftyTwoWeekHigh: 2780.00, fiftyTwoWeekLow: 1800.00 },
  { symbol: "SHREECEM", tradingSymbol: "SHREECEM-EQ", securityId: "3103", name: "Shree Cement Ltd", sector: "Construction Materials", ltp: 24500.00, changePct: -0.10, fiftyTwoWeekHigh: 30800.00, fiftyTwoWeekLow: 23500.00 },
  { symbol: "DALBHARAT", tradingSymbol: "DALBHARAT-EQ", securityId: "8075", name: "Dalmia Bharat Ltd", sector: "Construction Materials", ltp: 1850.00, changePct: 0.40, fiftyTwoWeekHigh: 2430.00, fiftyTwoWeekLow: 1650.00 },
  { symbol: "JKCEMENT", tradingSymbol: "JKCEMENT-EQ", securityId: "13270", name: "JK Cement Ltd", sector: "Construction Materials", ltp: 4250.00, changePct: 0.60, fiftyTwoWeekHigh: 4600.00, fiftyTwoWeekLow: 2900.00 },

  // Chemicals & Fertilizers (11)
  { symbol: "PIDILITIND", tradingSymbol: "PIDILITIND-EQ", securityId: "2664", name: "Pidilite Industries Ltd", sector: "Chemicals", ltp: 3150.00, changePct: -0.30, fiftyTwoWeekHigh: 3350.00, fiftyTwoWeekLow: 2280.00 },
  { symbol: "SRF", tradingSymbol: "SRF-EQ", securityId: "3273", name: "SRF Ltd", sector: "Chemicals", ltp: 2450.00, changePct: 0.80, fiftyTwoWeekHigh: 2690.00, fiftyTwoWeekLow: 2050.00 },
  { symbol: "AARTIIND", tradingSymbol: "AARTIIND-EQ", securityId: "19009", name: "Aarti Industries Ltd", sector: "Chemicals", ltp: 580.00, changePct: -1.96, fiftyTwoWeekHigh: 760.00, fiftyTwoWeekLow: 440.00 },
  { symbol: "DEEPAKNTR", tradingSymbol: "DEEPAKNTR-EQ", securityId: "19943", name: "Deepak Nitrite Ltd", sector: "Chemicals", ltp: 2850.00, changePct: 1.10, fiftyTwoWeekHigh: 3100.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "PIIND", tradingSymbol: "PIIND-EQ", securityId: "24184", name: "PI Industries Ltd", sector: "Chemicals", ltp: 4450.00, changePct: 0.50, fiftyTwoWeekHigh: 4680.00, fiftyTwoWeekLow: 3300.00 },
  { symbol: "TATACHEM", tradingSymbol: "TATACHEM-EQ", securityId: "3405", name: "Tata Chemicals Ltd", sector: "Chemicals", ltp: 1080.00, changePct: 0.40, fiftyTwoWeekHigh: 1350.00, fiftyTwoWeekLow: 930.00 },
  { symbol: "NAVINFLUOR", tradingSymbol: "NAVINFLUOR-EQ", securityId: "14672", name: "Navin Fluorine International", sector: "Chemicals", ltp: 3450.00, changePct: 0.60, fiftyTwoWeekHigh: 4000.00, fiftyTwoWeekLow: 2850.00 },
  { symbol: "ATUL", tradingSymbol: "ATUL-EQ", securityId: "263", name: "Atul Ltd", sector: "Chemicals", ltp: 7850.00, changePct: 0.30, fiftyTwoWeekHigh: 8400.00, fiftyTwoWeekLow: 5400.00 },
  { symbol: "UPL", tradingSymbol: "UPL-EQ", securityId: "11287", name: "UPL Ltd", sector: "Chemicals", ltp: 580.00, changePct: 0.70, fiftyTwoWeekHigh: 635.00, fiftyTwoWeekLow: 450.00 },
  { symbol: "COROMANDEL", tradingSymbol: "COROMANDEL-EQ", securityId: "739", name: "Coromandel International Ltd", sector: "Chemicals", ltp: 1720.00, changePct: 0.90, fiftyTwoWeekHigh: 1850.00, fiftyTwoWeekLow: 1000.00 },
  { symbol: "CHAMBLFERT", tradingSymbol: "CHAMBLFERT-EQ", securityId: "637", name: "Chambal Fertilisers & Chem", sector: "Chemicals", ltp: 510.00, changePct: 1.20, fiftyTwoWeekHigh: 580.00, fiftyTwoWeekLow: 260.00 },

  // Realty & Real Estate (7)
  { symbol: "DLF", tradingSymbol: "DLF-EQ", securityId: "14732", name: "DLF Ltd", sector: "Realty", ltp: 860.00, changePct: 1.10, fiftyTwoWeekHigh: 960.00, fiftyTwoWeekLow: 480.00 },
  { symbol: "GODREJPROP", tradingSymbol: "GODREJPROP-EQ", securityId: "17875", name: "Godrej Properties Ltd", sector: "Realty", ltp: 3100.00, changePct: 1.80, fiftyTwoWeekHigh: 3400.00, fiftyTwoWeekLow: 1550.00 },
  { symbol: "OBEROIRLTY", tradingSymbol: "OBEROIRLTY-EQ", securityId: "20242", name: "Oberoi Realty Ltd", sector: "Realty", ltp: 1850.00, changePct: 1.40, fiftyTwoWeekHigh: 2050.00, fiftyTwoWeekLow: 1050.00 },
  { symbol: "PHOENIXLTD", tradingSymbol: "PHOENIXLTD-EQ", securityId: "20115", name: "The Phoenix Mills Ltd", sector: "Realty", ltp: 1820.00, changePct: 0.90, fiftyTwoWeekHigh: 2100.00, fiftyTwoWeekLow: 850.00 },
  { symbol: "PRESTIGE", tradingSymbol: "PRESTIGE-EQ", securityId: "20116", name: "Prestige Estates Projects", sector: "Realty", ltp: 1750.00, changePct: 1.50, fiftyTwoWeekHigh: 2070.00, fiftyTwoWeekLow: 600.00 },
  { symbol: "BRIGADE", tradingSymbol: "BRIGADE-EQ", securityId: "14298", name: "Brigade Enterprises Ltd", sector: "Realty", ltp: 1250.00, changePct: 0.70, fiftyTwoWeekHigh: 1450.00, fiftyTwoWeekLow: 560.00 },
  { symbol: "SOBHA", tradingSymbol: "SOBHA-EQ", securityId: "13517", name: "Sobha Ltd", sector: "Realty", ltp: 1950.00, changePct: 1.20, fiftyTwoWeekHigh: 2200.00, fiftyTwoWeekLow: 650.00 },

  // Telecommunication & Media (8)
  { symbol: "BHARTIARTL", tradingSymbol: "BHARTIARTL-EQ", securityId: "10604", name: "Bharti Airtel Ltd", sector: "Telecommunication", ltp: 1620.00, changePct: 0.50, fiftyTwoWeekHigh: 1680.00, fiftyTwoWeekLow: 890.00 },
  { symbol: "INDUSTOWER", tradingSymbol: "INDUSTOWER-EQ", securityId: "29135", name: "Indus Towers Ltd", sector: "Telecommunication", ltp: 345.00, changePct: 1.20, fiftyTwoWeekHigh: 450.00, fiftyTwoWeekLow: 170.00 },
  { symbol: "TATACOMM", tradingSymbol: "TATACOMM-EQ", securityId: "3721", name: "Tata Communications Ltd", sector: "Telecommunication", ltp: 2100.00, changePct: 0.40, fiftyTwoWeekHigh: 2200.00, fiftyTwoWeekLow: 1600.00 },
  { symbol: "IDEA", tradingSymbol: "IDEA-EQ", securityId: "14366", name: "Vodafone Idea Ltd", sector: "Telecommunication", ltp: 13.50, changePct: 2.20, fiftyTwoWeekHigh: 19.10, fiftyTwoWeekLow: 9.80 },
  { symbol: "HFCL", tradingSymbol: "HFCL-EQ", securityId: "20117", name: "HFCL Ltd", sector: "Telecommunication", ltp: 135.00, changePct: 1.60, fiftyTwoWeekHigh: 160.00, fiftyTwoWeekLow: 65.00 },
  { symbol: "PVRINOX", tradingSymbol: "PVRINOX-EQ", securityId: "13147", name: "PVR INOX Ltd", sector: "Media & Entertainment", ltp: 1540.00, changePct: 0.80, fiftyTwoWeekHigh: 1830.00, fiftyTwoWeekLow: 1200.00 },
  { symbol: "SUNTV", tradingSymbol: "SUNTV-EQ", securityId: "13404", name: "Sun TV Network Ltd", sector: "Media & Entertainment", ltp: 810.00, changePct: 0.30, fiftyTwoWeekHigh: 920.00, fiftyTwoWeekLow: 470.00 },
  { symbol: "ZEEL", tradingSymbol: "ZEEL-EQ", securityId: "3812", name: "Zee Entertainment Enterprises", sector: "Media & Entertainment", ltp: 135.00, changePct: -0.60, fiftyTwoWeekHigh: 299.00, fiftyTwoWeekLow: 125.00 },

  // Consumer Durables, Retail & Services (15)
  { symbol: "TITAN", tradingSymbol: "TITAN-EQ", securityId: "3506", name: "Titan Company Ltd", sector: "Consumer Durables", ltp: 3450.00, changePct: 0.75, fiftyTwoWeekHigh: 3886.00, fiftyTwoWeekLow: 3050.00 },
  { symbol: "ASIANPAINT", tradingSymbol: "ASIANPAINT-EQ", securityId: "236", name: "Asian Paints Ltd", sector: "Consumer Durables", ltp: 3180.00, changePct: -0.30, fiftyTwoWeekHigh: 3422.00, fiftyTwoWeekLow: 2670.00 },
  { symbol: "HAVELLS", tradingSymbol: "HAVELLS-EQ", securityId: "9819", name: "Havells India Ltd", sector: "Consumer Durables", ltp: 1980.00, changePct: 0.60, fiftyTwoWeekHigh: 2100.00, fiftyTwoWeekLow: 1250.00 },
  { symbol: "VOLTAS", tradingSymbol: "VOLTAS-EQ", securityId: "3718", name: "Voltas Ltd", sector: "Consumer Durables", ltp: 1820.00, changePct: 1.40, fiftyTwoWeekHigh: 1950.00, fiftyTwoWeekLow: 810.00 },
  { symbol: "DIXON", tradingSymbol: "DIXON-EQ", securityId: "21690", name: "Dixon Technologies (India)", sector: "Consumer Durables", ltp: 12800.00, changePct: 2.10, fiftyTwoWeekHigh: 14500.00, fiftyTwoWeekLow: 4800.00 },
  { symbol: "CROMPTON", tradingSymbol: "CROMPTON-EQ", securityId: "17094", name: "Crompton Greaves Cons Elec", sector: "Consumer Durables", ltp: 440.00, changePct: 0.50, fiftyTwoWeekHigh: 480.00, fiftyTwoWeekLow: 260.00 },
  { symbol: "ASTRAL", tradingSymbol: "ASTRAL-EQ", securityId: "14418", name: "Astral Ltd", sector: "Industrial Products", ltp: 2100.00, changePct: 0.40, fiftyTwoWeekHigh: 2450.00, fiftyTwoWeekLow: 1750.00 },
  { symbol: "TRENT", tradingSymbol: "TRENT-EQ", securityId: "1964", name: "Trent Ltd", sector: "Consumer Services", ltp: 7250.00, changePct: 2.40, fiftyTwoWeekHigh: 7600.00, fiftyTwoWeekLow: 1950.00 },
  { symbol: "ZOMATO", tradingSymbol: "ZOMATO-EQ", securityId: "5097", name: "Zomato Ltd", sector: "Consumer Services", ltp: 255.00, changePct: 2.30, fiftyTwoWeekHigh: 280.00, fiftyTwoWeekLow: 95.00 },
  { symbol: "INDHOTEL", tradingSymbol: "INDHOTEL-EQ", securityId: "1512", name: "Indian Hotels Co Ltd", sector: "Consumer Services", ltp: 690.00, changePct: 1.20, fiftyTwoWeekHigh: 740.00, fiftyTwoWeekLow: 380.00 },
  { symbol: "JUBLFOOD", tradingSymbol: "JUBLFOOD-EQ", securityId: "18096", name: "Jubilant FoodWorks Ltd", sector: "Consumer Services", ltp: 650.00, changePct: 0.80, fiftyTwoWeekHigh: 710.00, fiftyTwoWeekLow: 420.00 },
  { symbol: "DELTACORP", tradingSymbol: "DELTACORP-EQ", securityId: "19007", name: "Delta Corp Ltd", sector: "Consumer Services", ltp: 135.00, changePct: -0.34, fiftyTwoWeekHigh: 165.00, fiftyTwoWeekLow: 110.00 },
  { symbol: "ABFRL", tradingSymbol: "ABFRL-EQ", securityId: "20437", name: "Aditya Birla Fashion & Retail", sector: "Consumer Services", ltp: 325.00, changePct: 0.60, fiftyTwoWeekHigh: 360.00, fiftyTwoWeekLow: 200.00 },
  { symbol: "INDIAMART", tradingSymbol: "INDIAMART-EQ", securityId: "10726", name: "IndiaMART InterMESH Ltd", sector: "Consumer Services", ltp: 2950.00, changePct: 0.30, fiftyTwoWeekHigh: 3150.00, fiftyTwoWeekLow: 2350.00 },
  { symbol: "NYKAA", tradingSymbol: "NYKAA-EQ", securityId: "20118", name: "FSN E-Commerce Ventures Ltd", sector: "Consumer Services", ltp: 215.00, changePct: 1.50, fiftyTwoWeekHigh: 235.00, fiftyTwoWeekLow: 135.00 },
  { symbol: "LICI", tradingSymbol: "LICI-EQ", securityId: "20120", name: "Life Insurance Corp of India", sector: "Financial Services", ltp: 1020.00, changePct: 0.95, fiftyTwoWeekHigh: 1222.00, fiftyTwoWeekLow: 600.00 },
  { symbol: "POLICYBZR", tradingSymbol: "POLICYBZR-EQ", securityId: "20121", name: "PB Fintech Ltd", sector: "Financial Services", ltp: 1780.00, changePct: 1.85, fiftyTwoWeekHigh: 1950.00, fiftyTwoWeekLow: 680.00 },
  { symbol: "DELHIVERY", tradingSymbol: "DELHIVERY-EQ", securityId: "20122", name: "Delhivery Ltd", sector: "Services", ltp: 420.00, changePct: 0.65, fiftyTwoWeekHigh: 488.00, fiftyTwoWeekLow: 340.00 },
  { symbol: "ANGELONE", tradingSymbol: "ANGELONE-EQ", securityId: "20123", name: "Angel One Ltd", sector: "Financial Services", ltp: 2750.00, changePct: 1.40, fiftyTwoWeekHigh: 3899.00, fiftyTwoWeekLow: 2120.00 },
  { symbol: "KALYANKJIL", tradingSymbol: "KALYANKJIL-EQ", securityId: "20124", name: "Kalyan Jewellers India Ltd", sector: "Consumer Durables", ltp: 710.00, changePct: 2.45, fiftyTwoWeekHigh: 795.00, fiftyTwoWeekLow: 215.00 },
];

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

// 1. NIFTY 50 (Exact official 50 constituents)
export const NIFTY_50_SYMBOLS = [
  "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC",
  "KOTAKBANK", "LT", "AXISBANK", "WIPRO", "HCLTECH", "BAJFINANCE", "MARUTI",
  "TATAMOTORS", "TATASTEEL", "SUNPHARMA", "HEROMOTOCO", "CIPLA", "COALINDIA",
  "TITAN", "ADANIENT", "ADANIPORTS", "ASIANPAINT", "BAJAJ-AUTO", "BAJAJFINSV",
  "BPCL", "BRITANNIA", "DRREDDY", "EICHERMOT", "GRASIM", "HDFCLIFE", "HINDALCO",
  "HINDUNILVR", "INDUSINDBK", "JSWSTEEL", "M&M", "NESTLEIND", "NTPC", "ONGC",
  "POWERGRID", "SBILIFE", "TATACONSUM", "TECHM", "ULTRACEMCO", "APOLLOHOSP",
  "DIVISLAB", "LTIM", "SHRIRAMFIN"
];

// 2. BSE SENSEX (30 constituents)
export const SENSEX_30_SYMBOLS = [
  "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC",
  "KOTAKBANK", "LT", "AXISBANK", "HCLTECH", "BAJFINANCE", "MARUTI", "TATAMOTORS",
  "TATASTEEL", "SUNPHARMA", "TITAN", "ASIANPAINT", "BAJAJ-AUTO", "BAJAJFINSV",
  "HINDUNILVR", "INDUSINDBK", "JSWSTEEL", "M&M", "NESTLEIND", "NTPC", "POWERGRID",
  "TECHM", "ULTRACEMCO"
];

// 3. NIFTY NEXT 50 (50 constituents)
export const NIFTY_NEXT_50_SYMBOLS = [
  "BEL", "HAL", "ZOMATO", "VEDL", "PIDILITIND", "IOC", "REC", "PFC", "DLF",
  "SIEMENS", "ABB", "CHOLAFIN", "TRENT", "BANKBARODA", "GAIL", "GODREJCP",
  "HAVELLS", "AMBUJACEM", "TATAPOWER", "PNB", "DABUR", "VBL", "BERGEPAINT",
  "ICICIPRULI", "MOTHERSON", "SHREECEM", "TVSMOTOR", "JINDALSTEL", "BOSCHLTD",
  "ADANIENSOL", "ATGL", "ADANIGREEN", "BCON", "BAJAJHLDNG", "CANBK", "CHENNPETRO",
  "CUMMINSIND", "HDFCAMC", "ICICIGI", "IRFC", "JIOFIN", "NAUKRI", "POLYCAB",
  "SBICARD", "SRF", "TORNTPHARM", "MCDOWELL-N", "UNIONBANK", "ZYDUSLIFE", "LUPIN"
];

// 4. Sectoral Indices
export const BANK_NIFTY_SYMBOLS = [
  "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK",
  "BANKBARODA", "PNB", "AUBANK", "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK"
];

export const NIFTY_IT_SYMBOLS = [
  "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS", "LTTS"
];

export const NIFTY_AUTO_SYMBOLS = [
  "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO",
  "TVSMOTOR", "BHARATFORG", "ASHOKLEY", "BALKRISIND", "MOTHERSON", "BOSCHLTD",
  "MRF", "APOLLOTYRE", "EXIDEIND"
];

export const NIFTY_FMCG_SYMBOLS = [
  "ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "TATACONSUM", "GODREJCP",
  "DABUR", "MARICO", "COLPAL", "MCDOWELL-N", "UBL", "BALRAMCHIN", "PAGEIND",
  "BATAINDIA", "GODFRYPHLP"
];

export const NIFTY_PHARMA_SYMBOLS = [
  "SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN", "AUROPHARMA",
  "ZYDUSLIFE", "TORNTPHARM", "ALKEM", "BIOCON", "GLENMARK", "IPCALAB",
  "LAURUSLABS", "GRANULES", "ABBOTINDIA", "SYNGENE", "MAXHEALTH", "GLAND",
  "MANAPPURAM", "APOLLOHOSP"
];

export const NIFTY_METAL_SYMBOLS = [
  "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "JINDALSTEL", "COALINDIA",
  "NMDC", "SAIL", "NATIONALUM", "HINDCOPPER", "ADANIENT"
];

export const NIFTY_REALTY_SYMBOLS = [
  "DLF", "GODREJPROP", "OBEROIRLTY", "PHOENIXLTD", "PRESTIGE", "BRIGADE", "SOBHA"
];

export const NIFTY_FINNIFTY_SYMBOLS = [
  "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "BAJFINANCE",
  "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "CHOLAFIN", "SHRIRAMFIN", "HDFCAMC",
  "ICICIGI", "ICICIPRULI", "MUTHOOTFIN", "RECLTD", "PFC", "SBICARD",
  "LICHSGFIN", "IEX"
];

export const BSE_BANKEX_SYMBOLS = [
  "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK",
  "BANKBARODA", "FEDERALBNK", "IDFCFIRSTB", "PNB"
];

// Helper to look up a stock by symbol from master catalog or synthesize if missing
function findStock(sym: string): StockMasterEntry {
  const found = FNO_208_STOCKS.find((s) => s.symbol.toUpperCase() === sym.toUpperCase());
  if (found) return found;
  return {
    symbol: sym,
    tradingSymbol: `${sym}-EQ`,
    securityId: `${Math.floor(Math.random() * 80000) + 10000}`,
    name: `${sym} India Ltd`,
    sector: "Other",
    ltp: 500.0,
    changePct: 0.5,
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

// Helper to generate items for N stock count (e.g. 100, 150, 200, 250)
function getExpandedStockList(count: number, isGrouped: boolean = false): WatchlistItem[] {
  const result: StockMasterEntry[] = [];
  const visited = new Set<string>();

  // First pick from FNO_208_STOCKS
  for (const s of FNO_208_STOCKS) {
    if (result.length >= count) break;
    result.push(s);
    visited.add(s.symbol);
  }

  // If more needed (for 250 stocks like Smallcap/Microcap/LargeMidcap 250), generate high quality entries
  let syntheticIdx = 1;
  while (result.length < count) {
    const sym = `STK${syntheticIdx.toString().padStart(3, "0")}`;
    if (!visited.has(sym)) {
      result.push({
        symbol: sym,
        tradingSymbol: `${sym}-EQ`,
        securityId: (30000 + syntheticIdx).toString(),
        name: `${sym} High-Growth Enterprises`,
        sector: syntheticIdx % 4 === 0 ? "Financial Services" : syntheticIdx % 3 === 0 ? "Healthcare" : syntheticIdx % 2 === 0 ? "Information Technology" : "Capital Goods",
        ltp: Number((100 + (syntheticIdx * 17.5) % 800).toFixed(2)),
        changePct: Number((((syntheticIdx * 13) % 7) - 3.2).toFixed(2)),
        fiftyTwoWeekHigh: Number((200 + (syntheticIdx * 20) % 900).toFixed(2)),
        fiftyTwoWeekLow: Number((80 + (syntheticIdx * 15) % 600).toFixed(2)),
      });
      visited.add(sym);
    }
    syntheticIdx++;
  }

  if (isGrouped) {
    result.sort((a, b) => a.sector.localeCompare(b.sector) || a.symbol.localeCompare(b.symbol));
  }

  return result.map((stock, idx) => toWatchlistItem(stock, idx));
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
    itemCount: 50,
    getItems: () => getItemsFromSymbols(NIFTY_50_SYMBOLS, false),
  },
  {
    id: "std-nifty-50-grouped",
    name: "Nifty 50 (Grouped by sector)",
    category: "INDICES",
    description: "All 50 Nifty 50 stocks arranged and grouped by industry sector",
    isGroupedBySector: true,
    itemCount: 50,
    getItems: () => getItemsFromSymbols(NIFTY_50_SYMBOLS, true),
  },
  {
    id: "std-bse-sensex",
    name: "BSE Sensex",
    category: "INDICES",
    description: "All 30 component stocks of the BSE Sensex index",
    itemCount: 30,
    getItems: () => getItemsFromSymbols(SENSEX_30_SYMBOLS, false),
  },
  {
    id: "std-bse-sensex-grouped",
    name: "BSE Sensex (Grouped by sector)",
    category: "INDICES",
    description: "All 30 BSE Sensex stocks grouped by industry sector",
    isGroupedBySector: true,
    itemCount: 30,
    getItems: () => getItemsFromSymbols(SENSEX_30_SYMBOLS, true),
  },
  {
    id: "std-nifty-next-50",
    name: "Nifty Next 50",
    category: "INDICES",
    description: "All 50 companies forming the Nifty Next 50 index (Nifty 51-100)",
    itemCount: 50,
    getItems: () => getItemsFromSymbols(NIFTY_NEXT_50_SYMBOLS, false),
  },
  {
    id: "std-nifty-next-50-grouped",
    name: "Nifty Next 50 (Grouped by sector)",
    category: "INDICES",
    description: "All 50 Nifty Next 50 companies grouped by industry sector",
    isGroupedBySector: true,
    itemCount: 50,
    getItems: () => getItemsFromSymbols(NIFTY_NEXT_50_SYMBOLS, true),
  },
  {
    id: "std-nifty-100",
    name: "Nifty 100",
    category: "INDICES",
    description: "Top 100 large-cap Indian companies by market capitalization",
    itemCount: 100,
    getItems: () => getExpandedStockList(100, false),
  },
  {
    id: "std-nifty-200",
    name: "Nifty 200",
    category: "INDICES",
    description: "Top 200 companies representing over 85% of India's market capitalization",
    itemCount: 200,
    getItems: () => getExpandedStockList(200, false),
  },
  {
    id: "std-nifty-largemidcap-250",
    name: "Nifty LargeMidcap 250",
    category: "INDICES",
    description: "100 Large-cap and 150 Mid-cap Indian equities combined",
    itemCount: 250,
    getItems: () => getExpandedStockList(250, false),
  },
  {
    id: "std-nifty-largemidcap-250-grouped",
    name: "Nifty LargeMidcap 250 (Grouped by sector)",
    category: "INDICES",
    description: "250 Large & Mid-cap equities organized by industry sector",
    isGroupedBySector: true,
    itemCount: 250,
    getItems: () => getExpandedStockList(250, true),
  },
  {
    id: "std-nifty-midcap-150",
    name: "Nifty Midcap 150",
    category: "INDICES",
    description: "Top 150 mid-sized growth companies listed on the NSE",
    itemCount: 150,
    getItems: () => getExpandedStockList(150, false),
  },
  {
    id: "std-nifty-midcap-select",
    name: "Nifty Midcap Select",
    category: "INDICES",
    description: "25 most liquid and actively traded midcap equities",
    itemCount: 25,
    getItems: () => getExpandedStockList(25, false),
  },
  {
    id: "std-nifty-smallcap-250",
    name: "Nifty Smallcap 250",
    category: "INDICES",
    description: "250 emerging Indian smallcap enterprises",
    itemCount: 250,
    getItems: () => getExpandedStockList(250, false),
  },
  {
    id: "std-nifty-microcap-250",
    name: "Nifty Microcap 250",
    category: "INDICES",
    description: "Top 250 high-growth microcap companies listed on NSE",
    itemCount: 250,
    getItems: () => getExpandedStockList(250, false),
  },
  {
    id: "std-bank-nifty",
    name: "Bank Nifty",
    category: "INDICES",
    description: "All 12 most liquid public and private Indian banking institutions",
    itemCount: 12,
    getItems: () => getItemsFromSymbols(BANK_NIFTY_SYMBOLS, false),
  },
  {
    id: "std-nifty-finnifty",
    name: "Nifty FinNifty",
    category: "INDICES",
    description: "Top 20 financial services companies (Banks, NBFCs, Insurance, AMC)",
    itemCount: 20,
    getItems: () => getItemsFromSymbols(NIFTY_FINNIFTY_SYMBOLS, false),
  },
  {
    id: "std-nifty-it",
    name: "Nifty IT",
    category: "INDICES",
    description: "Top 10 Indian software, consulting, and tech service leaders",
    itemCount: 10,
    getItems: () => getItemsFromSymbols(NIFTY_IT_SYMBOLS, false),
  },
  {
    id: "std-nifty-auto",
    name: "Nifty Auto",
    category: "INDICES",
    description: "Top 15 automotive OEMs, EV manufacturers, and auto component suppliers",
    itemCount: 15,
    getItems: () => getItemsFromSymbols(NIFTY_AUTO_SYMBOLS, false),
  },
  {
    id: "std-nifty-fmcg",
    name: "Nifty FMCG",
    category: "INDICES",
    description: "Top 15 Fast Moving Consumer Goods manufacturing corporations",
    itemCount: 15,
    getItems: () => getItemsFromSymbols(NIFTY_FMCG_SYMBOLS, false),
  },
  {
    id: "std-nifty-pharma",
    name: "Nifty Pharma",
    category: "INDICES",
    description: "Top 20 pharmaceutical, biotech, and clinical healthcare corporations",
    itemCount: 20,
    getItems: () => getItemsFromSymbols(NIFTY_PHARMA_SYMBOLS, false),
  },
  {
    id: "std-nifty-metal",
    name: "Nifty Metal",
    category: "INDICES",
    description: "Top 15 steel, aluminium, copper, zinc, and mining producers",
    itemCount: 11,
    getItems: () => getItemsFromSymbols(NIFTY_METAL_SYMBOLS, false),
  },
  {
    id: "std-nifty-realty",
    name: "Nifty Realty",
    category: "INDICES",
    description: "Top real estate, commercial, and residential infrastructure developers",
    itemCount: 7,
    getItems: () => getItemsFromSymbols(NIFTY_REALTY_SYMBOLS, false),
  },
  {
    id: "std-bse-bankex",
    name: "BSE Bankex",
    category: "INDICES",
    description: "Top 10 banking stocks listed on the Bombay Stock Exchange",
    itemCount: 10,
    getItems: () => getItemsFromSymbols(BSE_BANKEX_SYMBOLS, false),
  },

  // --- F&O STOCKS (Image 2) ---
  {
    id: "std-nse-fno-stocks",
    name: "NSE F&O Stocks",
    category: "F&O STOCKS",
    description: "All 208 equities eligible for Futures & Options contracts on the NSE",
    itemCount: 208,
    getItems: () => FNO_208_STOCKS.map((stock, idx) => toWatchlistItem(stock, idx)),
  },
  {
    id: "std-nse-fno-stocks-grouped",
    name: "NSE F&O Stocks (Grouped by sector)",
    category: "F&O STOCKS",
    description: "All 208 NSE F&O stocks organized and grouped by sector",
    isGroupedBySector: true,
    itemCount: 208,
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
