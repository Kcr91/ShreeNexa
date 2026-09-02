import { describe, expect, it } from "vitest";
import { cancelAllOpenOrders, cancelSingleOrder } from "./panic";
import { ActiveOrderItem } from "./types";

describe("Blotter Panic Cancel and Order Cancellation", () => {
  const sampleOrders: ActiveOrderItem[] = [
    { orderId: "ORD-1", symbol: "RELIANCE", side: "BUY", orderType: "LIMIT", product: "CNC", quantity: 10, filledQuantity: 0, price: 2950, status: "OPEN", placedAt: "09:30:00" },
    { orderId: "ORD-2", symbol: "TCS", side: "SELL", orderType: "LIMIT", product: "MIS", quantity: 20, filledQuantity: 0, price: 4200, status: "PENDING", placedAt: "09:35:00" },
    { orderId: "ORD-3", symbol: "INFY", side: "BUY", orderType: "MARKET", product: "CNC", quantity: 50, filledQuantity: 50, price: 1800, status: "FILLED", placedAt: "09:20:00" },
  ];

  it("cancels all open and pending orders via panic action without affecting filled orders", () => {
    const { updatedOrders, result } = cancelAllOpenOrders(sampleOrders);

    expect(result.canceledCount).toBe(2);
    expect(result.orderIds).toEqual(["ORD-1", "ORD-2"]);

    expect(updatedOrders.find((o) => o.orderId === "ORD-1")?.status).toBe("CANCELLED");
    expect(updatedOrders.find((o) => o.orderId === "ORD-2")?.status).toBe("CANCELLED");
    expect(updatedOrders.find((o) => o.orderId === "ORD-3")?.status).toBe("FILLED");
  });

  it("cancels a single specific working order", () => {
    const updated = cancelSingleOrder(sampleOrders, "ORD-1");
    expect(updated.find((o) => o.orderId === "ORD-1")?.status).toBe("CANCELLED");
    expect(updated.find((o) => o.orderId === "ORD-2")?.status).toBe("PENDING");
  });
});
