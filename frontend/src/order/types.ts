export type AssetClass = "EQUITY" | "OPTION" | "FUTURE";
export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT" | "STOP_LOSS";
export type ProductType = "CNC" | "MIS" | "NRML";
export type OptionType = "CE" | "PE";
export type ExecutionMode = "PAPER" | "LIVE";

export interface StockOrder {
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  productType: ProductType;
  quantity: number;
  price: number;
  correlationId?: string;
  confirmationAcknowledged?: boolean;
}

export interface OptionLeg {
  id: string;
  symbol: string;
  expiry: string;
  strike: number;
  optionType: OptionType;
  side: OrderSide;
  quantity: number;
  premium: number;
}

export interface MultiLegOptionOrder {
  strategyName: string;
  productType: ProductType;
  legs: OptionLeg[];
  correlationId?: string;
  confirmationAcknowledged?: boolean;
}

export interface MarginRequirement {
  initialMargin: number;
  exposureMargin: number;
  premiumPayable: number;
  premiumReceivable: number;
  hedgingBenefit: number;
  totalRequiredMargin: number;
  estimatedCosts: number;
  availableFunds: number;
  isSufficient: boolean;
}

export interface OrderValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface OrderPlacementResult {
  success: boolean;
  orderId?: string;
  executionMode: ExecutionMode;
  isUncertain?: boolean;
  message: string;
}

export interface OrderTicketSettings {
  defaultAssetClass: "EQUITY" | "OPTION";
  defaultSymbol: string;
  defaultQuantity: number;
}
