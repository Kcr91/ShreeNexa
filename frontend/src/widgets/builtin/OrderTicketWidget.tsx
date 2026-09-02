import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  AssetClass,
  OrderSide,
  OrderType,
  ProductType,
  OptionLeg,
  ExecutionMode,
  StockOrder,
  MultiLegOptionOrder,
  OrderTicketSettings,
} from "../../order/types";
import { calculateStockMargin, calculateMultiLegOptionMargin } from "../../order/margin";
import { placeOrder } from "../../order/execution";

export const OrderTicketWidget: React.FC<WidgetComponentProps<OrderTicketSettings>> = ({
  settings,
}) => {
  const [assetClass, setAssetClass] = useState<AssetClass>(settings.defaultAssetClass || "EQUITY");
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("PAPER");

  // Stock Form State
  const [stockSymbol, setStockSymbol] = useState<string>(settings.defaultSymbol || "RELIANCE");
  const [stockSide, setStockSide] = useState<OrderSide>("BUY");
  const [stockProduct, setStockProduct] = useState<ProductType>("CNC");
  const [stockOrderType, setStockOrderType] = useState<OrderType>("LIMIT");
  const [stockQuantity, setStockQuantity] = useState<number>(settings.defaultQuantity || 25);
  const [stockPrice, setStockPrice] = useState<number>(2950);

  // Multi-Leg Option Form State
  const [optionUnderlying, setOptionUnderlying] = useState<string>("NIFTY");
  const [optionExpiry, setOptionExpiry] = useState<string>("2026-01-29");
  const [legs, setLegs] = useState<OptionLeg[]>([
    {
      id: "leg-1",
      symbol: "NIFTY",
      expiry: "2026-01-29",
      strike: 24500,
      optionType: "CE",
      side: "SELL",
      quantity: 50,
      premium: 145.2,
    },
    {
      id: "leg-2",
      symbol: "NIFTY",
      expiry: "2026-01-29",
      strike: 24000,
      optionType: "PE",
      side: "SELL",
      quantity: 50,
      premium: 128.5,
    },
  ]);

  const [submissionStatus, setSubmissionStatus] = useState<{ success: boolean; message: string } | null>(null);

  const availableFunds = 500000; // Mock development buying power

  // Margin Previews
  const stockMargin = useMemo(() => {
    return calculateStockMargin(
      {
        symbol: stockSymbol,
        side: stockSide,
        orderType: stockOrderType,
        productType: stockProduct,
        quantity: stockQuantity,
        price: stockPrice,
      },
      availableFunds
    );
  }, [stockSymbol, stockSide, stockOrderType, stockProduct, stockQuantity, stockPrice, availableFunds]);

  const optionMargin = useMemo(() => {
    return calculateMultiLegOptionMargin(legs, availableFunds);
  }, [legs, availableFunds]);

  const handleAddLeg = () => {
    const newLeg: OptionLeg = {
      id: `leg-${Date.now()}`,
      symbol: optionUnderlying,
      expiry: optionExpiry,
      strike: 24600,
      optionType: "CE",
      side: "BUY",
      quantity: 50,
      premium: 95.0,
    };
    setLegs([...legs, newLeg]);
  };

  const handleRemoveLeg = (id: string) => {
    setLegs(legs.filter((l) => l.id !== id));
  };

  const handleStockSubmit = () => {
    const order: StockOrder = {
      symbol: stockSymbol,
      side: stockSide,
      orderType: stockOrderType,
      productType: stockProduct,
      quantity: stockQuantity,
      price: stockPrice,
    };
    const res = placeOrder(order, availableFunds, executionMode, false);
    setSubmissionStatus(res);
  };

  const handleOptionSubmit = () => {
    const order: MultiLegOptionOrder = {
      strategyName: `${optionUnderlying} Custom Multi-Leg`,
      productType: "NRML",
      legs,
    };
    const res = placeOrder(order, availableFunds, executionMode, false);
    setSubmissionStatus(res);
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-3)", gap: "var(--spacing-3)" }}>
      {/* Top Controls: Asset Class & Mode */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            onClick={() => setAssetClass("EQUITY")}
            style={{
              padding: "var(--spacing-1) var(--spacing-3)",
              backgroundColor: assetClass === "EQUITY" ? "var(--bg-active)" : "transparent",
              color: assetClass === "EQUITY" ? "var(--color-primary)" : "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Equity Stock
          </button>
          <button
            type="button"
            onClick={() => setAssetClass("OPTION")}
            style={{
              padding: "var(--spacing-1) var(--spacing-3)",
              backgroundColor: assetClass === "OPTION" ? "var(--bg-active)" : "transparent",
              color: assetClass === "OPTION" ? "var(--color-primary)" : "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Multi-Leg Options
          </button>
        </div>

        {/* Paper vs Live Mode Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)", fontSize: "var(--font-size-xs)" }}>
          <span style={{ color: "var(--text-muted)" }}>Mode:</span>
          <select
            value={executionMode}
            onChange={(e) => setExecutionMode(e.target.value as ExecutionMode)}
            aria-label="Execution Mode"
            style={{
              backgroundColor: executionMode === "LIVE" ? "var(--color-down-bg)" : "var(--color-up-bg)",
              color: executionMode === "LIVE" ? "var(--color-down)" : "var(--color-up)",
              fontWeight: "bold",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "2px 6px",
              fontSize: "var(--font-size-xs)",
            }}
          >
            <option value="PAPER">Paper Simulation</option>
            <option value="LIVE">Live Broker (Locked)</option>
          </select>
        </div>
      </div>

      {/* Submission Status Message */}
      {submissionStatus && (
        <div
          role="alert"
          style={{
            padding: "var(--spacing-2)",
            backgroundColor: submissionStatus.success ? "var(--color-up-bg)" : "var(--color-down-bg)",
            color: submissionStatus.success ? "var(--color-up)" : "var(--color-down)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
          }}
        >
          {submissionStatus.message}
        </div>
      )}

      {/* Main Form Body */}
      {assetClass === "EQUITY" ? (
        /* Equity Form */
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)", flex: 1, overflowY: "auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-2)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="stock-symbol-select" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Symbol</label>
              <select
                id="stock-symbol-select"
                value={stockSymbol}
                onChange={(e) => setStockSymbol(e.target.value)}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              >
                <option value="RELIANCE">RELIANCE</option>
                <option value="TCS">TCS</option>
                <option value="HDFCBANK">HDFCBANK</option>
                <option value="INFY">INFY</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Side</label>
              <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
                <button
                  type="button"
                  onClick={() => setStockSide("BUY")}
                  style={{
                    flex: 1,
                    padding: "var(--spacing-1)",
                    backgroundColor: stockSide === "BUY" ? "var(--color-up)" : "var(--bg-surface)",
                    color: stockSide === "BUY" ? "var(--text-inverse)" : "var(--text-muted)",
                    border: "none",
                    borderRadius: "var(--radius-sm)",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setStockSide("SELL")}
                  style={{
                    flex: 1,
                    padding: "var(--spacing-1)",
                    backgroundColor: stockSide === "SELL" ? "var(--color-down)" : "var(--bg-surface)",
                    color: stockSide === "SELL" ? "var(--text-inverse)" : "var(--text-muted)",
                    border: "none",
                    borderRadius: "var(--radius-sm)",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  SELL
                </button>
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--spacing-2)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="stock-type-select" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Order Type</label>
              <select
                id="stock-type-select"
                value={stockOrderType}
                onChange={(e) => setStockOrderType(e.target.value as OrderType)}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              >
                <option value="LIMIT">LIMIT</option>
                <option value="MARKET">MARKET</option>
              </select>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="stock-product-select" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Product</label>
              <select
                id="stock-product-select"
                value={stockProduct}
                onChange={(e) => setStockProduct(e.target.value as ProductType)}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              >
                <option value="CNC">CNC (Delivery)</option>
                <option value="MIS">MIS (Intraday)</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="stock-quantity-input" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Quantity</label>
              <input
                id="stock-quantity-input"
                type="number"
                value={stockQuantity}
                onChange={(e) => setStockQuantity(Number(e.target.value))}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="stock-price-input" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Price (₹)</label>
              <input
                id="stock-price-input"
                type="number"
                value={stockPrice}
                onChange={(e) => setStockPrice(Number(e.target.value))}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              />
            </div>
          </div>

          {/* Margin Summary Box */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--spacing-3)",
              fontSize: "var(--font-size-xs)",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Required Margin:</span>
              <strong style={{ fontFamily: "var(--font-family-mono)" }}>₹{stockMargin.totalRequiredMargin.toLocaleString()}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Est. Regulatory Costs:</span>
              <span style={{ fontFamily: "var(--font-family-mono)" }}>₹{stockMargin.estimatedCosts}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--border-subtle)", paddingTop: "4px" }}>
              <span style={{ color: "var(--text-muted)" }}>Available Funds:</span>
              <span style={{ fontFamily: "var(--font-family-mono)", color: stockMargin.isSufficient ? "var(--color-up)" : "var(--color-down)" }}>
                ₹{availableFunds.toLocaleString()}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleStockSubmit}
            style={{
              padding: "var(--spacing-2)",
              backgroundColor: stockSide === "BUY" ? "var(--color-up)" : "var(--color-down)",
              color: "var(--text-inverse)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontWeight: "bold",
              fontSize: "var(--font-size-sm)",
              cursor: "pointer",
            }}
          >
            Submit {executionMode} Order
          </button>
        </div>
      ) : (
        /* Multi-Leg Option Builder */
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)", flex: 1, overflowY: "auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-2)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="option-underlying-select" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Underlying Index</label>
              <select
                id="option-underlying-select"
                value={optionUnderlying}
                onChange={(e) => setOptionUnderlying(e.target.value)}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              >
                <option value="NIFTY">NIFTY</option>
                <option value="BANKNIFTY">BANKNIFTY</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <label htmlFor="option-expiry-select" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Expiry Date</label>
              <select
                id="option-expiry-select"
                value={optionExpiry}
                onChange={(e) => setOptionExpiry(e.target.value)}
                style={{
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-1)",
                }}
              >
                <option value="2026-01-29">2026-01-29 (Weekly)</option>
                <option value="2026-02-26">2026-02-26 (Monthly)</option>
              </select>
            </div>
          </div>

          {/* Option Legs Table */}
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-1)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "var(--font-size-xs)", fontWeight: 600 }}>Option Legs ({legs.length})</span>
              <button
                type="button"
                onClick={handleAddLeg}
                style={{
                  fontSize: "0.6875rem",
                  padding: "2px 6px",
                  backgroundColor: "var(--color-primary-bg)",
                  color: "var(--color-primary)",
                  border: "1px solid var(--color-primary)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                }}
              >
                + Add Leg
              </button>
            </div>

            {legs.map((leg, idx) => (
              <div
                key={leg.id}
                data-testid={`option-leg-row-${idx}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "60px 80px 50px 60px 70px 24px",
                  gap: "var(--spacing-1)",
                  alignItems: "center",
                  backgroundColor: "var(--bg-surface)",
                  padding: "var(--spacing-1) var(--spacing-2)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-xs)",
                }}
              >
                <span style={{ fontWeight: 600, color: leg.side === "BUY" ? "var(--color-up)" : "var(--color-down)" }}>
                  {leg.side}
                </span>
                <span>{leg.strike}</span>
                <span style={{ fontWeight: 600 }}>{leg.optionType}</span>
                <span>Qty: {leg.quantity}</span>
                <span>₹{leg.premium}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveLeg(leg.id)}
                  aria-label={`Remove Leg ${idx + 1}`}
                  style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          {/* Option Margin Breakdown */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--spacing-3)",
              fontSize: "var(--font-size-xs)",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Hedging Benefit Offset:</span>
              <span style={{ fontFamily: "var(--font-family-mono)", color: "var(--color-up)" }}>
                -₹{optionMargin.hedgingBenefit.toLocaleString()}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Total Net Margin Required:</span>
              <strong style={{ fontFamily: "var(--font-family-mono)" }}>
                ₹{optionMargin.totalRequiredMargin.toLocaleString()}
              </strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Est. Regulatory Costs:</span>
              <span style={{ fontFamily: "var(--font-family-mono)" }}>₹{optionMargin.estimatedCosts}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleOptionSubmit}
            style={{
              padding: "var(--spacing-2)",
              backgroundColor: "var(--color-primary)",
              color: "var(--text-inverse)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontWeight: "bold",
              fontSize: "var(--font-size-sm)",
              cursor: "pointer",
            }}
          >
            Submit Multi-Leg {executionMode} Order
          </button>
        </div>
      )}
    </div>
  );
};

export const orderTicketDefinition: WidgetDefinition<OrderTicketSettings> = {
  id: "order-ticket",
  title: "Order Ticket & Leg Builder",
  description: "Stock and multi-leg options ticket with margin calculation and risk gates.",
  category: "order",
  icon: "🎫",
  defaultWidth: 380,
  defaultHeight: 460,
  schema: {
    fields: [
      {
        name: "defaultAssetClass",
        label: "Default Asset Class",
        type: "select",
        default: "EQUITY",
        options: [
          { label: "Equity Stock", value: "EQUITY" },
          { label: "Multi-Leg Options", value: "OPTION" },
        ],
      },
      {
        name: "defaultSymbol",
        label: "Default Symbol",
        type: "string",
        default: "RELIANCE",
      },
      {
        name: "defaultQuantity",
        label: "Default Quantity",
        type: "number",
        default: 25,
        min: 1,
      },
    ],
  },
  component: OrderTicketWidget,
};
