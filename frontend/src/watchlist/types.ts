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
  sortable?: boolean;
}

export const ALL_COLUMNS: ColumnConfig[] = [
  { id: "symbol", label: "Symbol", minWidth: 100, align: "left", sortable: true },
  { id: "ltp", label: "LTP (₹)", minWidth: 80, align: "right", sortable: true },
  { id: "changeAbs", label: "Chg (₹)", minWidth: 70, align: "right", sortable: true },
  { id: "changePct", label: "Chg %", minWidth: 70, align: "right", sortable: true },
  { id: "volume", label: "Volume", minWidth: 80, align: "right", sortable: true },
  { id: "fiftyTwoWeekHigh", label: "52W High", minWidth: 110, align: "right", sortable: true },
  { id: "fiftyTwoWeekLow", label: "52W Low", minWidth: 110, align: "right", sortable: true },
  { id: "fiftyTwoWeek", label: "52W H / L", minWidth: 140, align: "right", sortable: false },
  { id: "oi", label: "Open Interest", minWidth: 90, align: "right", sortable: true },
  { id: "oiChangePct", label: "OI Chg %", minWidth: 80, align: "right", sortable: true },
  { id: "highLow", label: "High / Low", minWidth: 110, align: "right", sortable: false },
  { id: "bidAsk", label: "Bid / Ask", minWidth: 110, align: "right", sortable: false },
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
  sector?: string;
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
  marketDataState?: "LIVE" | "MARKET_CLOSED" | "STALE" | "UNAVAILABLE" | "ERROR";
  marketDataSource?: "DHAN_WEBSOCKET" | "DHAN_REST";
  marketDataReceivedAt?: number;
  marketDataError?: string;
}

export interface Watchlist {
  id: string;
  name: string;
  description?: string;
  isDefault?: boolean;
  isGroupedBySector?: boolean;
  columns: WatchlistColumn[];
  items: WatchlistItem[];
}
