import { SectorIndexCatalogItem, IndexDrillInResponse } from "./types";

export const DEFAULT_SECTOR_CATALOG: SectorIndexCatalogItem[] = [
  { index_name: "NIFTY 50", sector: "Diversified Large Cap", description: "Flagship 50 Indian blue chip companies" },
  { index_name: "NIFTY BANK", sector: "Banking", description: "12 most liquid Indian banking stocks" },
  { index_name: "NIFTY IT", sector: "Information Technology", description: "Top Indian IT software and services companies" },
  { index_name: "NIFTY AUTO", sector: "Automotive", description: "Automobile OEMs and auto ancillaries" },
  { index_name: "NIFTY PHARMA", sector: "Pharmaceuticals", description: "Pharmaceuticals and healthcare companies" },
  { index_name: "NIFTY FMCG", sector: "FMCG", description: "Fast Moving Consumer Goods manufacturers" },
  { index_name: "NIFTY METAL", sector: "Metals & Mining", description: "Steel, aluminum, and mining producers" },
  { index_name: "NIFTY ENERGY", sector: "Energy", description: "Petroleum, gas, power utilities, and renewables" },
  { index_name: "NIFTY REALTY", sector: "Real Estate", description: "Real estate developers and infrastructure" },
];

export async function fetchSectorCatalog(): Promise<SectorIndexCatalogItem[]> {
  try {
    const res = await fetch("/api/v1/indices/sectors/catalog");
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Fall back to default catalog
  }
  return DEFAULT_SECTOR_CATALOG;
}

export async function fetchIndexDrillIn(
  indexName: string,
  asOf?: string
): Promise<IndexDrillInResponse> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  try {
    const res = await fetch(`/api/v1/indices/${encodeURIComponent(indexName)}/drill-in${query}`);
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Fall back to offline seed
  }

  // Realistic offline seed data
  const isFallback = true;
  const constituents = getMockConstituents(indexName);
  const sectorWeights: Record<string, number> = {};

  constituents.forEach((c) => {
    const sec = c.sector || "Unclassified";
    sectorWeights[sec] = Number(((sectorWeights[sec] || 0) + (c.weight || 0)).toFixed(2));
  });

  return {
    index_name: indexName,
    as_of: asOf || null,
    total_constituents: constituents.length,
    has_fallback: isFallback,
    provenance_sources: ["fallback"],
    sector_weights: sectorWeights,
    constituents,
  };
}

function getMockConstituents(indexName: string) {
  if (indexName === "NIFTY IT") {
    return [
      {
        symbol: "TCS",
        weight: 28.5,
        sector: "Information Technology",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 4210.0,
        changePct: -0.45,
        volume: 1850000,
      },
      {
        symbol: "INFY",
        weight: 26.2,
        sector: "Information Technology",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 1890.1,
        changePct: -1.1,
        volume: 3100000,
      },
      {
        symbol: "HCLTECH",
        weight: 12.8,
        sector: "Information Technology",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 1780.4,
        changePct: 0.75,
        volume: 1400000,
      },
      {
        symbol: "WIPRO",
        weight: 8.5,
        sector: "Information Technology",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 540.2,
        changePct: 0.35,
        volume: 2200000,
      },
    ];
  }

  if (indexName === "NIFTY BANK") {
    return [
      {
        symbol: "HDFCBANK",
        weight: 29.4,
        sector: "Banking",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 1640.2,
        changePct: 0.8,
        volume: 6800000,
      },
      {
        symbol: "ICICIBANK",
        weight: 24.1,
        sector: "Banking",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 1215.3,
        changePct: 1.65,
        volume: 5400000,
      },
      {
        symbol: "SBIN",
        weight: 11.2,
        sector: "Banking",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 815.4,
        changePct: 1.15,
        volume: 7600000,
      },
      {
        symbol: "AXISBANK",
        weight: 10.5,
        sector: "Banking",
        valid_from: "2024-01-01",
        valid_to: null,
        source: "fallback",
        source_date: "2024-01-01",
        ltp: 1180.0,
        changePct: -0.25,
        volume: 3800000,
      },
    ];
  }

  // Default NIFTY 50
  return [
    {
      symbol: "RELIANCE",
      weight: 9.8,
      sector: "Energy",
      valid_from: "2024-01-01",
      valid_to: null,
      source: "fallback",
      source_date: "2024-01-01",
      ltp: 2980.5,
      changePct: 1.25,
      volume: 4250000,
    },
    {
      symbol: "HDFCBANK",
      weight: 8.5,
      sector: "Banking",
      valid_from: "2024-01-01",
      valid_to: null,
      source: "fallback",
      source_date: "2024-01-01",
      ltp: 1640.2,
      changePct: 0.8,
      volume: 6800000,
    },
    {
      symbol: "ICICIBANK",
      weight: 7.9,
      sector: "Banking",
      valid_from: "2024-01-01",
      valid_to: null,
      source: "fallback",
      source_date: "2024-01-01",
      ltp: 1215.3,
      changePct: 1.65,
      volume: 5400000,
    },
    {
      symbol: "INFY",
      weight: 5.6,
      sector: "Information Technology",
      valid_from: "2024-01-01",
      valid_to: null,
      source: "fallback",
      source_date: "2024-01-01",
      ltp: 1890.1,
      changePct: -1.1,
      volume: 3100000,
    },
    {
      symbol: "TCS",
      weight: 4.2,
      sector: "Information Technology",
      valid_from: "2024-01-01",
      valid_to: null,
      source: "fallback",
      source_date: "2024-01-01",
      ltp: 4210.0,
      changePct: -0.45,
      volume: 1850000,
    },
  ];
}
