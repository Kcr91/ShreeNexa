import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  BlotterTab,
  PositionItem,
  ActiveOrderItem,
  TradeLogItem,
  BlotterWidgetSettings,
} from "../../blotter/types";
import { computePortfolioSummary } from "../../blotter/pnl";
import { cancelAllOpenOrders, cancelSingleOrder } from "../../blotter/panic";

export const BlotterWidget: React.FC<WidgetComponentProps<BlotterWidgetSettings>> = ({
  settings,
}) => {
  const [activeTab, setActiveTab] = useState<BlotterTab>(settings.defaultTab || "POSITIONS");

  // Mock initial positions
  const [positions, setPositions] = useState<PositionItem[]>([
    {
      symbol: "RELIANCE",
      product: "CNC",
      quantity: 50,
      buyAvgPrice: 2920.0,
      ltp: 2955.5,
      dayChange: 35.5,
      dayChangePct: 1.22,
      unrealizedPnl: 1775.0,
      realizedPnl: 450.0,
      totalPnl: 2225.0,
    },
    {
      symbol: "NIFTY 24500 CE",
      product: "NRML",
      quantity: -50,
      buyAvgPrice: 160.0,
      ltp: 142.5,
      dayChange: -17.5,
      dayChangePct: -10.94,
      unrealizedPnl: 875.0,
      realizedPnl: 0.0,
      totalPnl: 875.0,
    },
    {
      symbol: "TCS",
      product: "MIS",
      quantity: 25,
      buyAvgPrice: 4220.0,
      ltp: 4195.0,
      dayChange: -25.0,
      dayChangePct: -0.59,
      unrealizedPnl: -625.0,
      realizedPnl: 120.0,
      totalPnl: -505.0,
    },
  ]);

  // Mock working orders
  const [orders, setOrders] = useState<ActiveOrderItem[]>([
    {
      orderId: "ORD-90211",
      symbol: "INFY",
      side: "BUY",
      orderType: "LIMIT",
      product: "CNC",
      quantity: 100,
      filledQuantity: 0,
      price: 1820.0,
      status: "OPEN",
      placedAt: "09:32:15",
    },
    {
      orderId: "ORD-90212",
      symbol: "HDFCBANK",
      side: "BUY",
      orderType: "LIMIT",
      product: "MIS",
      quantity: 50,
      filledQuantity: 0,
      price: 1640.0,
      status: "PENDING",
      placedAt: "09:45:02",
    },
  ]);

  // Mock trade executions
  const [trades, setTrades] = useState<TradeLogItem[]>([
    {
      tradeId: "TRD-1001",
      orderId: "ORD-90100",
      symbol: "RELIANCE",
      side: "BUY",
      product: "CNC",
      quantity: 50,
      executionPrice: 2920.0,
      executionTime: "09:16:30",
    },
    {
      tradeId: "TRD-1002",
      orderId: "ORD-90101",
      symbol: "NIFTY 24500 CE",
      side: "SELL",
      product: "NRML",
      quantity: 50,
      executionPrice: 160.0,
      executionTime: "09:22:10",
    },
  ]);

  const [panicNotification, setPanicNotification] = useState<string | null>(null);

  const openOrdersCount = useMemo(
    () => orders.filter((o) => o.status === "OPEN" || o.status === "PENDING").length,
    [orders]
  );

  const summary = useMemo(() => {
    return computePortfolioSummary(positions, openOrdersCount);
  }, [positions, openOrdersCount]);

  const handlePanicCancelAll = () => {
    const { updatedOrders, result } = cancelAllOpenOrders(orders);
    setOrders(updatedOrders);
    setPanicNotification(`Panic action executed: ${result.canceledCount} open orders canceled.`);
  };

  const handleCancelSingle = (orderId: string) => {
    setOrders((prev) => cancelSingleOrder(prev, orderId));
  };

  const handleSquareOffPosition = (symbol: string) => {
    // Add trade log entry for square off and close position
    const pos = positions.find((p) => p.symbol === symbol);
    if (!pos || pos.quantity === 0) return;

    const newTrade: TradeLogItem = {
      tradeId: `TRD-${Date.now().toString().slice(-4)}`,
      orderId: `ORD-${Date.now().toString().slice(-5)}`,
      symbol: pos.symbol,
      side: pos.quantity > 0 ? "SELL" : "BUY",
      product: pos.product,
      quantity: Math.abs(pos.quantity),
      executionPrice: pos.ltp,
      executionTime: new Date().toLocaleTimeString(),
    };

    setTrades([newTrade, ...trades]);
    setPositions(
      positions.map((p) =>
        p.symbol === symbol
          ? {
              ...p,
              quantity: 0,
              realizedPnl: p.realizedPnl + p.unrealizedPnl,
              unrealizedPnl: 0,
              totalPnl: p.realizedPnl + p.unrealizedPnl,
            }
          : p
      )
    );
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Portfolio Summary & Panic Trigger */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", gap: "var(--spacing-4)", fontSize: "var(--font-size-xs)" }}>
          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Unrealized:</span>
            <strong
              style={{
                fontFamily: "var(--font-family-mono)",
                color: summary.totalUnrealizedPnl >= 0 ? "var(--color-up)" : "var(--color-down)",
              }}
            >
              {summary.totalUnrealizedPnl >= 0 ? "+" : ""}₹{summary.totalUnrealizedPnl.toLocaleString()}
            </strong>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Realized:</span>
            <strong
              style={{
                fontFamily: "var(--font-family-mono)",
                color: summary.totalRealizedPnl >= 0 ? "var(--color-up)" : "var(--color-down)",
              }}
            >
              {summary.totalRealizedPnl >= 0 ? "+" : ""}₹{summary.totalRealizedPnl.toLocaleString()}
            </strong>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Net Day PnL:</span>
            <strong
              style={{
                fontFamily: "var(--font-family-mono)",
                color: summary.netPnl >= 0 ? "var(--color-up)" : "var(--color-down)",
              }}
            >
              {summary.netPnl >= 0 ? "+" : ""}₹{summary.netPnl.toLocaleString()}
            </strong>
          </div>
        </div>

        {/* Panic Button */}
        <button
          type="button"
          onClick={handlePanicCancelAll}
          aria-label="Cancel All Open Orders"
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "var(--color-down)",
            color: "var(--text-inverse)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.6875rem",
            fontWeight: "bold",
            cursor: "pointer",
          }}
        >
          ⚠️ CANCEL ALL ({openOrdersCount})
        </button>
      </div>

      {/* Panic Notification Alert */}
      {panicNotification && (
        <div
          role="alert"
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "var(--color-down-bg)",
            color: "var(--color-down)",
            fontSize: "var(--font-size-xs)",
            borderRadius: "var(--radius-sm)",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>{panicNotification}</span>
          <button
            type="button"
            onClick={() => setPanicNotification(null)}
            style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Blotter Navigation Tabs */}
      <div style={{ display: "flex", gap: "var(--spacing-1)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
        <button
          type="button"
          data-testid="blotter-tab-positions"
          onClick={() => setActiveTab("POSITIONS")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "POSITIONS" ? "var(--bg-active)" : "transparent",
            color: activeTab === "POSITIONS" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Positions ({positions.length})
        </button>
        <button
          type="button"
          data-testid="blotter-tab-open-orders"
          onClick={() => setActiveTab("OPEN_ORDERS")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "OPEN_ORDERS" ? "var(--bg-active)" : "transparent",
            color: activeTab === "OPEN_ORDERS" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Open Orders ({openOrdersCount})
        </button>
        <button
          type="button"
          data-testid="blotter-tab-trade-log"
          onClick={() => setActiveTab("TRADE_LOG")}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: activeTab === "TRADE_LOG" ? "var(--bg-active)" : "transparent",
            color: activeTab === "TRADE_LOG" ? "var(--color-primary)" : "var(--text-muted)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Trade Log ({trades.length})
        </button>
      </div>

      {/* Main Table Area */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {activeTab === "POSITIONS" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-xs)" }}>
            <thead>
              <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "4px" }}>Symbol</th>
                <th style={{ padding: "4px" }}>Product</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Avg Price</th>
                <th style={{ padding: "4px", textAlign: "right" }}>LTP</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Unrealized PnL</th>
                <th style={{ padding: "4px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => (
                <tr
                  key={`${pos.symbol}-${pos.product}`}
                  data-testid={`position-row-${pos.symbol}`}
                  style={{ borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <td style={{ padding: "6px 4px", fontWeight: 600 }}>{pos.symbol}</td>
                  <td style={{ padding: "6px 4px", color: "var(--text-muted)" }}>{pos.product}</td>
                  <td
                    style={{
                      padding: "6px 4px",
                      textAlign: "right",
                      fontFamily: "var(--font-family-mono)",
                      color: pos.quantity > 0 ? "var(--color-up)" : pos.quantity < 0 ? "var(--color-down)" : "var(--text-muted)",
                    }}
                  >
                    {pos.quantity}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{pos.buyAvgPrice.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{pos.ltp.toFixed(2)}
                  </td>
                  <td
                    style={{
                      padding: "6px 4px",
                      textAlign: "right",
                      fontFamily: "var(--font-family-mono)",
                      fontWeight: 600,
                      color: pos.unrealizedPnl >= 0 ? "var(--color-up)" : "var(--color-down)",
                    }}
                  >
                    {pos.unrealizedPnl >= 0 ? "+" : ""}₹{pos.unrealizedPnl.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "center" }}>
                    {pos.quantity !== 0 && (
                      <button
                        type="button"
                        onClick={() => handleSquareOffPosition(pos.symbol)}
                        style={{
                          fontSize: "0.625rem",
                          padding: "1px 6px",
                          backgroundColor: "var(--bg-active)",
                          border: "1px solid var(--border-default)",
                          color: "var(--text-primary)",
                          borderRadius: "var(--radius-sm)",
                          cursor: "pointer",
                        }}
                      >
                        Exit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === "OPEN_ORDERS" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-xs)" }}>
            <thead>
              <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "4px" }}>Order ID</th>
                <th style={{ padding: "4px" }}>Symbol</th>
                <th style={{ padding: "4px" }}>Side</th>
                <th style={{ padding: "4px" }}>Type</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Price</th>
                <th style={{ padding: "4px" }}>Status</th>
                <th style={{ padding: "4px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr
                  key={order.orderId}
                  data-testid={`order-row-${order.orderId}`}
                  style={{ borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <td style={{ padding: "6px 4px", fontFamily: "var(--font-family-mono)", color: "var(--text-muted)" }}>
                    {order.orderId}
                  </td>
                  <td style={{ padding: "6px 4px", fontWeight: 600 }}>{order.symbol}</td>
                  <td style={{ padding: "6px 4px", fontWeight: 600, color: order.side === "BUY" ? "var(--color-up)" : "var(--color-down)" }}>
                    {order.side}
                  </td>
                  <td style={{ padding: "6px 4px", color: "var(--text-muted)" }}>{order.orderType}</td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {order.filledQuantity}/{order.quantity}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{order.price.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px 4px" }}>
                    <span
                      style={{
                        padding: "1px 4px",
                        borderRadius: "2px",
                        fontSize: "0.625rem",
                        backgroundColor:
                          order.status === "OPEN"
                            ? "var(--color-primary-bg)"
                            : order.status === "CANCELLED"
                            ? "var(--color-down-bg)"
                            : "var(--bg-active)",
                        color:
                          order.status === "OPEN"
                            ? "var(--color-primary)"
                            : order.status === "CANCELLED"
                            ? "var(--color-down)"
                            : "var(--text-muted)",
                      }}
                    >
                      {order.status}
                    </span>
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "center" }}>
                    {(order.status === "OPEN" || order.status === "PENDING") && (
                      <button
                        type="button"
                        onClick={() => handleCancelSingle(order.orderId)}
                        aria-label={`Cancel ${order.orderId}`}
                        style={{
                          fontSize: "0.625rem",
                          padding: "1px 6px",
                          backgroundColor: "transparent",
                          border: "1px solid var(--color-down)",
                          color: "var(--color-down)",
                          borderRadius: "var(--radius-sm)",
                          cursor: "pointer",
                        }}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === "TRADE_LOG" && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-xs)" }}>
            <thead>
              <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "4px" }}>Trade ID</th>
                <th style={{ padding: "4px" }}>Time</th>
                <th style={{ padding: "4px" }}>Symbol</th>
                <th style={{ padding: "4px" }}>Side</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Exec Price</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Trade Value</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trd) => (
                <tr key={trd.tradeId} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "6px 4px", fontFamily: "var(--font-family-mono)", color: "var(--text-muted)" }}>
                    {trd.tradeId}
                  </td>
                  <td style={{ padding: "6px 4px", color: "var(--text-muted)" }}>{trd.executionTime}</td>
                  <td style={{ padding: "6px 4px", fontWeight: 600 }}>{trd.symbol}</td>
                  <td style={{ padding: "6px 4px", fontWeight: 600, color: trd.side === "BUY" ? "var(--color-up)" : "var(--color-down)" }}>
                    {trd.side}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {trd.quantity}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{trd.executionPrice.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{(trd.quantity * trd.executionPrice).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export const blotterDefinition: WidgetDefinition<BlotterWidgetSettings> = {
  id: "blotter",
  title: "Positions & Orders Blotter",
  description: "Real-time mark-to-market positions, working orders, trade log, and panic cancel button.",
  category: "order",
  icon: "📑",
  defaultWidth: 500,
  defaultHeight: 380,
  schema: {
    fields: [
      {
        name: "defaultTab",
        label: "Default Active Tab",
        type: "select",
        default: "POSITIONS",
        options: [
          { label: "Positions", value: "POSITIONS" },
          { label: "Open Orders", value: "OPEN_ORDERS" },
          { label: "Trade Log", value: "TRADE_LOG" },
        ],
      },
      {
        name: "showRealizedPnl",
        label: "Show Realized PnL",
        type: "boolean",
        default: true,
      },
    ],
  },
  component: BlotterWidget,
};
