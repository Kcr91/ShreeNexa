import { ActiveOrderItem, PanicCancelResult } from "./types";

export function cancelAllOpenOrders(orders: ActiveOrderItem[]): {
  updatedOrders: ActiveOrderItem[];
  result: PanicCancelResult;
} {
  const canceledOrderIds: string[] = [];

  const updatedOrders = orders.map((order) => {
    if (order.status === "OPEN" || order.status === "PENDING") {
      canceledOrderIds.push(order.orderId);
      return { ...order, status: "CANCELLED" as const };
    }
    return order;
  });

  return {
    updatedOrders,
    result: {
      canceledCount: canceledOrderIds.length,
      orderIds: canceledOrderIds,
      timestamp: new Date().toISOString(),
    },
  };
}

export function cancelSingleOrder(orders: ActiveOrderItem[], orderId: string): ActiveOrderItem[] {
  return orders.map((order) => {
    if (order.orderId === orderId && (order.status === "OPEN" || order.status === "PENDING")) {
      return { ...order, status: "CANCELLED" as const };
    }
    return order;
  });
}
