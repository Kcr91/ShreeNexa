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
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function placeOrder(
  order: StockOrder | MultiLegOptionOrder,
  availableFunds: number = 500000,
  executionMode: ExecutionMode = "PAPER",
  isLiveApproved: boolean = false
): OrderPlacementResult {
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

  const orderId = `ORD-${Date.now()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;

  return {
    success: true,
    orderId,
    executionMode,
    message: `${executionMode} order ${orderId} submitted successfully to SimBroker engine.`,
  };
}
