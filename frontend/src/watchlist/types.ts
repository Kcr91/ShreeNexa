export type WatchlistColumn =
  | "symbol"
  | "ltp"
  | "changePct"
  | "changeAbs"
  | "volume"
  | "oi"
  | "oiChangePct"
  | "highLow"
  | "bidAsk";

export interface ColumnConfig {
  id: WatchlistColumn;
  label: string;
  minWidth: number;
  align?: "left" | "right" | "center";
}

export const ALL_COLUMNS: ColumnConfig[] = [
  { id: "symbol", label: "Symbol", minWidth: 100, align: "left" },
  { id: "ltp", label: "LTP (₹)", minWidth: 80, align: "right" },
  { id: "changePct", label: "Chg %", minWidth: 70, align: "right" },
  { id: "changeAbs", label: "Chg (₹)", minWidth: 70, align: "right" },
  { id: "volume", label: "Volume", minWidth: 80, align: "right" },
  { id: "oi", label: "Open Interest", minWidth: 90, align: "right" },
  { id: "oiChangePct", label: "OI Chg %", minWidth: 80, align: "right" },
  { id: "highLow", label: "High / Low", minWidth: 110, align: "right" },
  { id: "bidAsk", label: "Bid / Ask", minWidth: 110, align: "right" },
];

export interface WatchlistItem {
  symbol: string;
  segment: string;
  securityId: string;
  tradingSymbol: string;
  order: number;
  expiry?: string;
  strike?: number;
  optionType?: "CE" | "PE";
  // Live dynamic market fields
  ltp?: number;
  changePct?: number;
  changeAbs?: number;
  volume?: number;
  oi?: number;
  oiChangePct?: number;
  high?: number;
  low?: number;
  bid?: number;
  ask?: number;
  isStale?: boolean;
}

export interface Watchlist {
  id: string;
  name: string;
  description?: string;
  isDefault?: boolean;
  columns: WatchlistColumn[];
  items: WatchlistItem[];
}
