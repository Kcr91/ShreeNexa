export interface SectorIndexCatalogItem {
  index_name: string;
  sector: string;
  description: string;
}

export interface IndexConstituentItem {
  symbol: string;
  weight: number | null;
  sector: string | null;
  valid_from: string;
  valid_to: string | null;
  source: string;
  source_date: string;
  // Live dynamic market fields
  ltp?: number;
  changePct?: number;
  volume?: number;
}

export interface IndexDrillInResponse {
  index_name: string;
  as_of: string | null;
  total_constituents: number;
  has_fallback: boolean;
  provenance_sources: string[];
  sector_weights: Record<string, number>;
  constituents: IndexConstituentItem[];
}
