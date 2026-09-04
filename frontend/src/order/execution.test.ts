import { describe, expect, it, vi } from "vitest";
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

  it("validates and accepts a normal paper stock order within margin limits", async () => {
    const res = validateStockOrder(validStockOrder, 500000, "PAPER", false);
    expect(res.isValid).toBe(true);
    expect(res.errors).toHaveLength(0);

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        mode: "PAPER",
        order_id: "ORD-PAPER-TEST-123",
        correlation_id: "TICKET-2885",
        order_status: "PENDING",
        message: "Paper order ORD-PAPER-TEST-123 submitted successfully to SimBroker engine.",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const placement = await placeOrder(validStockOrder, 500000, "PAPER", false);
    expect(placement.success).toBe(true);
    expect(placement.orderId).toBe("ORD-PAPER-TEST-123");
    expect(placement.executionMode).toBe("PAPER");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/orders/ticket/place",
      expect.objectContaining({
        method: "POST",
      })
    );

    vi.unstubAllGlobals();
  });

  it("rejects order exceeding available margin balance", () => {
    const hugeOrder: StockOrder = { ...validStockOrder, quantity: 10000, price: 3000 }; // 30,000,000
    const res = validateStockOrder(hugeOrder, 100000, "PAPER", false);

    expect(res.isValid).toBe(false);
    expect(res.errors[0]).toContain("Insufficient funds");
  });

  it("strictly blocks live execution without explicit live authorization gate", async () => {
    // Attempting LIVE order when isLiveApproved is false
    const res = validateStockOrder(validStockOrder, 500000, "LIVE", false);

    expect(res.isValid).toBe(false);
    expect(res.errors[0]).toContain("Live execution locked");

    const placement = await placeOrder(validStockOrder, 500000, "LIVE", false);
    expect(placement.success).toBe(false);
    expect(placement.message).toContain("Live execution locked");
  });

  it("strictly blocks live execution without explicit confirmation acknowledgment", () => {
    const unconfirmedLiveOrder: StockOrder = {
      ...validStockOrder,
      confirmationAcknowledged: false,
    };
    const res = validateStockOrder(unconfirmedLiveOrder, 500000, "LIVE", true);
    expect(res.isValid).toBe(false);
    expect(res.errors).toContain("Live execution requires explicit confirmation acknowledgment.");
  });

  it("blocks blind retry when order is in uncertain status", async () => {
    const uncertainSet = new Set(["UNCERTAIN-CORR-01"]);
    const retryOrder: StockOrder = {
      ...validStockOrder,
      correlationId: "UNCERTAIN-CORR-01",
    };

    const placement = await placeOrder(retryOrder, 500000, "PAPER", false, uncertainSet);
    expect(placement.success).toBe(false);
    expect(placement.isUncertain).toBe(true);
    expect(placement.message).toContain("PENDING_BROKER_CONFIRMATION");
    expect(placement.message).toContain("Blind retry is blocked");
  });

  it("handles backend 504 gateway timeout as uncertain order blocking retry", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 504,
      json: async () => ({
        detail: "Broker transport timed out. Status is PENDING_BROKER_CONFIRMATION.",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const placement = await placeOrder(validStockOrder, 500000, "PAPER", false);
    expect(placement.success).toBe(false);
    expect(placement.isUncertain).toBe(true);
    expect(placement.message).toContain("PENDING_BROKER_CONFIRMATION");

    vi.unstubAllGlobals();
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
