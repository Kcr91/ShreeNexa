export type BlotterTab = "POSITIONS" | "OPEN_ORDERS" | "TRADE_LOG";
export type ProductType = "CNC" | "MIS" | "NRML";
export type OrderSide = "BUY" | "SELL";
export type OrderType = "LIMIT" | "MARKET" | "STOP_LOSS";
export type OrderStatus = "OPEN" | "PENDING" | "CANCELLED" | "FILLED";

export interface PositionItem {
  symbol: string;
  product: ProductType;
  quantity: number;
  buyAvgPrice: number;
  ltp: number;
  dayChange: number;
  dayChangePct: number;
  unrealizedPnl: number;
  realizedPnl: number;
  totalPnl: number;
}

export interface ActiveOrderItem {
  orderId: string;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  product: ProductType;
  quantity: number;
  filledQuantity: number;
  price: number;
  status: OrderStatus;
  placedAt: string;
}

export interface TradeLogItem {
  tradeId: string;
  orderId: string;
  symbol: string;
  side: OrderSide;
  product: ProductType;
  quantity: number;
  executionPrice: number;
  executionTime: string;
}

export interface PortfolioSummary {
  totalInvested: number;
  totalUnrealizedPnl: number;
  totalRealizedPnl: number;
  netPnl: number;
  openPositionsCount: number;
  activeOrdersCount: number;
}

export interface PanicCancelResult {
  canceledCount: number;
  orderIds: string[];
  timestamp: string;
}

export interface BlotterWidgetSettings {
  defaultTab: BlotterTab;
  refreshIntervalMs: number;
  showRealizedPnl: boolean;
}
