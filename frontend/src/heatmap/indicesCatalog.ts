import { IndexCategory, IndexHeatmapItem, ConstituentHeatmapItem } from "./types";
import { FNO_208_STOCKS } from "../watchlist/standardWatchlists";

// ---------------------------------------------------------------------------
// 1. Broad Market Indices (21 indices - Image 1)
// ---------------------------------------------------------------------------
export const BROAD_MARKET_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY 50", category: "BROAD_MARKET", sector: "Large Cap Benchmark", weight: 35.0, ltp: 23779.15, changePct: -0.50, advances: 13, declines: 37, unchanged: 0, futuresBasis: 22.5, oiChangePct: 1.8, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY NEXT 50", category: "BROAD_MARKET", sector: "Large Cap Emerging", weight: 12.0, ltp: 72575.75, changePct: -0.42, advances: 18, declines: 32, unchanged: 0, futuresBasis: 35.0, oiChangePct: 0.9, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDCAP 50", category: "BROAD_MARKET", sector: "Mid Cap Select", weight: 6.0, ltp: 16051.60, changePct: -0.42, advances: 19, declines: 31, unchanged: 0, futuresBasis: 15.0, oiChangePct: 1.1, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDCAP 100", category: "BROAD_MARKET", sector: "Mid Cap Core", weight: 8.0, ltp: 52796.15, changePct: -0.40, advances: 42, declines: 58, unchanged: 0, futuresBasis: 45.0, oiChangePct: 2.2, constituentCount: 100, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDCAP 150", category: "BROAD_MARKET", sector: "Mid Cap Broad", weight: 10.0, ltp: 23062.25, changePct: -0.49, advances: 55, declines: 95, unchanged: 0, futuresBasis: 28.0, oiChangePct: 1.5, constituentCount: 150, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMLCAP 50", category: "BROAD_MARKET", sector: "Small Cap High Growth", weight: 4.0, ltp: 10026.65, changePct: 0.07, advances: 27, declines: 23, unchanged: 0, futuresBasis: 8.0, oiChangePct: 3.4, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMLCAP 100", category: "BROAD_MARKET", sector: "Small Cap Core", weight: 5.0, ltp: 20100.20, changePct: 0.02, advances: 52, declines: 48, unchanged: 0, futuresBasis: 12.0, oiChangePct: 2.1, constituentCount: 100, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMLCAP 250", category: "BROAD_MARKET", sector: "Small Cap Broad", weight: 6.0, ltp: 18484.15, changePct: 0.01, advances: 128, declines: 122, unchanged: 0, futuresBasis: 16.0, oiChangePct: 1.9, constituentCount: 250, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDSML 400", category: "BROAD_MARKET", sector: "Mid & Small Aggregate", weight: 7.0, ltp: 21414.95, changePct: -0.29, advances: 175, declines: 225, unchanged: 0, futuresBasis: 20.0, oiChangePct: 1.4, constituentCount: 400, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY 100", category: "BROAD_MARKET", sector: "Top 100 Large Cap", weight: 20.0, ltp: 24902.50, changePct: -0.49, advances: 31, declines: 69, unchanged: 0, futuresBasis: 30.0, oiChangePct: 1.6, constituentCount: 100, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY 200", category: "BROAD_MARKET", sector: "Large & Mid Cap 200", weight: 15.0, ltp: 13942.00, changePct: -0.49, advances: 73, declines: 127, unchanged: 0, futuresBasis: 18.0, oiChangePct: 1.7, constituentCount: 200, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 MULTICAP 50:25:25", category: "BROAD_MARKET", sector: "Balanced Multicap", weight: 8.0, ltp: 16503.85, changePct: -0.35, advances: 190, declines: 310, unchanged: 0, futuresBasis: 22.0, oiChangePct: 0.8, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY LARGEMIDCAP 250", category: "BROAD_MARKET", sector: "Large & Mid Blend", weight: 9.0, ltp: 16576.65, changePct: -0.47, advances: 86, declines: 164, unchanged: 0, futuresBasis: 24.0, oiChangePct: 1.3, constituentCount: 250, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MID SELECT", category: "BROAD_MARKET", sector: "Liquid Midcaps", weight: 5.0, ltp: 14650.70, changePct: -0.43, advances: 10, declines: 15, unchanged: 0, futuresBasis: 14.0, oiChangePct: 2.6, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY TOTAL MARKET", category: "BROAD_MARKET", sector: "Entire NSE Listed Market", weight: 10.0, ltp: 13097.90, changePct: -0.38, advances: 340, declines: 410, unchanged: 0, futuresBasis: 19.0, oiChangePct: 1.0, constituentCount: 750, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MICROCAP 250", category: "BROAD_MARKET", sector: "Emerging Microcaps", weight: 3.0, ltp: 26575.60, changePct: 0.42, advances: 145, declines: 105, unchanged: 0, futuresBasis: 10.0, oiChangePct: 4.2, constituentCount: 250, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY 500", category: "BROAD_MARKET", sector: "Broad 500 Equities", weight: 14.0, ltp: 22156.20, changePct: -0.42, advances: 195, declines: 305, unchanged: 0, futuresBasis: 26.0, oiChangePct: 1.2, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INDIA FPI 150", category: "BROAD_MARKET", sector: "FPI Eligible Equities", weight: 5.0, ltp: 1545.20, changePct: -0.55, advances: 48, declines: 102, unchanged: 0, futuresBasis: 5.0, oiChangePct: -0.4, constituentCount: 150, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 LARGEMIDSMALL EQUAL-CAP WEIGHTED", category: "BROAD_MARKET", sector: "Equal Cap Weighted", weight: 6.0, ltp: 19527.05, changePct: -0.31, advances: 210, declines: 290, unchanged: 0, futuresBasis: 15.0, oiChangePct: 0.7, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDSMALLCAP400 50:50", category: "BROAD_MARKET", sector: "Mid & Small 50:50", weight: 6.0, ltp: 20950.10, changePct: -0.22, advances: 180, declines: 220, unchanged: 0, futuresBasis: 18.0, oiChangePct: 1.2, constituentCount: 400, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SMALLCAP 500", category: "BROAD_MARKET", sector: "Extended Smallcaps", weight: 4.0, ltp: 21114.35, changePct: 0.12, advances: 270, declines: 230, unchanged: 0, futuresBasis: 11.0, oiChangePct: 2.8, constituentCount: 500, weightingSource: "OFFICIAL_NSE" },
];

// ---------------------------------------------------------------------------
// 2. Sectoral Indices (23 indices - Image 2)
// ---------------------------------------------------------------------------
export const SECTORAL_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY AUTO", category: "SECTORAL", sector: "Automotive", weight: 8.0, ltp: 27098.75, changePct: -0.04, advances: 7, declines: 8, unchanged: 0, futuresBasis: 18.0, oiChangePct: 1.4, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY BANK", category: "SECTORAL", sector: "Banking", weight: 28.0, ltp: 57088.30, changePct: -0.49, advances: 4, declines: 8, unchanged: 0, futuresBasis: 65.0, oiChangePct: 3.2, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FIN SERVICE", category: "SECTORAL", sector: "Financial Services", weight: 22.0, ltp: 25935.60, changePct: -0.44, advances: 7, declines: 13, unchanged: 0, futuresBasis: 42.0, oiChangePct: 2.1, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FINSRV25/50", category: "SECTORAL", sector: "Financial Services Cap", weight: 8.0, ltp: 26073.70, changePct: -0.51, advances: 6, declines: 14, unchanged: 0, futuresBasis: 38.0, oiChangePct: 1.9, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FMCG", category: "SECTORAL", sector: "Fast Moving Consumer Goods", weight: 9.0, ltp: 65592.15, changePct: -0.66, advances: 4, declines: 11, unchanged: 0, futuresBasis: -25.0, oiChangePct: -0.8, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IT", category: "SECTORAL", sector: "Information Technology", weight: 14.0, ltp: 39995.20, changePct: -2.29, advances: 1, declines: 9, unchanged: 0, futuresBasis: -85.0, oiChangePct: -3.5, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MEDIA", category: "SECTORAL", sector: "Media & Entertainment", weight: 3.0, ltp: 1520.65, changePct: -2.96, advances: 2, declines: 8, unchanged: 0, futuresBasis: -12.0, oiChangePct: -1.2, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY METAL", category: "SECTORAL", sector: "Metals & Mining", weight: 6.0, ltp: 13152.90, changePct: -1.24, advances: 3, declines: 8, unchanged: 0, futuresBasis: -20.0, oiChangePct: 0.5, constituentCount: 11, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PHARMA", category: "SECTORAL", sector: "Pharmaceuticals", weight: 8.0, ltp: 26675.50, changePct: 0.75, advances: 15, declines: 5, unchanged: 0, futuresBasis: 32.0, oiChangePct: 4.1, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PSU BANK", category: "SECTORAL", sector: "Public Sector Banks", weight: 5.0, ltp: 8424.65, changePct: -1.06, advances: 3, declines: 9, unchanged: 0, futuresBasis: -15.0, oiChangePct: 1.8, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY REALTY", category: "SECTORAL", sector: "Real Estate", weight: 4.0, ltp: 892.50, changePct: -1.70, advances: 1, declines: 6, unchanged: 0, futuresBasis: -8.0, oiChangePct: -0.6, constituentCount: 7, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PVT BANK", category: "SECTORAL", sector: "Private Sector Banks", weight: 12.0, ltp: 27745.75, changePct: -0.28, advances: 4, declines: 6, unchanged: 0, futuresBasis: 25.0, oiChangePct: 2.4, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY HEALTHCARE", category: "SECTORAL", sector: "Healthcare & Diagnostics", weight: 6.0, ltp: 16520.30, changePct: 0.68, advances: 14, declines: 6, unchanged: 0, futuresBasis: 22.0, oiChangePct: 3.2, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CONSR DURBL", category: "SECTORAL", sector: "Consumer Durables", weight: 5.0, ltp: 39318.80, changePct: -0.42, advances: 6, declines: 9, unchanged: 0, futuresBasis: 10.0, oiChangePct: 1.1, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY OIL AND GAS", category: "SECTORAL", sector: "Oil Gas & Petroleum", weight: 7.0, ltp: 11118.85, changePct: -0.61, advances: 5, declines: 10, unchanged: 0, futuresBasis: -14.0, oiChangePct: 0.9, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MIDSML HLTH", category: "SECTORAL", sector: "Mid & Small Healthcare", weight: 4.0, ltp: 52275.15, changePct: 0.65, advances: 16, declines: 9, unchanged: 0, futuresBasis: 35.0, oiChangePct: 2.8, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CHEMICALS", category: "SECTORAL", sector: "Chemicals & Agri Inputs", weight: 5.0, ltp: 39961.90, changePct: -0.40, advances: 7, declines: 13, unchanged: 0, futuresBasis: 12.0, oiChangePct: 1.3, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 HEALTHCARE", category: "SECTORAL", sector: "Broad Healthcare 500", weight: 4.0, ltp: 21648.20, changePct: 0.78, advances: 35, declines: 15, unchanged: 0, futuresBasis: 28.0, oiChangePct: 3.5, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY FINSERVIEXBK", category: "SECTORAL", sector: "Fin Services Ex Banks", weight: 5.0, ltp: 21997.70, changePct: -0.57, advances: 5, declines: 10, unchanged: 0, futuresBasis: 16.0, oiChangePct: 1.5, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MS FIN SERV", category: "SECTORAL", sector: "Mid & Small Fin Services", weight: 4.0, ltp: 22736.65, changePct: -0.36, advances: 12, declines: 18, unchanged: 0, futuresBasis: 18.0, oiChangePct: 1.7, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MS IT TELCOM", category: "SECTORAL", sector: "Mid & Small IT & Telecom", weight: 4.0, ltp: 10156.05, changePct: -0.49, advances: 8, declines: 12, unchanged: 0, futuresBasis: 8.0, oiChangePct: 0.6, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CEMENT", category: "SECTORAL", sector: "Cement & Building Materials", weight: 4.0, ltp: 14440.45, changePct: -1.44, advances: 2, declines: 8, unchanged: 0, futuresBasis: -22.0, oiChangePct: -1.1, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY REITS REALTY", category: "SECTORAL", sector: "REITs & Real Estate Inv", weight: 3.0, ltp: 1920.35, changePct: -0.63, advances: 3, declines: 7, unchanged: 0, futuresBasis: 4.0, oiChangePct: 0.4, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
];

// ---------------------------------------------------------------------------
// 3. Thematic Indices (39 indices - Image 3)
// ---------------------------------------------------------------------------
export const THEMATIC_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY COMMODITIES", category: "THEMATIC", sector: "Commodities Producers", weight: 5.0, ltp: 9702.10, changePct: -1.04, advances: 8, declines: 22, unchanged: 0, futuresBasis: -15.0, oiChangePct: 0.8, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CONSUMPTION", category: "THEMATIC", sector: "Domestic Consumption", weight: 6.0, ltp: 11560.75, changePct: -0.32, advances: 12, declines: 18, unchanged: 0, futuresBasis: 8.0, oiChangePct: 1.2, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CPSE", category: "THEMATIC", sector: "Central Public Sector", weight: 4.0, ltp: 6417.25, changePct: -0.04, advances: 5, declines: 7, unchanged: 0, futuresBasis: 6.0, oiChangePct: 2.1, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY ENERGY", category: "THEMATIC", sector: "Power, Oil & Gas", weight: 7.0, ltp: 37973.35, changePct: -0.25, advances: 3, declines: 7, unchanged: 0, futuresBasis: 20.0, oiChangePct: 1.5, constituentCount: 10, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INFRA", category: "THEMATIC", sector: "Infrastructure", weight: 6.0, ltp: 9188.70, changePct: -0.30, advances: 11, declines: 19, unchanged: 0, futuresBasis: 12.0, oiChangePct: 1.6, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MNC", category: "THEMATIC", sector: "Multinational Corporations", weight: 5.0, ltp: 32038.05, changePct: -0.23, advances: 14, declines: 16, unchanged: 0, futuresBasis: 18.0, oiChangePct: 0.9, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY PSE", category: "THEMATIC", sector: "Public Sector Enterprises", weight: 4.0, ltp: 9680.05, changePct: -0.31, advances: 8, declines: 12, unchanged: 0, futuresBasis: 14.0, oiChangePct: 1.8, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SERV SECTOR", category: "THEMATIC", sector: "Services Ecosystem", weight: 6.0, ltp: 30422.70, changePct: -0.50, advances: 11, declines: 19, unchanged: 0, futuresBasis: 25.0, oiChangePct: 1.3, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY100 LIQ 15", category: "THEMATIC", sector: "Top 15 Liquid Stocks", weight: 5.0, ltp: 7475.05, changePct: -0.34, advances: 5, declines: 10, unchanged: 0, futuresBasis: 10.0, oiChangePct: 2.5, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MID LIQ 15", category: "THEMATIC", sector: "Liquid Midcap 15", weight: 4.0, ltp: 17230.50, changePct: -0.30, advances: 6, declines: 9, unchanged: 0, futuresBasis: 15.0, oiChangePct: 2.2, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IND DIGITAL", category: "THEMATIC", sector: "India Digital Transformation", weight: 5.0, ltp: 8881.65, changePct: -0.91, advances: 8, declines: 22, unchanged: 0, futuresBasis: -16.0, oiChangePct: -1.0, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY100 ESG", category: "THEMATIC", sector: "ESG Compliant Leaders", weight: 5.0, ltp: 4920.55, changePct: -0.68, advances: 22, declines: 42, unchanged: 0, futuresBasis: 8.0, oiChangePct: 0.7, constituentCount: 64, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INDIA MFG", category: "THEMATIC", sector: "Make in India Manufacturing", weight: 5.0, ltp: 16187.00, changePct: -0.21, advances: 16, declines: 14, unchanged: 0, futuresBasis: 12.0, oiChangePct: 1.8, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY TATA 25 CAP", category: "THEMATIC", sector: "Tata Conglomerate Group", weight: 4.0, ltp: 14239.50, changePct: -0.89, advances: 7, declines: 18, unchanged: 0, futuresBasis: -18.0, oiChangePct: 0.4, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MULTI MFG", category: "THEMATIC", sector: "Multi-Cap Manufacturing", weight: 4.0, ltp: 16732.55, changePct: -0.32, advances: 24, declines: 26, unchanged: 0, futuresBasis: 14.0, oiChangePct: 1.1, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MULTI INFRA", category: "THEMATIC", sector: "Multi-Cap Infrastructure", weight: 4.0, ltp: 14437.10, changePct: -0.11, advances: 26, declines: 24, unchanged: 0, futuresBasis: 10.0, oiChangePct: 1.4, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INTERNET", category: "THEMATIC", sector: "Internet & Platform Tech", weight: 3.0, ltp: 1457.45, changePct: -0.23, advances: 8, declines: 12, unchanged: 0, futuresBasis: 5.0, oiChangePct: 2.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY WAVES", category: "THEMATIC", sector: "Next-Gen Trends & Themes", weight: 3.0, ltp: 1882.15, changePct: -0.58, advances: 9, declines: 16, unchanged: 0, futuresBasis: 6.0, oiChangePct: 0.9, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY INFRALOG", category: "THEMATIC", sector: "Logistics Infrastructure", weight: 4.0, ltp: 1940.80, changePct: -0.30, advances: 12, declines: 18, unchanged: 0, futuresBasis: 7.0, oiChangePct: 1.5, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IND DEFENCE", category: "THEMATIC", sector: "Defence & Aerospace", weight: 4.0, ltp: 9754.55, changePct: 0.47, advances: 11, declines: 4, unchanged: 0, futuresBasis: 24.0, oiChangePct: 5.6, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IND TOURISM", category: "THEMATIC", sector: "Tourism & Hospitality", weight: 3.0, ltp: 7776.10, changePct: -0.51, advances: 6, declines: 11, unchanged: 0, futuresBasis: -4.0, oiChangePct: 0.8, constituentCount: 17, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CAPITAL GOODS", category: "THEMATIC", sector: "Heavy Capital Equipment", weight: 5.0, ltp: 5457.60, changePct: 0.71, advances: 14, declines: 6, unchanged: 0, futuresBasis: 19.0, oiChangePct: 3.8, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY EV", category: "THEMATIC", sector: "Electric Vehicles & Tech", weight: 4.0, ltp: 3207.30, changePct: -0.30, advances: 11, declines: 19, unchanged: 0, futuresBasis: 8.0, oiChangePct: 1.7, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY NEW CONSUMPTION", category: "THEMATIC", sector: "Modern Lifestyle & Retail", weight: 4.0, ltp: 11921.50, changePct: -0.30, advances: 10, declines: 15, unchanged: 0, futuresBasis: 9.0, oiChangePct: 1.4, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY CORP MARKET", category: "THEMATIC", sector: "Corporate Governance Top", weight: 5.0, ltp: 38396.65, changePct: -0.92, advances: 12, declines: 28, unchanged: 0, futuresBasis: -22.0, oiChangePct: 0.3, constituentCount: 40, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MOBILITY", category: "THEMATIC", sector: "Future Transportation", weight: 4.0, ltp: 23018.05, changePct: -0.17, advances: 13, declines: 17, unchanged: 0, futuresBasis: 11.0, oiChangePct: 1.5, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY100 ENH ESG", category: "THEMATIC", sector: "Enhanced ESG Leaders", weight: 4.0, ltp: 4952.95, changePct: -0.68, advances: 18, declines: 36, unchanged: 0, futuresBasis: 7.0, oiChangePct: 0.5, constituentCount: 54, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY COREHOUSING", category: "THEMATIC", sector: "Housing & Real Estate Core", weight: 4.0, ltp: 15274.75, changePct: -1.39, advances: 6, declines: 19, unchanged: 0, futuresBasis: -16.0, oiChangePct: -0.8, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY HOUSING", category: "THEMATIC", sector: "Broad Housing Ecosystem", weight: 4.0, ltp: 11701.30, changePct: -0.79, advances: 11, declines: 19, unchanged: 0, futuresBasis: -10.0, oiChangePct: 0.2, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY IPO", category: "THEMATIC", sector: "Recently Listed Enterprises", weight: 3.0, ltp: 2425.75, changePct: 0.00, advances: 12, declines: 12, unchanged: 1, futuresBasis: 5.0, oiChangePct: 3.1, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY MS IND CONS", category: "THEMATIC", sector: "Mid & Small Indian Cons", weight: 4.0, ltp: 18406.55, changePct: -0.51, advances: 14, declines: 26, unchanged: 0, futuresBasis: 10.0, oiChangePct: 1.1, constituentCount: 40, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY NONCYC CONS", category: "THEMATIC", sector: "Non-Cyclical Consumer", weight: 4.0, ltp: 14985.00, changePct: -0.53, advances: 10, declines: 20, unchanged: 0, futuresBasis: 6.0, oiChangePct: 0.4, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY RURAL", category: "THEMATIC", sector: "Rural India Transformation", weight: 4.0, ltp: 15034.90, changePct: -0.40, advances: 12, declines: 18, unchanged: 0, futuresBasis: 9.0, oiChangePct: 1.2, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY SHARIAH 25", category: "THEMATIC", sector: "Shariah Compliant Liquid", weight: 4.0, ltp: 7784.35, changePct: -0.86, advances: 7, declines: 18, unchanged: 0, futuresBasis: -11.0, oiChangePct: 0.6, constituentCount: 25, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY TRANS LOGISTICS", category: "THEMATIC", sector: "Transport & Supply Chain", weight: 4.0, ltp: 25629.35, changePct: -0.30, advances: 13, declines: 17, unchanged: 0, futuresBasis: 12.0, oiChangePct: 1.6, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY50 SHARIAH", category: "THEMATIC", sector: "Nifty 50 Shariah Compliant", weight: 5.0, ltp: 4156.65, changePct: -1.33, advances: 5, declines: 15, unchanged: 0, futuresBasis: -14.0, oiChangePct: -0.2, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY500 SHARIAH", category: "THEMATIC", sector: "Nifty 500 Shariah Compliant", weight: 5.0, ltp: 6895.00, changePct: -0.69, advances: 65, declines: 135, unchanged: 0, futuresBasis: 15.0, oiChangePct: 0.8, constituentCount: 200, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY RAILWAYS", category: "THEMATIC", sector: "Rail Infra & Wagons", weight: 4.0, ltp: 2750.55, changePct: -0.68, advances: 4, declines: 8, unchanged: 0, futuresBasis: -5.0, oiChangePct: 1.9, constituentCount: 12, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTYCONGLOMERATES", category: "THEMATIC", sector: "Diversified Conglomerates", weight: 5.0, ltp: 15058.45, changePct: -0.65, advances: 6, declines: 14, unchanged: 0, futuresBasis: 16.0, oiChangePct: 1.0, constituentCount: 20, weightingSource: "OFFICIAL_NSE" },
];

// ---------------------------------------------------------------------------
// 4. Strategy Indices (6 key indices)
// ---------------------------------------------------------------------------
export const STRATEGY_INDICES: IndexHeatmapItem[] = [
  { indexName: "NIFTY DIVIDEND OPP 50", category: "STRATEGY", sector: "High Dividend Yield", weight: 5.0, ltp: 6450.20, changePct: 0.15, advances: 28, declines: 22, unchanged: 0, futuresBasis: 10.0, oiChangePct: 1.5, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY GROWTH SECTORS 15", category: "STRATEGY", sector: "Growth Momentum", weight: 6.0, ltp: 11200.50, changePct: -0.25, advances: 6, declines: 9, unchanged: 0, futuresBasis: 14.0, oiChangePct: 2.1, constituentCount: 15, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY HIGH BETA 50", category: "STRATEGY", sector: "High Market Beta", weight: 5.0, ltp: 4890.30, changePct: -0.70, advances: 18, declines: 32, unchanged: 0, futuresBasis: -15.0, oiChangePct: 3.4, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY LOW VOLATILITY 50", category: "STRATEGY", sector: "Low Price Variance", weight: 6.0, ltp: 24150.00, changePct: 0.35, advances: 33, declines: 17, unchanged: 0, futuresBasis: 20.0, oiChangePct: 1.2, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY QUALITY 30", category: "STRATEGY", sector: "High ROE & Low Debt", weight: 6.0, ltp: 5320.10, changePct: 0.20, advances: 19, declines: 11, unchanged: 0, futuresBasis: 12.0, oiChangePct: 1.8, constituentCount: 30, weightingSource: "OFFICIAL_NSE" },
  { indexName: "NIFTY ALPHA 50", category: "STRATEGY", sector: "Pure Alpha Outperformance", weight: 5.0, ltp: 47800.00, changePct: -0.45, advances: 20, declines: 30, unchanged: 0, futuresBasis: 25.0, oiChangePct: 2.9, constituentCount: 50, weightingSource: "OFFICIAL_NSE" },
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
  { symbol: "APOLLOHOSP", name: "Apollo Hospitals", sector: "Healthcare", weight: 0.95, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 8750.00, changePct: 1.27, volume: 850000 },
  { symbol: "LT", name: "Larsen & Toubro Ltd", sector: "Construction", weight: 3.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 3659.00, changePct: 0.89, volume: 1450000 },
  { symbol: "COALINDIA", name: "Coal India Ltd", sector: "Mining", weight: 1.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 419.65, changePct: 0.84, volume: 6200000 },
  { symbol: "BHARTIARTL", name: "Bharti Airtel Ltd", sector: "Telecommunication", weight: 3.65, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1654.00, changePct: 0.76, volume: 3800000 },
  { symbol: "MAXHEALTH", name: "Max Healthcare Inst", sector: "Healthcare", weight: 0.75, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 992.00, changePct: 0.73, volume: 1100000 },
  { symbol: "CIPLA", name: "Cipla Ltd", sector: "Pharmaceuticals", weight: 1.25, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1395.00, changePct: 0.72, volume: 1900000 },
  { symbol: "EICHERMOT", name: "Eicher Motors Ltd", sector: "Automobile", weight: 1.45, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 7672.00, changePct: 0.54, volume: 620000 },
  { symbol: "MARUTI", name: "Maruti Suzuki India", sector: "Automobile", weight: 1.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 12760.00, changePct: 0.52, volume: 740000 },
  { symbol: "TATACONSUM", name: "Tata Consumer Products", sector: "FMCG", weight: 1.10, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1015.00, changePct: 0.50, volume: 1800000 },
  { symbol: "INDIGO", name: "InterGlobe Aviation", sector: "Aviation", weight: 1.30, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 5001.00, changePct: 0.49, volume: 950000 },
  { symbol: "ADANIENT", name: "Adani Enterprises Ltd", sector: "Metals & Mining", weight: 1.20, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 2950.00, changePct: 0.41, volume: 2200000 },
  { symbol: "ICICIBANK", name: "ICICI Bank Ltd", sector: "Financial Services", weight: 7.92, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1427.50, changePct: 0.30, volume: 8900000 },
  { symbol: "POWERGRID", name: "Power Grid Corp", sector: "Power", weight: 1.65, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 288.45, changePct: 0.17, volume: 7500000 },
  { symbol: "BAJFINANCE", name: "Bajaj Finance Ltd", sector: "Financial Services", weight: 2.10, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 7090.00, changePct: -0.05, volume: 1100000 },
  { symbol: "NTPC", name: "NTPC Ltd", sector: "Power", weight: 1.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 332.00, changePct: -0.15, volume: 9400000 },
  { symbol: "SUNPHARMA", name: "Sun Pharma Ind", sector: "Pharmaceuticals", weight: 1.75, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1695.00, changePct: -0.21, volume: 2100000 },
  { symbol: "HDFCBANK", name: "HDFC Bank Ltd", sector: "Financial Services", weight: 11.45, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1640.50, changePct: -0.22, volume: 11200000 },
  { symbol: "ITC", name: "ITC Ltd", sector: "FMCG", weight: 4.35, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 493.50, changePct: -0.23, volume: 8600000 },
  { symbol: "M&M", name: "Mahindra & Mahindra", sector: "Automobile", weight: 2.25, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 3160.00, changePct: -0.32, volume: 1750000 },
  { symbol: "BEL", name: "Bharat Electronics Ltd", sector: "Capital Goods", weight: 1.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 404.00, changePct: -0.33, volume: 5400000 },
  { symbol: "SHRIRAMFIN", name: "Shriram Finance Ltd", sector: "Financial Services", weight: 1.35, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 3237.00, changePct: -0.38, volume: 980000 },
  { symbol: "ONGC", name: "Oil & Natural Gas Corp", sector: "Oil Gas & Petroleum", weight: 1.45, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 233.70, changePct: -0.40, volume: 7600000 },
  { symbol: "HINDALCO", name: "Hindalco Industries", sector: "Metals & Mining", weight: 1.25, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1006.00, changePct: -0.49, volume: 3100000 },
  { symbol: "TITAN", name: "Titan Company Ltd", sector: "Consumer Durables", weight: 1.55, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 3495.00, changePct: -0.50, volume: 880000 },
  { symbol: "AXISBANK", name: "Axis Bank Ltd", sector: "Financial Services", weight: 3.42, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1266.00, changePct: -0.55, volume: 4600000 },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank", sector: "Financial Services", weight: 2.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1822.10, changePct: -0.57, volume: 2900000 },
  { symbol: "GRASIM", name: "Grasim Industries", sector: "Construction Materials", weight: 0.95, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 3302.40, changePct: -0.59, volume: 720000 },
  { symbol: "DRREDDY", name: "Dr Reddy's Labs", sector: "Pharmaceuticals", weight: 1.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1144.20, changePct: -0.59, volume: 850000 },
  { symbol: "ETERNAL", name: "Eternal Life Science", sector: "Healthcare", weight: 0.65, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 320.00, changePct: -0.60, volume: 450000 },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever", sector: "FMCG", weight: 2.45, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1960.00, changePct: -0.69, volume: 2300000 },
  { symbol: "ADANIPORTS", name: "Adani Ports & SEZ", sector: "Services", weight: 1.35, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1694.30, changePct: -0.76, volume: 2600000 },
  { symbol: "HCLTECH", name: "HCL Technologies", sector: "Information Technology", weight: 1.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1292.00, changePct: -0.82, volume: 1900000 },
  { symbol: "NESTLEIND", name: "Nestle India Ltd", sector: "FMCG", weight: 0.95, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1399.00, changePct: -0.89, volume: 640000 },
  { symbol: "RELIANCE", name: "Reliance Industries", sector: "Oil Gas & Petroleum", weight: 9.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 2980.50, changePct: -0.95, volume: 6800000 },
  { symbol: "BAJAJ-AUTO", name: "Bajaj Auto Ltd", sector: "Automobile", weight: 1.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 11800.00, changePct: -1.00, volume: 420000 },
  { symbol: "SBIN", name: "State Bank of India", sector: "Financial Services", weight: 2.65, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 815.90, changePct: -1.00, volume: 9200000 },
  { symbol: "ASIANPAINT", name: "Asian Paints Ltd", sector: "Consumer Durables", weight: 1.55, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 2500.90, changePct: -1.04, volume: 1100000 },
  { symbol: "TRENT", name: "Trent Ltd", sector: "Consumer Services", weight: 1.45, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 2814.50, changePct: -1.35, volume: 1350000 },
  { symbol: "TMPV", name: "Tata Motors Passenger", sector: "Automobile", weight: 0.75, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 307.00, changePct: -1.44, volume: 3200000 },
  { symbol: "TCS", name: "Tata Consultancy Services", sector: "Information Technology", weight: 4.10, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 4210.00, changePct: -1.48, volume: 2400000 },
  { symbol: "BAJAJFINSV", name: "Bajaj Finserv Ltd", sector: "Financial Services", weight: 1.25, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1939.60, changePct: -1.59, volume: 1200000 },
  { symbol: "TATASTEEL", name: "Tata Steel Ltd", sector: "Metals & Mining", weight: 1.25, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 154.61, changePct: -1.68, volume: 12500000 },
  { symbol: "JSWSTEEL", name: "JSW Steel Ltd", sector: "Metals & Mining", weight: 1.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1302.00, changePct: -1.74, volume: 2100000 },
  { symbol: "ULTRACEMCO", name: "UltraTech Cement", sector: "Construction Materials", weight: 1.15, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 11175.00, changePct: -2.04, volume: 550000 },
  { symbol: "WIPRO", name: "Wipro Ltd", sector: "Information Technology", weight: 0.95, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 540.90, changePct: -2.04, volume: 4100000 },
  { symbol: "TECHM", name: "Tech Mahindra Ltd", sector: "Information Technology", weight: 1.05, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1564.00, changePct: -2.06, volume: 1600000 },
  { symbol: "JIOFIN", name: "Jio Financial Services", sector: "Financial Services", weight: 0.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 334.40, changePct: -2.13, volume: 7800000 },
  { symbol: "HDFCLIFE", name: "HDFC Life Insurance", sector: "Financial Services", weight: 0.95, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 533.20, changePct: -2.42, volume: 2200000 },
  { symbol: "SBILIFE", name: "SBI Life Insurance", sector: "Financial Services", weight: 0.85, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1732.00, changePct: -2.42, volume: 1400000 },
  { symbol: "INFY", name: "Infosys Ltd", sector: "Information Technology", weight: 5.68, isWeightFallback: false, weightingSource: "OFFICIAL_NSE", ltp: 1887.50, changePct: -3.78, volume: 8200000 },
];

// Helper to generate realistic constituents for any index from FNO_208_STOCKS
export function getConstituentsForIndex(indexName: string): ConstituentHeatmapItem[] {
  const clean = indexName.toUpperCase().trim();
  if (clean === "NIFTY 50") {
    return NIFTY_50_AUTHENTIC_CONSTITUENTS;
  }

  // Filter stocks by relevant sector or keywords
  let matching = FNO_208_STOCKS.filter((stock) => {
    if (clean.includes("BANK") || clean.includes("FIN")) {
      return stock.sector === "Financial Services";
    }
    if (clean.includes("IT") || clean.includes("TECH") || clean.includes("DIGITAL")) {
      return stock.sector === "Information Technology" || stock.sector === "Telecommunication";
    }
    if (clean.includes("AUTO")) {
      return stock.sector === "Automobile";
    }
    if (clean.includes("PHARMA") || clean.includes("HEALTH")) {
      return stock.sector === "Healthcare & Pharma";
    }
    if (clean.includes("FMCG") || clean.includes("CONSUMPTION") || clean.includes("CONSR")) {
      return stock.sector === "FMCG" || stock.sector === "Consumer Services" || stock.sector === "Consumer Durables";
    }
    if (clean.includes("METAL")) {
      return stock.sector === "Metals & Mining";
    }
    if (clean.includes("REALTY") || clean.includes("HOUSING")) {
      return stock.sector === "Realty";
    }
    if (clean.includes("ENERGY") || clean.includes("OIL") || clean.includes("POWER")) {
      return stock.sector === "Oil Gas & Consumables" || stock.sector === "Power";
    }
    if (clean.includes("MEDIA")) {
      return stock.sector === "Media & Entertainment";
    }
    if (clean.includes("CHEM")) {
      return stock.sector === "Chemicals";
    }
    if (clean.includes("INFRA") || clean.includes("CAPITAL")) {
      return stock.sector === "Infrastructure" || stock.sector === "Industrial Products";
    }
    return false;
  });

  if (matching.length === 0) {
    // If general or broad market, pick a representative sample deterministically
    const seed = sumChars(clean);
    const count = clean.includes("NEXT") || clean.includes("50") ? 50 : 25;
    const offset = seed % Math.max(1, FNO_208_STOCKS.length - count);
    matching = FNO_208_STOCKS.slice(offset, offset + count);
  }

  const count = matching.length;
  // Generate realistic power-law / market-cap weights descending from largest to smallest
  // e.g. top constituents receive higher index weight, tapering down to smaller constituents
  const rawWeights = matching.map((_, i) => Math.pow(count - i, 1.25));
  const sumRaw = rawWeights.reduce((acc, w) => acc + w, 0);
  const calculatedWeights = rawWeights.map((w) => Number(((w / sumRaw) * 100).toFixed(2)));
  const totalCalc = calculatedWeights.reduce((acc, w) => acc + w, 0);
  calculatedWeights[0] = Number((calculatedWeights[0] + (100 - totalCalc)).toFixed(2));

  return matching.map((stock, idx) => {
    // Add deterministic tick variance based on symbol
    const symSeed = sumChars(stock.symbol + clean);
    const variancePct = Number((((symSeed % 300) - 150) / 100).toFixed(2));
    const finalChange = Number((stock.changePct + variancePct).toFixed(2));
    const finalLtp = Number((stock.ltp * (1 + finalChange / 100)).toFixed(2));

    return {
      symbol: stock.symbol,
      name: stock.name,
      sector: stock.sector,
      weight: calculatedWeights[idx],
      isWeightFallback: true,
      weightingSource: "FALLBACK_EQUAL_WEIGHT",
      changePct: finalChange,
      changeAbs: Number(((finalLtp * finalChange) / 100).toFixed(2)),
      ltp: finalLtp,
      volume: stock.volume || (symSeed * 1420) % 5000000 + 100000,
    };
  });
}

function sumChars(str: string): number {
  let s = 0;
  for (let i = 0; i < str.length; i++) {
    s += str.charCodeAt(i);
  }
  return s;
}
