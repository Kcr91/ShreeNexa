import { describe, expect, it } from "vitest";
import { validateStockOrder, validateOptionOrder, placeOrder } from "./execution";
import { StockOrder, MultiLegOptionOrder } from "./types";

describe("Order Execution and Safety Gate Validation", () => {
  const validStockOrder: StockOrder = {
    symbol: "RELIANCE",
    side: "BUY",
    orderType: "LIMIT",
    productType: "CNC",
    quantity: 10,
    price: 3000,
  };

  it("validates and accepts a normal paper stock order within margin limits", () => {
    const res = validateStockOrder(validStockOrder, 500000, "PAPER", false);
    expect(res.isValid).toBe(true);
    expect(res.errors).toHaveLength(0);

    const placement = placeOrder(validStockOrder, 500000, "PAPER", false);
    expect(placement.success).toBe(true);
    expect(placement.orderId).toBeDefined();
    expect(placement.executionMode).toBe("PAPER");
  });

  it("rejects order exceeding available margin balance", () => {
    const hugeOrder: StockOrder = { ...validStockOrder, quantity: 10000, price: 3000 }; // 30,000,000
    const res = validateStockOrder(hugeOrder, 100000, "PAPER", false);

    expect(res.isValid).toBe(false);
    expect(res.errors[0]).toContain("Insufficient funds");
  });

  it("strictly blocks live execution without explicit live authorization gate", () => {
    // Attempting LIVE order when isLiveApproved is false
    const res = validateStockOrder(validStockOrder, 500000, "LIVE", false);

    expect(res.isValid).toBe(false);
    expect(res.errors[0]).toContain("Live execution locked");

    const placement = placeOrder(validStockOrder, 500000, "LIVE", false);
    expect(placement.success).toBe(false);
    expect(placement.message).toContain("Live execution locked");
  });

  it("validates multi-leg option orders and requires valid legs", () => {
    const invalidOptionOrder: MultiLegOptionOrder = {
      strategyName: "Empty Strategy",
      productType: "NRML",
      legs: [],
    };
    const res = validateOptionOrder(invalidOptionOrder, 500000, "PAPER", false);
    expect(res.isValid).toBe(false);
    expect(res.errors[0]).toContain("At least one option leg is required");
  });
});
