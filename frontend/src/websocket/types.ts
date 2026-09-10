export type WebSocketState = "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "RECONNECTING" | "ERROR";

export type FeedChannel = "quotes" | "depth" | "orders" | "positions" | "pnl" | "oi";

export interface TickData {
  symbol: string;
  ltp: number;
  change?: number;
  changePct?: number;
  volume?: number;
  timestamp: number;
  sourceTimestamp?: number | string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  previousClose?: number;
  marketState?: "LIVE" | "MARKET_CLOSED" | "STALE" | "UNAVAILABLE" | "ERROR";
  source?: "DHAN_WEBSOCKET" | "DHAN_REST";
  isStale?: boolean;
}

export interface InstrumentSubscription {
  segment: string;
  securityId: string;
  symbol?: string;
}

export interface OrderUpdateMessage {
  orderId: string;
  symbol: string;
  side: "BUY" | "SELL";
  status: "PENDING" | "FILLED" | "CANCELLED" | "REJECTED";
  filledQuantity: number;
  averagePrice: number;
  timestamp: number;
}

export interface PositionUpdateMessage {
  symbol: string;
  quantity: number;
  buyAvgPrice: number;
  currentLtp: number;
  unrealizedPnl: number;
  timestamp: number;
}

export interface ClientSubscribeMessage {
  action: "subscribe" | "unsubscribe";
  channels: FeedChannel[];
  symbols?: string[];
}

export interface WebSocketClientOptions {
  url?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelayMs?: number;
  heartbeatIntervalMs?: number;
  mockFeedEnabled?: boolean;
}

export interface LiveFeedWidgetSettings {
  showTickStream: boolean;
  maxStreamHistory: number;
}
