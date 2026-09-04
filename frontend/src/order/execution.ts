import {
  StockOrder,
  MultiLegOptionOrder,
  ExecutionMode,
  OrderValidationResult,
  OrderPlacementResult,
} from "./types";
import { calculateStockMargin, calculateMultiLegOptionMargin } from "./margin";

export function validateStockOrder(
  order: StockOrder,
  availableFunds: number = 500000,
  executionMode: ExecutionMode = "PAPER",
  isLiveApproved: boolean = false
): OrderValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!order.symbol || order.symbol.trim() === "") {
    errors.push("Trading symbol is required.");
  }
  if (order.quantity <= 0 || !Number.isInteger(order.quantity)) {
    errors.push("Order quantity must be a positive integer.");
  }
  if (order.orderType === "LIMIT" && (!order.price || order.price <= 0)) {
    errors.push("Limit price must be greater than zero.");
  }

  // Margin Check
  const margin = calculateStockMargin(order, availableFunds);
  if (!margin.isSufficient) {
    errors.push(
      `Insufficient funds. Required margin ₹${margin.totalRequiredMargin.toLocaleString()} exceeds available balance ₹${availableFunds.toLocaleString()}.`
    );
  }

  // Live Mode Gating Invariant
  if (executionMode === "LIVE") {
    if (!isLiveApproved) {
      errors.push("Live execution locked. Real order placement is strictly gated behind Epic 12 live approval.");
    }
    if (!order.confirmationAcknowledged) {
      errors.push("Live execution requires explicit confirmation acknowledgment.");
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validateOptionOrder(
  order: MultiLegOptionOrder,
  availableFunds: number = 500000,
  executionMode: ExecutionMode = "PAPER",
  isLiveApproved: boolean = false
): OrderValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!order.legs || order.legs.length === 0) {
    errors.push("At least one option leg is required.");
    return { isValid: false, errors, warnings };
  }

  for (let i = 0; i < order.legs.length; i++) {
    const leg = order.legs[i];
    if (leg.quantity <= 0 || !Number.isInteger(leg.quantity)) {
      errors.push(`Leg ${i + 1} (${leg.strike} ${leg.optionType}): quantity must be a positive integer.`);
    }
    if (leg.strike <= 0) {
      errors.push(`Leg ${i + 1}: strike price must be greater than zero.`);
    }
    if (leg.premium < 0) {
      errors.push(`Leg ${i + 1}: premium cannot be negative.`);
    }
  }

  // Multi-Leg Margin Check
  const margin = calculateMultiLegOptionMargin(order.legs, availableFunds);
  if (!margin.isSufficient) {
    errors.push(
      `Insufficient funds. Required margin ₹${margin.totalRequiredMargin.toLocaleString()} exceeds available balance ₹${availableFunds.toLocaleString()}.`
    );
  }

  // Live Mode Gating Invariant
  if (executionMode === "LIVE") {
    if (!isLiveApproved) {
      errors.push("Live execution locked. Real order placement is strictly gated behind Epic 12 live approval.");
    }
    if (!order.confirmationAcknowledged) {
      errors.push("Live execution requires explicit confirmation acknowledgment.");
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

const KNOWN_SECURITIES: Record<string, string> = {
  RELIANCE: "2885",
  TCS: "11536",
  INFY: "1594",
  HDFCBANK: "1333",
  ICICIBANK: "4963",
  SBIN: "3045",
  NIFTY: "13",
  BANKNIFTY: "25",
};

export async function placeOrder(
  order: StockOrder | MultiLegOptionOrder,
  availableFunds: number = 500000,
  executionMode: ExecutionMode = "PAPER",
  isLiveApproved: boolean = false,
  uncertainOrders?: Set<string>
): Promise<OrderPlacementResult> {
  if (order.correlationId && uncertainOrders?.has(order.correlationId)) {
    return {
      success: false,
      executionMode,
      isUncertain: true,
      message: `Order '${order.correlationId}' is in uncertain state (PENDING_BROKER_CONFIRMATION). Blind retry is blocked.`,
    };
  }

  const isStock = "price" in order;
  const validation = isStock
    ? validateStockOrder(order as StockOrder, availableFunds, executionMode, isLiveApproved)
    : validateOptionOrder(order as MultiLegOptionOrder, availableFunds, executionMode, isLiveApproved);

  if (!validation.isValid) {
    return {
      success: false,
      executionMode,
      message: validation.errors.join(" | "),
    };
  }

  const symbol = isStock ? (order as StockOrder).symbol : (order as MultiLegOptionOrder).strategyName;
  const securityId = (isStock && (order as StockOrder).securityId) || KNOWN_SECURITIES[symbol] || symbol;
  const transactionType = isStock ? (order as StockOrder).side : "BUY";
  const orderType = isStock ? (order as StockOrder).orderType : "LIMIT";
  const rawProduct = order.productType;
  const productType = rawProduct === "MIS" ? "INTRADAY" : rawProduct === "NRML" ? "MARGIN" : rawProduct;
  const quantity = isStock ? (order as StockOrder).quantity : 1;
  const price = isStock ? (order as StockOrder).price : 0;

  const payload = {
    mode: executionMode,
    confirmation_acknowledged: Boolean(order.confirmationAcknowledged),
    symbol,
    security_id: String(securityId),
    exchange_segment: "NSE_EQ",
    transaction_type: transactionType,
    order_type: orderType,
    product_type: productType,
    quantity,
    price,
    trigger_price: null,
    correlation_id: order.correlationId || null,
  };

  try {
    const res = await fetch("/api/v1/orders/ticket/place", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      const detail = errorData.detail || `Order placement failed with HTTP ${res.status}`;
      const isUncertain = res.status === 504 || (typeof detail === "string" && detail.includes("PENDING_BROKER_CONFIRMATION"));
      return {
        success: false,
        executionMode,
        isUncertain,
        message: detail,
      };
    }

    const data = await res.json();
    return {
      success: data.success ?? true,
      orderId: data.order_id,
      executionMode,
      message: data.message || `${executionMode} order ${data.order_id} placed successfully.`,
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "connection failed";
    return {
      success: false,
      executionMode,
      message: `Network error placing order: ${msg}`,
    };
  }
}
