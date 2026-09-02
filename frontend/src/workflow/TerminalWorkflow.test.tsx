import { render, screen, fireEvent } from "@testing-library/react";
import React, { useState } from "react";
import { describe, expect, it } from "vitest";
import { TerminalWorkflowEngine } from "./engine";
import { NotificationProvider, useNotifications } from "../notifications/NotificationContext";
import { ToastContainer } from "../notifications/ToastContainer";
import { PositionItem, ActiveOrderItem } from "../blotter/types";

const TerminalWorkflowTestHarness: React.FC = () => {
  const [engine] = useState(() => new TerminalWorkflowEngine("NIFTY 50", 3, 5, 5));
  const [currentLtp, setCurrentLtp] = useState(24500);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [orders, setOrders] = useState<ActiveOrderItem[]>([]);
  const [pnl, setPnl] = useState(0);

  const { sendNotification } = useNotifications();

  const handleInjectTick = (price: number) => {
    setCurrentLtp(price);
    const result = engine.processTick(price);

    setPositions([...result.updatedPositions]);
    setOrders([...engine.orders]);
    setPnl(result.totalUnrealizedPnl);

    if (result.signal === "BUY" && result.generatedOrder) {
      sendNotification({
        title: "Automated Strategy Order Executed",
        message: `BUY 25 NIFTY 50 filled @ ₹${price}`,
        severity: "SUCCESS",
        category: "ORDER_FILL",
      });
    }
  };

  return (
    <div>
      <ToastContainer />
      <div data-testid="current-ltp-display">LTP: {currentLtp}</div>
      <div data-testid="total-pnl-display">PnL: {pnl}</div>

      <button
        type="button"
        onClick={() => {
          // Send descending ticks then sharp upward breakout to trigger Golden Cross
          const ticks = [24500, 24450, 24400, 24350, 24300, 24450, 24600, 24800];
          for (const p of ticks) {
            handleInjectTick(p);
          }
        }}
      >
        Run Synthetic Tick Sequence
      </button>

      {/* Position blotter list */}
      <div data-testid="workflow-positions-table">
        {positions.map((pos) => (
          <div key={pos.symbol} data-testid={`pos-row-${pos.symbol}`}>
            <span>{pos.symbol}</span>
            <span>Qty: {pos.quantity}</span>
            <span>Avg: {pos.buyAvgPrice}</span>
            <span>LTP: {pos.ltp}</span>
            <span>Unrealized: {pos.unrealizedPnl}</span>
          </div>
        ))}
      </div>

      {/* Orders list */}
      <div data-testid="workflow-orders-table">
        {orders.map((ord) => (
          <div key={ord.orderId} data-testid={`ord-row-${ord.orderId}`}>
            <span>{ord.symbol}</span>
            <span>Side: {ord.side}</span>
            <span>Status: {ord.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

describe("End-to-End Terminal Workflow Integration", () => {
  it("processes live ticks, evaluates strategy cross, fills paper order, updates blotter, and notifies user", () => {
    render(
      <NotificationProvider initialSettings={{ enableSound: false }}>
        <TerminalWorkflowTestHarness />
      </NotificationProvider>
    );

    expect(screen.getByTestId("current-ltp-display")).toHaveTextContent("LTP: 24500");

    const runBtn = screen.getByRole("button", { name: "Run Synthetic Tick Sequence" });
    fireEvent.click(runBtn);

    // After tick sequence:
    // 1. LTP should be 24800
    expect(screen.getByTestId("current-ltp-display")).toHaveTextContent("LTP: 24800");

    // 2. Position created in Blotter
    expect(screen.getByTestId("pos-row-NIFTY 50")).toBeInTheDocument();
    expect(screen.getByText("Qty: 25")).toBeInTheDocument();

    // 3. Unrealized PnL positive
    expect(screen.getByTestId("total-pnl-display")).not.toHaveTextContent("PnL: 0");

    // 4. Toast notification dispatched
    expect(screen.getByText("Automated Strategy Order Executed")).toBeInTheDocument();
  });
});
