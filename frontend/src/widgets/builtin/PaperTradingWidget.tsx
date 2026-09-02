import React, { useState, useEffect, useCallback } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";

export interface PaperTradingWidgetSettings {
  accountId?: string;
  defaultTab?: "POSITIONS" | "ORDER_BOOK" | "TRADE_BOOK" | "RECONCILIATION";
  autoRefreshInterval?: number;
}

export interface PaperOrderUI {
  order_id: string;
  account_id: string;
  symbol: string;
  security_id: string;
  side: "BUY" | "SELL";
  order_type: "MARKET" | "LIMIT" | "STOP_LOSS_MARKET" | "STOP_LOSS_LIMIT";
  quantity: number;
  filled_quantity: number;
  price?: number | null;
  trigger_price?: number | null;
  status: "SUBMITTED" | "ACCEPTED" | "PARTIALLY_FILLED" | "FILLED" | "CANCELLED" | "REJECTED" | "EXPIRED";
  reject_reason?: string | null;
  created_at: string;
}

export interface PaperFillUI {
  fill_id: string;
  order_id: string;
  account_id: string;
  symbol: string;
  security_id: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  slippage: number;
  transaction_cost: number;
  timestamp: string;
}

export interface PaperPositionUI {
  symbol: string;
  security_id: string;
  segment: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
}

export interface PortfolioSummaryUI {
  account_id: string;
  name: string;
  initial_capital: number;
  cash_balance: number;
  blocked_margin: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_equity: number;
  total_transaction_costs: number;
  total_orders: number;
  working_orders_count: number;
  filled_orders_count: number;
  rejected_orders_count: number;
  total_fills: number;
  open_positions_count: number;
  is_reconciled: boolean;
  cash_discrepancy: number;
  positions: PaperPositionUI[];
  rejected_orders: Array<{
    order_id: string;
    symbol: string;
    security_id: string;
    side: "BUY" | "SELL";
    quantity: number;
    reject_reason: string;
  }>;
}

const DEFAULT_SUMMARY: PortfolioSummaryUI = {
  account_id: "default",
  name: "Paper Portfolio",
  initial_capital: 1000000.0,
  cash_balance: 982450.0,
  blocked_margin: 0.0,
  realized_pnl: 1450.0,
  unrealized_pnl: 3220.0,
  total_equity: 985670.0,
  total_transaction_costs: 84.5,
  total_orders: 5,
  working_orders_count: 1,
  filled_orders_count: 3,
  rejected_orders_count: 1,
  total_fills: 3,
  open_positions_count: 2,
  is_reconciled: true,
  cash_discrepancy: 0.0,
  positions: [
    {
      symbol: "TCS",
      security_id: "11536",
      segment: "NSE_EQ",
      quantity: 30,
      avg_entry_price: 3500.0,
      current_price: 3650.0,
      realized_pnl: 1450.0,
      unrealized_pnl: 4500.0,
      total_pnl: 5950.0,
    },
    {
      symbol: "INFY",
      security_id: "1594",
      segment: "NSE_EQ",
      quantity: 100,
      avg_entry_price: 1600.0,
      current_price: 1587.2,
      realized_pnl: 0.0,
      unrealized_pnl: -1280.0,
      total_pnl: -1280.0,
    },
  ],
  rejected_orders: [
    {
      order_id: "ord-rej-1",
      symbol: "RELIANCE",
      security_id: "2885",
      side: "BUY",
      quantity: 1000,
      reject_reason: "Insufficient funds: required ₹3,000,000.00, available ₹982,450.00",
    },
  ],
};

export const PaperTradingWidget: React.FC<WidgetComponentProps<PaperTradingWidgetSettings>> = ({
  settings,
}) => {
  const accountId = settings.accountId || "default";
  const [activeTab, setActiveTab] = useState<"POSITIONS" | "ORDER_BOOK" | "TRADE_BOOK" | "RECONCILIATION">(
    settings.defaultTab || "POSITIONS"
  );
  const [summary, setSummary] = useState<PortfolioSummaryUI>(DEFAULT_SUMMARY);
  const [orders, setOrders] = useState<PaperOrderUI[]>([
    {
      order_id: "ord-1",
      account_id: accountId,
      symbol: "TCS",
      security_id: "11536",
      side: "BUY",
      order_type: "LIMIT",
      quantity: 50,
      filled_quantity: 50,
      price: 3500.0,
      status: "FILLED",
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      order_id: "ord-2",
      account_id: accountId,
      symbol: "INFY",
      security_id: "1594",
      side: "BUY",
      order_type: "LIMIT",
      quantity: 100,
      filled_quantity: 100,
      price: 1600.0,
      status: "FILLED",
      created_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      order_id: "ord-3",
      account_id: accountId,
      symbol: "TCS",
      security_id: "11536",
      side: "SELL",
      order_type: "LIMIT",
      quantity: 20,
      filled_quantity: 20,
      price: 3600.0,
      status: "FILLED",
      created_at: new Date(Date.now() - 900000).toISOString(),
    },
    {
      order_id: "ord-4",
      account_id: accountId,
      symbol: "RELIANCE",
      security_id: "2885",
      side: "BUY",
      order_type: "LIMIT",
      quantity: 1000,
      filled_quantity: 0,
      price: 3000.0,
      status: "REJECTED",
      reject_reason: "Insufficient funds: required ₹3,000,000.00, available ₹982,450.00",
      created_at: new Date(Date.now() - 600000).toISOString(),
    },
    {
      order_id: "ord-5",
      account_id: accountId,
      symbol: "SBIN",
      security_id: "3045",
      side: "BUY",
      order_type: "LIMIT",
      quantity: 150,
      filled_quantity: 0,
      price: 780.0,
      status: "ACCEPTED",
      created_at: new Date(Date.now() - 300000).toISOString(),
    },
  ]);

  const [fills, setFills] = useState<PaperFillUI[]>([
    {
      fill_id: "fill-1",
      order_id: "ord-1",
      account_id: accountId,
      symbol: "TCS",
      security_id: "11536",
      side: "BUY",
      quantity: 50,
      price: 3500.0,
      slippage: 0.0,
      transaction_cost: 32.5,
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      fill_id: "fill-2",
      order_id: "ord-2",
      account_id: accountId,
      symbol: "INFY",
      security_id: "1594",
      side: "BUY",
      quantity: 100,
      price: 1600.0,
      slippage: 0.0,
      transaction_cost: 30.2,
      timestamp: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      fill_id: "fill-3",
      order_id: "ord-3",
      account_id: accountId,
      symbol: "TCS",
      security_id: "11536",
      side: "SELL",
      quantity: 20,
      price: 3600.0,
      slippage: 0.0,
      transaction_cost: 21.8,
      timestamp: new Date(Date.now() - 900000).toISOString(),
    },
  ]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [cancelStatus, setCancelStatus] = useState<string | null>(null);

  const fetchPaperData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [sumRes, ordRes, fillRes] = await Promise.all([
        fetch(`/api/v1/paper/portfolio/summary?account_id=${encodeURIComponent(accountId)}`),
        fetch(`/api/v1/paper/orders?account_id=${encodeURIComponent(accountId)}`),
        fetch(`/api/v1/paper/fills?account_id=${encodeURIComponent(accountId)}`),
      ]);

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSummary(sumData);
      }
      if (ordRes.ok) {
        const ordData = await ordRes.json();
        if (Array.isArray(ordData) && ordData.length > 0) {
          setOrders(ordData);
        }
      }
      if (fillRes.ok) {
        const fillData = await fillRes.json();
        if (Array.isArray(fillData) && fillData.length > 0) {
          setFills(fillData);
        }
      }
    } catch {
      // Fallback cleanly to current state if API server is unmounted or offline
    } finally {
      setIsLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    void fetchPaperData();
  }, [fetchPaperData]);

  const handleCancelOrder = async (orderId: string) => {
    try {
      const res = await fetch(`/api/v1/paper/orders/${encodeURIComponent(orderId)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setCancelStatus(`Order ${orderId} cancelled`);
        setOrders((prev) =>
          prev.map((o) => (o.order_id === orderId ? { ...o, status: "CANCELLED" } : o))
        );
      } else {
        setCancelStatus(`Failed to cancel order ${orderId}`);
      }
    } catch {
      // Fallback local update
      setOrders((prev) =>
        prev.map((o) => (o.order_id === orderId ? { ...o, status: "CANCELLED" } : o))
      );
      setCancelStatus(`Order ${orderId} cancelled locally`);
    }
    setTimeout(() => setCancelStatus(null), 3000);
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "FILLED":
        return "#10B981"; // green
      case "ACCEPTED":
      case "SUBMITTED":
        return "#3B82F6"; // blue
      case "PARTIALLY_FILLED":
        return "#F59E0B"; // amber
      case "REJECTED":
        return "#EF4444"; // red
      case "CANCELLED":
      default:
        return "#6B7280"; // gray
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "var(--color-bg-primary, #0f172a)",
        color: "var(--color-text-primary, #f8fafc)",
        fontSize: "12px",
        fontFamily: "var(--font-family-sans, sans-serif)",
        overflow: "hidden",
      }}
    >
      {/* Account Metric Header Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gap: "8px",
          padding: "10px",
          backgroundColor: "var(--color-bg-secondary, #1e293b)",
          borderBottom: "1px solid var(--color-border, #334155)",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>Account Equity</span>
          <span style={{ fontSize: "14px", fontWeight: "bold", fontFamily: "var(--font-family-mono)" }}>
            ₹{summary.total_equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>Cash Available</span>
          <span style={{ fontSize: "14px", fontFamily: "var(--font-family-mono)" }}>
            ₹{summary.cash_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>Realized P&L</span>
          <span
            style={{
              fontSize: "14px",
              fontFamily: "var(--font-family-mono)",
              color: summary.realized_pnl >= 0 ? "#10B981" : "#EF4444",
            }}
          >
            {summary.realized_pnl >= 0 ? "+" : ""}
            ₹{summary.realized_pnl.toFixed(2)}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>Live MTM Unrealized</span>
          <span
            style={{
              fontSize: "14px",
              fontWeight: "bold",
              fontFamily: "var(--font-family-mono)",
              color: summary.unrealized_pnl >= 0 ? "#10B981" : "#EF4444",
            }}
          >
            {summary.unrealized_pnl >= 0 ? "+" : ""}
            ₹{summary.unrealized_pnl.toFixed(2)}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>Statutory Costs</span>
          <span style={{ fontSize: "14px", fontFamily: "var(--font-family-mono)", color: "#f59e0b" }}>
            ₹{summary.total_transaction_costs.toFixed(2)}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", justifyContent: "center" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 6px",
              borderRadius: "4px",
              backgroundColor: summary.is_reconciled ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
              color: summary.is_reconciled ? "#10B981" : "#EF4444",
              fontWeight: "600",
              fontSize: "11px",
            }}
          >
            {summary.is_reconciled ? "🟢 Reconciled" : `⚠️ Drift ₹${summary.cash_discrepancy}`}
          </div>
        </div>
      </div>

      {/* Tabs and Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 10px",
          borderBottom: "1px solid var(--color-border, #334155)",
          backgroundColor: "rgba(15, 23, 42, 0.6)",
        }}
      >
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            onClick={() => setActiveTab("POSITIONS")}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              border: "none",
              cursor: "pointer",
              fontWeight: activeTab === "POSITIONS" ? "bold" : "normal",
              backgroundColor: activeTab === "POSITIONS" ? "#2563EB" : "transparent",
              color: activeTab === "POSITIONS" ? "#fff" : "#94a3b8",
            }}
          >
            Positions ({summary.positions.filter((p) => p.quantity !== 0).length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("ORDER_BOOK")}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              border: "none",
              cursor: "pointer",
              fontWeight: activeTab === "ORDER_BOOK" ? "bold" : "normal",
              backgroundColor: activeTab === "ORDER_BOOK" ? "#2563EB" : "transparent",
              color: activeTab === "ORDER_BOOK" ? "#fff" : "#94a3b8",
            }}
          >
            Order Book ({orders.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("TRADE_BOOK")}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              border: "none",
              cursor: "pointer",
              fontWeight: activeTab === "TRADE_BOOK" ? "bold" : "normal",
              backgroundColor: activeTab === "TRADE_BOOK" ? "#2563EB" : "transparent",
              color: activeTab === "TRADE_BOOK" ? "#fff" : "#94a3b8",
            }}
          >
            Trade Book ({fills.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("RECONCILIATION")}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              border: "none",
              cursor: "pointer",
              fontWeight: activeTab === "RECONCILIATION" ? "bold" : "normal",
              backgroundColor: activeTab === "RECONCILIATION" ? "#2563EB" : "transparent",
              color: activeTab === "RECONCILIATION" ? "#fff" : "#94a3b8",
            }}
          >
            Reconciliation & Costs
          </button>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {cancelStatus && <span style={{ color: "#10b981", fontSize: "11px" }}>{cancelStatus}</span>}
          <button
            type="button"
            onClick={() => void fetchPaperData()}
            disabled={isLoading}
            style={{
              padding: "3px 8px",
              backgroundColor: "#334155",
              color: "#e2e8f0",
              border: "none",
              borderRadius: "3px",
              cursor: "pointer",
            }}
          >
            {isLoading ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Main Tab Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
        {/* POSITIONS TAB */}
        {activeTab === "POSITIONS" && (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155", color: "#94a3b8" }}>
                <th style={{ padding: "6px" }}>Symbol</th>
                <th style={{ padding: "6px" }}>Qty</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Avg Price</th>
                <th style={{ padding: "6px", textAlign: "right" }}>LTP</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Realized P&L</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Live MTM</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Net P&L</th>
              </tr>
            </thead>
            <tbody>
              {summary.positions.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "20px", color: "#64748b" }}>
                    No open paper positions
                  </td>
                </tr>
              ) : (
                summary.positions.map((pos) => (
                  <tr key={pos.security_id} style={{ borderBottom: "1px solid rgba(51, 65, 85, 0.4)" }}>
                    <td style={{ padding: "6px", fontWeight: "bold" }}>
                      {pos.symbol}{" "}
                      <span style={{ fontSize: "9px", color: "#64748b" }}>({pos.segment})</span>
                    </td>
                    <td style={{ padding: "6px", fontFamily: "var(--font-family-mono)" }}>
                      <span
                        style={{
                          padding: "1px 4px",
                          borderRadius: "2px",
                          backgroundColor: pos.quantity > 0 ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)",
                          color: pos.quantity > 0 ? "#10b981" : "#ef4444",
                        }}
                      >
                        {pos.quantity > 0 ? `+${pos.quantity}` : pos.quantity}
                      </span>
                    </td>
                    <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      ₹{pos.avg_entry_price.toFixed(2)}
                    </td>
                    <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      ₹{pos.current_price.toFixed(2)}
                    </td>
                    <td
                      style={{
                        padding: "6px",
                        textAlign: "right",
                        fontFamily: "var(--font-family-mono)",
                        color: pos.realized_pnl >= 0 ? "#10B981" : "#EF4444",
                      }}
                    >
                      {pos.realized_pnl >= 0 ? "+" : ""}
                      ₹{pos.realized_pnl.toFixed(2)}
                    </td>
                    <td
                      style={{
                        padding: "6px",
                        textAlign: "right",
                        fontFamily: "var(--font-family-mono)",
                        fontWeight: "bold",
                        color: pos.unrealized_pnl >= 0 ? "#10B981" : "#EF4444",
                      }}
                    >
                      {pos.unrealized_pnl >= 0 ? "+" : ""}
                      ₹{pos.unrealized_pnl.toFixed(2)}
                    </td>
                    <td
                      style={{
                        padding: "6px",
                        textAlign: "right",
                        fontFamily: "var(--font-family-mono)",
                        fontWeight: "bold",
                        color: pos.total_pnl >= 0 ? "#10B981" : "#EF4444",
                      }}
                    >
                      {pos.total_pnl >= 0 ? "+" : ""}
                      ₹{pos.total_pnl.toFixed(2)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* ORDER BOOK TAB */}
        {activeTab === "ORDER_BOOK" && (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155", color: "#94a3b8" }}>
                <th style={{ padding: "6px" }}>Order ID</th>
                <th style={{ padding: "6px" }}>Symbol</th>
                <th style={{ padding: "6px" }}>Side</th>
                <th style={{ padding: "6px" }}>Type</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Price</th>
                <th style={{ padding: "6px" }}>Status</th>
                <th style={{ padding: "6px" }}>Rejection / Reason</th>
                <th style={{ padding: "6px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((ord) => {
                const isWorking = ord.status === "ACCEPTED" || ord.status === "PARTIALLY_FILLED";
                return (
                  <tr key={ord.order_id} style={{ borderBottom: "1px solid rgba(51, 65, 85, 0.4)" }}>
                    <td style={{ padding: "6px", fontFamily: "var(--font-family-mono)", color: "#94a3b8" }}>
                      {ord.order_id}
                    </td>
                    <td style={{ padding: "6px", fontWeight: "bold" }}>{ord.symbol}</td>
                    <td style={{ padding: "6px" }}>
                      <span
                        style={{
                          padding: "2px 5px",
                          borderRadius: "3px",
                          fontWeight: "bold",
                          backgroundColor: ord.side === "BUY" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)",
                          color: ord.side === "BUY" ? "#10b981" : "#ef4444",
                        }}
                      >
                        {ord.side}
                      </span>
                    </td>
                    <td style={{ padding: "6px", color: "#cbd5e1" }}>{ord.order_type}</td>
                    <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      {ord.filled_quantity}/{ord.quantity}
                    </td>
                    <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                      {ord.price ? `₹${ord.price.toFixed(2)}` : "MKT"}
                    </td>
                    <td style={{ padding: "6px" }}>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: "3px",
                          fontSize: "11px",
                          fontWeight: "bold",
                          backgroundColor: `${statusColor(ord.status)}22`,
                          color: statusColor(ord.status),
                        }}
                      >
                        {ord.status}
                      </span>
                    </td>
                    <td style={{ padding: "6px" }}>
                      {ord.reject_reason ? (
                        <span
                          title={ord.reject_reason}
                          style={{
                            display: "inline-block",
                            maxWidth: "240px",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            color: "#ef4444",
                            backgroundColor: "rgba(239,68,68,0.1)",
                            padding: "2px 6px",
                            borderRadius: "3px",
                            fontSize: "11px",
                          }}
                        >
                          ⚠️ {ord.reject_reason}
                        </span>
                      ) : (
                        <span style={{ color: "#64748b" }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: "6px", textAlign: "center" }}>
                      {isWorking ? (
                        <button
                          type="button"
                          onClick={() => void handleCancelOrder(ord.order_id)}
                          style={{
                            padding: "2px 6px",
                            backgroundColor: "#ef4444",
                            color: "#fff",
                            border: "none",
                            borderRadius: "3px",
                            cursor: "pointer",
                            fontSize: "11px",
                          }}
                        >
                          Cancel
                        </button>
                      ) : (
                        <span style={{ color: "#64748b" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {/* TRADE BOOK TAB */}
        {activeTab === "TRADE_BOOK" && (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155", color: "#94a3b8" }}>
                <th style={{ padding: "6px" }}>Fill ID</th>
                <th style={{ padding: "6px" }}>Order ID</th>
                <th style={{ padding: "6px" }}>Symbol</th>
                <th style={{ padding: "6px" }}>Side</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Qty</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Exec Price</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Turnover</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Statutory Cost</th>
                <th style={{ padding: "6px", textAlign: "right" }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {fills.map((f) => (
                <tr key={f.fill_id} style={{ borderBottom: "1px solid rgba(51, 65, 85, 0.4)" }}>
                  <td style={{ padding: "6px", fontFamily: "var(--font-family-mono)", color: "#94a3b8" }}>
                    {f.fill_id}
                  </td>
                  <td style={{ padding: "6px", fontFamily: "var(--font-family-mono)", color: "#64748b" }}>
                    {f.order_id}
                  </td>
                  <td style={{ padding: "6px", fontWeight: "bold" }}>{f.symbol}</td>
                  <td style={{ padding: "6px" }}>
                    <span
                      style={{
                        padding: "1px 5px",
                        borderRadius: "3px",
                        fontWeight: "bold",
                        backgroundColor: f.side === "BUY" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)",
                        color: f.side === "BUY" ? "#10b981" : "#ef4444",
                      }}
                    >
                      {f.side}
                    </span>
                  </td>
                  <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {f.quantity}
                  </td>
                  <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{f.price.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    ₹{(f.quantity * f.price).toLocaleString()}
                  </td>
                  <td
                    style={{
                      padding: "6px",
                      textAlign: "right",
                      fontFamily: "var(--font-family-mono)",
                      color: "#f59e0b",
                    }}
                  >
                    ₹{f.transaction_cost.toFixed(2)}
                  </td>
                  <td style={{ padding: "6px", textAlign: "right", color: "#64748b", fontSize: "10px" }}>
                    {new Date(f.timestamp).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* RECONCILIATION & COSTS TAB */}
        {activeTab === "RECONCILIATION" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", padding: "6px" }}>
            <div
              style={{
                backgroundColor: "rgba(30, 41, 59, 0.7)",
                borderRadius: "6px",
                padding: "12px",
                border: "1px solid #334155",
              }}
            >
              <h4 style={{ margin: "0 0 8px 0", fontSize: "13px", color: "#38bdf8" }}>
                Mathematical Accounting Invariants
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <div style={{ color: "#94a3b8" }}>Initial Capital:</div>
                  <div style={{ fontFamily: "var(--font-family-mono)", fontSize: "13px" }}>
                    ₹{summary.initial_capital.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8" }}>Reconciliation Status:</div>
                  <div style={{ fontWeight: "bold", color: summary.is_reconciled ? "#10B981" : "#EF4444" }}>
                    {summary.is_reconciled ? "✓ Exact Parity (0.00 Discrepancy)" : "⚠️ Reconciliation Drift"}
                  </div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8" }}>Total Statutory Charges:</div>
                  <div style={{ fontFamily: "var(--font-family-mono)", color: "#f59e0b" }}>
                    ₹{summary.total_transaction_costs.toFixed(2)} (STT, GST, SEBI, Turnover, Stamp)
                  </div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8" }}>Discrepancy Drift:</div>
                  <div style={{ fontFamily: "var(--font-family-mono)" }}>
                    ₹{summary.cash_discrepancy.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            {summary.rejected_orders.length > 0 && (
              <div
                style={{
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  borderRadius: "6px",
                  padding: "12px",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                }}
              >
                <h4 style={{ margin: "0 0 8px 0", fontSize: "13px", color: "#f87171" }}>
                  Rejected Orders & Pre-Trade Risk Violations
                </h4>
                {summary.rejected_orders.map((rej) => (
                  <div
                    key={rej.order_id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      padding: "4px 0",
                      borderBottom: "1px solid rgba(239, 68, 68, 0.2)",
                    }}
                  >
                    <span>
                      <strong>{rej.symbol}</strong> ({rej.side} {rej.quantity} shares):
                    </span>
                    <span style={{ color: "#ef4444", fontWeight: "500" }}>{rej.reject_reason}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export const paperTradingDefinition: WidgetDefinition<PaperTradingWidgetSettings> = {
  id: "paper_trading",
  title: "Paper Trading Blotter",
  description: "Paper order book, trade book, open positions, live MTM, and statutory costs.",
  category: "order",
  icon: "📜",
  defaultWidth: 620,
  defaultHeight: 420,
  schema: {
    fields: [
      {
        name: "accountId",
        label: "Account ID",
        type: "string",
        default: "default",
      },
      {
        name: "defaultTab",
        label: "Default Tab",
        type: "select",
        default: "POSITIONS",
        options: [
          { label: "Positions", value: "POSITIONS" },
          { label: "Order Book", value: "ORDER_BOOK" },
          { label: "Trade Book", value: "TRADE_BOOK" },
          { label: "Reconciliation", value: "RECONCILIATION" },
        ],
      },
      {
        name: "autoRefreshInterval",
        label: "Auto Refresh (ms)",
        type: "number",
        default: 3000,
      },
    ],
  },
  component: PaperTradingWidget,
};
