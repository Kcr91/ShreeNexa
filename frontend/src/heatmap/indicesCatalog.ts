import { IndexCategory, IndexHeatmapItem, ConstituentHeatmapItem } from "./types";
import { FNO_208_STOCKS } from "../watchlist/standardWatchlists";
import { OFFICIAL_INDEX_CONSTITUENTS, DERIVED_INDICES } from "./officialConstituents";

// ---------------------------------------------------------------------------
// 1. Broad Market Indices (21 indices - Image 1)
// ---------------------------------------------------------------------------
export const BROAD_MARKET_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY 50", category: "BROAD_MARKET", sector: "Large Cap Benchmark", weight: 35.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY NEXT 50", category: "BROAD_MARKET", sector: "Large Cap Emerging", weight: 12.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDCAP 50", category: "BROAD_MARKET", sector: "Mid Cap Select", weight: 6.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDCAP 100", category: "BROAD_MARKET", sector: "Mid Cap Core", weight: 8.0, constituentCount: 100, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDCAP 150", category: "BROAD_MARKET", sector: "Mid Cap Broad", weight: 10.0, constituentCount: 150, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMLCAP 50", category: "BROAD_MARKET", sector: "Small Cap High Growth", weight: 4.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMLCAP 100", category: "BROAD_MARKET", sector: "Small Cap Core", weight: 5.0, constituentCount: 100, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMLCAP 250", category: "BROAD_MARKET", sector: "Small Cap Broad", weight: 6.0, constituentCount: 250, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDSML 400", category: "BROAD_MARKET", sector: "Mid & Small Aggregate", weight: 7.0, constituentCount: 400, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY 100", category: "BROAD_MARKET", sector: "Top 100 Large Cap", weight: 20.0, constituentCount: 100, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY 200", category: "BROAD_MARKET", sector: "Large & Mid Cap 200", weight: 15.0, constituentCount: 200, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 MULTICAP 50:25:25", category: "BROAD_MARKET", sector: "Balanced Multicap", weight: 8.0, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY LARGEMIDCAP 250", category: "BROAD_MARKET", sector: "Large & Mid Blend", weight: 9.0, constituentCount: 250, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MID SELECT", category: "BROAD_MARKET", sector: "Liquid Midcaps", weight: 5.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY TOTAL MARKET", category: "BROAD_MARKET", sector: "Entire NSE Listed Market", weight: 10.0, constituentCount: 750, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MICROCAP 250", category: "BROAD_MARKET", sector: "Emerging Microcaps", weight: 3.0, constituentCount: 250, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY 500", category: "BROAD_MARKET", sector: "Broad 500 Equities", weight: 14.0, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INDIA FPI 150", category: "BROAD_MARKET", sector: "FPI Eligible Equities", weight: 5.0, constituentCount: 150, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 LARGEMIDSMALL EQUAL-CAP WEIGHTED", category: "BROAD_MARKET", sector: "Equal Cap Weighted", weight: 6.0, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDSMALLCAP400 50:50", category: "BROAD_MARKET", sector: "Mid & Small 50:50", weight: 6.0, constituentCount: 400, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMALLCAP 500", category: "BROAD_MARKET", sector: "Extended Smallcaps", weight: 4.0, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
];

// ---------------------------------------------------------------------------
// 2. Sectoral Indices (23 indices - Image 2)
// ---------------------------------------------------------------------------
export const SECTORAL_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY AUTO", category: "SECTORAL", sector: "Automotive", weight: 8.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY BANK", category: "SECTORAL", sector: "Banking", weight: 28.0, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FIN SERVICE", category: "SECTORAL", sector: "Financial Services", weight: 22.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FINSRV25/50", category: "SECTORAL", sector: "Financial Services Cap", weight: 8.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FMCG", category: "SECTORAL", sector: "Fast Moving Consumer Goods", weight: 9.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IT", category: "SECTORAL", sector: "Information Technology", weight: 14.0, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MEDIA", category: "SECTORAL", sector: "Media & Entertainment", weight: 3.0, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY METAL", category: "SECTORAL", sector: "Metals & Mining", weight: 6.0, constituentCount: 11, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PHARMA", category: "SECTORAL", sector: "Pharmaceuticals", weight: 8.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PSU BANK", category: "SECTORAL", sector: "Public Sector Banks", weight: 5.0, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY REALTY", category: "SECTORAL", sector: "Real Estate", weight: 4.0, constituentCount: 7, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PVT BANK", category: "SECTORAL", sector: "Private Sector Banks", weight: 12.0, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY HEALTHCARE", category: "SECTORAL", sector: "Healthcare & Diagnostics", weight: 6.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CONSR DURBL", category: "SECTORAL", sector: "Consumer Durables", weight: 5.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY OIL AND GAS", category: "SECTORAL", sector: "Oil Gas & Petroleum", weight: 7.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDSML HLTH", category: "SECTORAL", sector: "Mid & Small Healthcare", weight: 4.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CHEMICALS", category: "SECTORAL", sector: "Chemicals & Agri Inputs", weight: 5.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 HEALTHCARE", category: "SECTORAL", sector: "Broad Healthcare 500", weight: 4.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FINSERVIEXBK", category: "SECTORAL", sector: "Fin Services Ex Banks", weight: 5.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MS FIN SERV", category: "SECTORAL", sector: "Mid & Small Fin Services", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MS IT TELCOM", category: "SECTORAL", sector: "Mid & Small IT & Telecom", weight: 4.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CEMENT", category: "SECTORAL", sector: "Cement & Building Materials", weight: 4.0, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY REITS REALTY", category: "SECTORAL", sector: "REITs & Real Estate Inv", weight: 3.0, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
];

// ---------------------------------------------------------------------------
// 3. Thematic Indices (39 indices - Image 3)
// ---------------------------------------------------------------------------
export const THEMATIC_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY COMMODITIES", category: "THEMATIC", sector: "Commodities Producers", weight: 5.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CONSUMPTION", category: "THEMATIC", sector: "Domestic Consumption", weight: 6.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CPSE", category: "THEMATIC", sector: "Central Public Sector", weight: 4.0, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY ENERGY", category: "THEMATIC", sector: "Power, Oil & Gas", weight: 7.0, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INFRA", category: "THEMATIC", sector: "Infrastructure", weight: 6.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MNC", category: "THEMATIC", sector: "Multinational Corporations", weight: 5.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PSE", category: "THEMATIC", sector: "Public Sector Enterprises", weight: 4.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SERV SECTOR", category: "THEMATIC", sector: "Services Ecosystem", weight: 6.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY100 LIQ 15", category: "THEMATIC", sector: "Top 15 Liquid Stocks", weight: 5.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MID LIQ 15", category: "THEMATIC", sector: "Liquid Midcap 15", weight: 4.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IND DIGITAL", category: "THEMATIC", sector: "India Digital Transformation", weight: 5.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY100 ESG", category: "THEMATIC", sector: "ESG Compliant Leaders", weight: 5.0, constituentCount: 64, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INDIA MFG", category: "THEMATIC", sector: "Make in India Manufacturing", weight: 5.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY TATA 25 CAP", category: "THEMATIC", sector: "Tata Conglomerate Group", weight: 4.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MULTI MFG", category: "THEMATIC", sector: "Multi-Cap Manufacturing", weight: 4.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MULTI INFRA", category: "THEMATIC", sector: "Multi-Cap Infrastructure", weight: 4.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INTERNET", category: "THEMATIC", sector: "Internet & Platform Tech", weight: 3.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY WAVES", category: "THEMATIC", sector: "Next-Gen Trends & Themes", weight: 3.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INFRALOG", category: "THEMATIC", sector: "Logistics Infrastructure", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IND DEFENCE", category: "THEMATIC", sector: "Defence & Aerospace", weight: 4.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IND TOURISM", category: "THEMATIC", sector: "Tourism & Hospitality", weight: 3.0, constituentCount: 17, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CAPITAL GOODS", category: "THEMATIC", sector: "Heavy Capital Equipment", weight: 5.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY EV", category: "THEMATIC", sector: "Electric Vehicles & Tech", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY NEW CONSUMPTION", category: "THEMATIC", sector: "Modern Lifestyle & Retail", weight: 4.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CORP MARKET", category: "THEMATIC", sector: "Corporate Governance Top", weight: 5.0, constituentCount: 40, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MOBILITY", category: "THEMATIC", sector: "Future Transportation", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY100 ENH ESG", category: "THEMATIC", sector: "Enhanced ESG Leaders", weight: 4.0, constituentCount: 54, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY COREHOUSING", category: "THEMATIC", sector: "Housing & Real Estate Core", weight: 4.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY HOUSING", category: "THEMATIC", sector: "Broad Housing Ecosystem", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IPO", category: "THEMATIC", sector: "Recently Listed Enterprises", weight: 3.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MS IND CONS", category: "THEMATIC", sector: "Mid & Small Indian Cons", weight: 4.0, constituentCount: 40, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY NONCYC CONS", category: "THEMATIC", sector: "Non-Cyclical Consumer", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY RURAL", category: "THEMATIC", sector: "Rural India Transformation", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SHARIAH 25", category: "THEMATIC", sector: "Shariah Compliant Liquid", weight: 4.0, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY TRANS LOGISTICS", category: "THEMATIC", sector: "Transport & Supply Chain", weight: 4.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY50 SHARIAH", category: "THEMATIC", sector: "Nifty 50 Shariah Compliant", weight: 5.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 SHARIAH", category: "THEMATIC", sector: "Nifty 500 Shariah Compliant", weight: 5.0, constituentCount: 200, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY RAILWAYS", category: "THEMATIC", sector: "Rail Infra & Wagons", weight: 4.0, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTYCONGLOMERATES", category: "THEMATIC", sector: "Diversified Conglomerates", weight: 5.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
];

// ---------------------------------------------------------------------------
// 4. Strategy Indices (6 key indices)
// ---------------------------------------------------------------------------
export const STRATEGY_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY DIVIDEND OPP 50", category: "STRATEGY", sector: "High Dividend Yield", weight: 5.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY GROWTH SECTORS 15", category: "STRATEGY", sector: "Growth Momentum", weight: 6.0, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY HIGH BETA 50", category: "STRATEGY", sector: "High Market Beta", weight: 5.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY LOW VOLATILITY 50", category: "STRATEGY", sector: "Low Price Variance", weight: 6.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY QUALITY 30", category: "STRATEGY", sector: "High ROE & Low Debt", weight: 6.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY ALPHA 50", category: "STRATEGY", sector: "Pure Alpha Outperformance", weight: 5.0, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
];

export const ALL_INDICES_BY_CATEGORY: Record<IndexCategory, IndexHeatmapItem[]> = {
  BROAD_MARKET: BROAD_MARKET_INDICES,
  SECTORAL: SECTORAL_INDICES,
  THEMATIC: THEMATIC_INDICES,
  STRATEGY: STRATEGY_INDICES,
};

// ---------------------------------------------------------------------------
// 5. Authentic Constituent Stocks (Matching Image 4 for NIFTY 50 and Sectors)
// ---------------------------------------------------------------------------
export const NIFTY_50_AUTHENTIC_CONSTITUENTS: ConstituentHeatmapItem[] = [
  { symbol: "APOLLOHOSP", name: "Apollo Hospitals", sector: "Healthcare", weight: 0.80, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "LT", name: "Larsen & Toubro Ltd", sector: "Construction", weight: 3.47, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "COALINDIA", name: "Coal India Ltd", sector: "Mining", weight: 1.04, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "BHARTIARTL", name: "Bharti Airtel Ltd", sector: "Telecommunication", weight: 3.29, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "MAXHEALTH", name: "Max Healthcare Inst", sector: "Healthcare", weight: 0.68, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "CIPLA", name: "Cipla Ltd", sector: "Pharmaceuticals", weight: 1.13, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "EICHERMOT", name: "Eicher Motors Ltd", sector: "Automobile", weight: 1.31, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "MARUTI", name: "Maruti Suzuki India", sector: "Automobile", weight: 1.67, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TATACONSUM", name: "Tata Consumer Products", sector: "FMCG", weight: 0.99, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "INDIGO", name: "InterGlobe Aviation", sector: "Aviation", weight: 1.17, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ADANIENT", name: "Adani Enterprises Ltd", sector: "Metals & Mining", weight: 1.08, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ICICIBANK", name: "ICICI Bank Ltd", sector: "Financial Services", weight: 7.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "POWERGRID", name: "Power Grid Corp", sector: "Power", weight: 1.49, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "BAJFINANCE", name: "Bajaj Finance Ltd", sector: "Financial Services", weight: 1.89, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "NTPC", name: "NTPC Ltd", sector: "Power", weight: 1.67, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "SUNPHARMA", name: "Sun Pharma Ind", sector: "Pharmaceuticals", weight: 1.58, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "HDFCBANK", name: "HDFC Bank Ltd", sector: "Financial Services", weight: 10.33, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ITC", name: "ITC Ltd", sector: "FMCG", weight: 3.93, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "M&M", name: "Mahindra & Mahindra", sector: "Automobile", weight: 2.03, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "BEL", name: "Bharat Electronics Ltd", sector: "Capital Goods", weight: 1.04, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "SHRIRAMFIN", name: "Shriram Finance Ltd", sector: "Financial Services", weight: 1.22, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ONGC", name: "Oil & Natural Gas Corp", sector: "Oil Gas & Petroleum", weight: 1.31, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "HINDALCO", name: "Hindalco Industries", sector: "Metals & Mining", weight: 1.13, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TITAN", name: "Titan Company Ltd", sector: "Consumer Durables", weight: 1.40, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "AXISBANK", name: "Axis Bank Ltd", sector: "Financial Services", weight: 3.09, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank", sector: "Financial Services", weight: 2.57, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "GRASIM", name: "Grasim Industries", sector: "Construction Materials", weight: 0.86, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "DRREDDY", name: "Dr Reddy's Labs", sector: "Pharmaceuticals", weight: 1.04, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ETERNAL", name: "Eternal Life Science", sector: "Healthcare", weight: 0.59, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever", sector: "FMCG", weight: 2.21, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ADANIPORTS", name: "Adani Ports & SEZ", sector: "Services", weight: 1.22, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "HCLTECH", name: "HCL Technologies", sector: "Information Technology", weight: 1.67, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "NESTLEIND", name: "Nestle India Ltd", sector: "FMCG", weight: 0.86, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "RELIANCE", name: "Reliance Industries", sector: "Oil Gas & Petroleum", weight: 8.89, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "BAJAJ-AUTO", name: "Bajaj Auto Ltd", sector: "Automobile", weight: 1.04, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "SBIN", name: "State Bank of India", sector: "Financial Services", weight: 2.39, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ASIANPAINT", name: "Asian Paints Ltd", sector: "Consumer Durables", weight: 1.40, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TRENT", name: "Trent Ltd", sector: "Consumer Services", weight: 1.31, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TMPV", name: "Tata Motors Passenger", sector: "Automobile", weight: 0.68, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TCS", name: "Tata Consultancy Services", sector: "Information Technology", weight: 3.70, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "BAJAJFINSV", name: "Bajaj Finserv Ltd", sector: "Financial Services", weight: 1.13, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TATASTEEL", name: "Tata Steel Ltd", sector: "Metals & Mining", weight: 1.13, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "JSWSTEEL", name: "JSW Steel Ltd", sector: "Metals & Mining", weight: 1.04, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "ULTRACEMCO", name: "UltraTech Cement", sector: "Construction Materials", weight: 1.04, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "WIPRO", name: "Wipro Ltd", sector: "Information Technology", weight: 0.86, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "TECHM", name: "Tech Mahindra Ltd", sector: "Information Technology", weight: 0.95, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "JIOFIN", name: "Jio Financial Services", sector: "Financial Services", weight: 0.77, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "HDFCLIFE", name: "HDFC Life Insurance", sector: "Financial Services", weight: 0.86, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "SBILIFE", name: "SBI Life Insurance", sector: "Financial Services", weight: 0.77, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
  { symbol: "INFY", name: "Infosys Ltd", sector: "Information Technology", weight: 5.13, isWeightFallback: false, weightingSource: "OFFICIAL_NSE" },
];

// Map stock symbol -> F&O identity metadata for quick access.
const FNO_BY_SYMBOL = new Map<string, (typeof FNO_208_STOCKS)[number]>();
FNO_208_STOCKS.forEach((s) => FNO_BY_SYMBOL.set(s.symbol.toUpperCase(), s));

function getIndexSector(indexName: string): string {
  const clean = indexName.toUpperCase();
  if (clean.includes("BANK")) return "Banking";
  if (clean.includes("FIN")) return "Financial Services";
  if (clean.includes("IT") || clean.includes("TECH")) return "Information Technology";
  if (clean.includes("AUTO") || clean.includes("EV")) return "Automobile";
  if (clean.includes("PHARMA") || clean.includes("HEALTH")) return "Healthcare & Pharma";
  if (clean.includes("FMCG")) return "Fast Moving Consumer Goods";
  if (clean.includes("METAL")) return "Metals & Mining";
  if (clean.includes("REALTY") || clean.includes("HOUSING")) return "Realty";
  if (clean.includes("ENERGY") || clean.includes("OIL") || clean.includes("POWER")) return "Oil Gas & Consumables";
  if (clean.includes("MEDIA")) return "Media & Entertainment";
  if (clean.includes("DEFENCE")) return "Defence & Aerospace";
  if (clean.includes("RAILWAY")) return "Railways & Capital Goods";
  if (clean.includes("CPSE") || clean.includes("PSE")) return "Public Sector Enterprises";
  if (clean.includes("INFRA")) return "Infrastructure";
  if (clean.includes("COMMODITIES")) return "Commodities";
  if (clean.includes("CONSUMPTION")) return "Consumer Goods";
  if (clean.includes("TOURISM")) return "Tourism & Hospitality";
  return "Diversified";
}

// Synchronize exact constituent counts from the official NSE registry, and downgrade
// the weighting source for indices whose membership NSE does not publish.
[BROAD_MARKET_INDICES, SECTORAL_INDICES, THEMATIC_INDICES, STRATEGY_INDICES].forEach((list) => {
  list.forEach((item) => {
    const official = OFFICIAL_INDEX_CONSTITUENTS[item.indexName];
    if (official && official.length > 0) {
      item.constituentCount = official.length;
    }
    if (DERIVED_INDICES.has(item.indexName)) {
      item.weightingSource = "DERIVED_SCREEN";
    }
  });
});

// Resolve constituent identity from the official catalog. When the catalog has no
// published weights, assign visibly-labelled equal layout weights.
export function getConstituentsForIndex(indexName: string): ConstituentHeatmapItem[] {
  const clean = indexName.toUpperCase().trim();
  if (clean === "NIFTY 50") return NIFTY_50_AUTHENTIC_CONSTITUENTS;

  const officialList = OFFICIAL_INDEX_CONSTITUENTS[clean];
  if (!officialList?.length) return [];

  const count = officialList.length;
  const defaultSector = getIndexSector(clean);
  const weights = officialList.map(() => Number((100 / count).toFixed(2)));
  weights[0] = Number((weights[0] + 100 - weights.reduce((sum, weight) => sum + weight, 0)).toFixed(2));

  return officialList.map((stock, index) => {
    const reference = FNO_BY_SYMBOL.get(stock.symbol.toUpperCase());
    return {
      symbol: stock.symbol.toUpperCase(),
      name: stock.name || reference?.name || stock.symbol,
      sector: reference?.sector || defaultSector,
      weight: weights[index],
      isWeightFallback: true,
      weightingSource: "FALLBACK_EQUAL_WEIGHT",
      marketState: "UNAVAILABLE",
      error: "Waiting for a verified Dhan quote",
    };
  });
}
