export type WatchlistColumn =
  | "symbol"
  | "ltp"
  | "changeAbs"
  | "changePct"
  | "volume"
  | "fiftyTwoWeekHigh"
  | "fiftyTwoWeekLow"
  | "fiftyTwoWeek"
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
  { id: "changeAbs", label: "Chg (₹)", minWidth: 70, align: "right" },
  { id: "changePct", label: "Chg %", minWidth: 70, align: "right" },
  { id: "volume", label: "Volume", minWidth: 80, align: "right" },
  { id: "fiftyTwoWeekHigh", label: "52W High", minWidth: 110, align: "right" },
  { id: "fiftyTwoWeekLow", label: "52W Low", minWidth: 110, align: "right" },
  { id: "fiftyTwoWeek", label: "52W H / L", minWidth: 140, align: "right" },
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
  name?: string;
  instrumentType?: string;
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
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
  prevClose?: number;
  open?: number;
  close?: number;
  avgPrice?: number;
  lowerCircuit?: number;
  upperCircuit?: number;
  ltq?: number;
  ltt?: string;
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
