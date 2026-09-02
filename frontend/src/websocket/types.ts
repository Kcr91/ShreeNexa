export type WebSocketState = "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "RECONNECTING" | "ERROR";

export type FeedChannel = "quotes" | "depth" | "orders" | "positions" | "pnl";

export interface TickData {
  symbol: string;
  ltp: number;
  change: number;
  changePct: number;
  volume: number;
  timestamp: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
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
