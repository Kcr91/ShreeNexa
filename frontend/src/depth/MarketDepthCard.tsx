import React, { useState, useMemo } from "react";
import { MarketDepthBook } from "./types";
import { generateMockDepthBook } from "./engine";

export interface MarketDepthItemData {
  symbol: string;
  tradingSymbol?: string;
  name?: string;
  segment?: string;
  instrumentType?: string;
  securityId?: string;
  ltp?: number;
  lastPrice?: number;
  changePct?: number;
  changeAbs?: number;
  open?: number;
  prevClose?: number;
  high?: number;
  low?: number;
  volume?: number;
  avgPrice?: number;
  lowerCircuit?: number;
  upperCircuit?: number;
  ltq?: number;
  ltt?: string;
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
}

export interface MarketDepthCardProps {
  item: MarketDepthItemData;
  onClose?: () => void;
  isEmbedded?: boolean;
  capability?: string;
}

// Exact mock data from screenshot for MPHASIS if applicable
const MPHASIS_DEFAULT_DEPTH = {
  bids: [
    { price: 2357.10, orders: 5, quantity: 99 },
    { price: 2356.20, orders: 1, quantity: 92 },
    { price: 2356.10, orders: 1, quantity: 48 },
    { price: 2356.00, orders: 2, quantity: 48 },
    { price: 2355.90, orders: 1, quantity: 1 },
  ],
  totalBidQty: 35801,
  asks: [
    { price: 2357.50, orders: 2, quantity: 15 },
    { price: 2357.70, orders: 1, quantity: 6 },
    { price: 2357.90, orders: 1, quantity: 7 },
    { price: 2358.00, orders: 1, quantity: 1 },
    { price: 2358.40, orders: 2, quantity: 12 },
  ],
  totalAskQty: 23606,
};

export const MarketDepthCard: React.FC<MarketDepthCardProps> = ({
  item,
  onClose,
  isEmbedded = false,
  capability,
}) => {
  const [showDetails, setShowDetails] = useState(true);

  const ltp = item.ltp ?? item.lastPrice ?? 1000.0;
  const changeAbs = item.changeAbs ?? (item.changePct ? (ltp * item.changePct) / 100 : 0);
  const changePct = item.changePct ?? (item.prevClose ? ((ltp - item.prevClose) / item.prevClose) * 100 : 0);
  const isNegative = changePct < 0 || changeAbs < 0;
  const accentColor = isNegative ? "#ff5252" : "#3fb950";

  // Compute or fall back to statistics matching the image
  const prevClose = item.prevClose ?? Number((ltp - changeAbs).toFixed(2));
  const open = item.open ?? Number((prevClose * 0.995).toFixed(2));
  const high = item.high ?? Math.max(ltp, open, prevClose) * 1.004;
  const low = item.low ?? Math.min(ltp, open, prevClose) * 0.992;
  const volume = item.volume ?? 366195;
  const avgPrice = item.avgPrice ?? Number(((open + high + low + ltp) / 4).toFixed(2));
  const lowerCircuit = item.lowerCircuit ?? Number((prevClose * 0.9).toFixed(2));
  const upperCircuit = item.upperCircuit ?? Number((prevClose * 1.1).toFixed(2));
  const ltq = item.ltq ?? 3;
  const ltt = item.ltt ?? "2026-09-07 11:40:03";

  // 52-week High and Low
  const high52 = item.fiftyTwoWeekHigh ?? Number((Math.max(high, ltp) * 1.25).toFixed(2));
  const low52 = item.fiftyTwoWeekLow ?? Number((Math.min(low, ltp) * 0.85).toFixed(2));
  const diffFrom52High = ((ltp - high52) / high52) * 100;
  const diffFrom52Low = ((ltp - low52) / low52) * 100;

  // Day range slider percentage
  const rangeSpan = Math.max(high - low, 0.01);
  const currentSliderPct = Math.min(100, Math.max(0, ((ltp - low) / rangeSpan) * 100));

  // Depth data
  const depthBook: {
    bids: { price: number; orders: number; quantity: number }[];
    asks: { price: number; orders: number; quantity: number }[];
    totalBidQty: number;
    totalAskQty: number;
  } = useMemo(() => {
    if (item.symbol === "MPHASIS" && (!item.ltp || Math.abs(item.ltp - 2357.10) < 5)) {
      return MPHASIS_DEFAULT_DEPTH;
    }
    const generated: MarketDepthBook = generateMockDepthBook(
      item.symbol,
      item.segment || "NSE_EQ",
      "LEVEL_5",
      ltp,
      Number(item.securityId) || 1000
    );
    return {
      bids: generated.bids.slice(0, 5),
      asks: generated.asks.slice(0, 5),
      totalBidQty: generated.totalBidQty,
      totalAskQty: generated.totalAskQty,
    };
  }, [item.symbol, item.segment, item.securityId, ltp]);

  const maxBidQty = Math.max(...depthBook.bids.map((b) => b.quantity), 1);
  const maxAskQty = Math.max(...depthBook.asks.map((a) => a.quantity), 1);

  return (
    <div
      style={{
        backgroundColor: "#161a1e",
        color: "#d1d5db",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        fontSize: "12px",
        borderRadius: "6px",
        border: "1px solid #23272e",
        padding: "14px 16px",
        width: "100%",
        maxWidth: "420px",
        boxSizing: "border-box",
        boxShadow: isEmbedded ? "none" : "0 8px 24px rgba(0,0,0,0.6)",
      }}
      data-testid="market-depth-card"
    >
      {/* 1. Header: Script Symbol, Change, % Change, LTP */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontWeight: 700,
              fontSize: "15px",
              color: accentColor,
              letterSpacing: "0.5px",
            }}
          >
            {item.symbol}
          </span>
          {capability && (
            <span
              style={{
                fontSize: "10px",
                color: "#58a6ff",
                backgroundColor: "rgba(88, 166, 255, 0.12)",
                padding: "1px 6px",
                borderRadius: "3px",
                fontWeight: 600,
              }}
            >
              {capability}
            </span>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close modal"
              title="Close modal"
              style={{
                background: "none",
                border: "none",
                color: "#8b949e",
                cursor: "pointer",
                fontSize: "14px",
                padding: "0 4px",
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          )}
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontSize: "13px",
          }}
        >
          <span style={{ color: accentColor }}>
            {changeAbs >= 0 ? `+${changeAbs.toFixed(2)}` : changeAbs.toFixed(2)}
          </span>
          <span style={{ color: accentColor, display: "flex", alignItems: "center", gap: "2px" }}>
            {changePct >= 0 ? `+${changePct.toFixed(2)}%` : `${changePct.toFixed(2)}%`}
            <span style={{ fontSize: "10px" }}>{isNegative ? "v" : "▲"}</span>
          </span>
          <span style={{ color: accentColor, fontWeight: 700, fontSize: "14px" }}>
            {ltp.toFixed(2)}
          </span>
        </div>
      </div>

      {/* 2. 5-Level Depth Table */}
      <div style={{ marginBottom: "8px" }}>
        {/* Table Headers */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            color: "#8b949e",
            fontSize: "11px",
            paddingBottom: "4px",
            borderBottom: "1px solid #23272e",
          }}
        >
          {/* Bid Headers */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 45px 50px" }}>
            <span>Bid</span>
            <span style={{ textAlign: "right" }}>Orders</span>
            <span style={{ textAlign: "right" }}>Qty.</span>
          </div>
          {/* Offer Headers */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 45px 50px" }}>
            <span>Offer</span>
            <span style={{ textAlign: "right" }}>Orders</span>
            <span style={{ textAlign: "right" }}>Qty.</span>
          </div>
        </div>

        {/* 5 Rows of Bids and Offers */}
        <div style={{ marginTop: "4px" }}>
          {Array.from({ length: 5 }).map((_, idx) => {
            const bid = depthBook.bids[idx];
            const ask = depthBook.asks[idx];

            const bidBarWidthPct = bid ? Math.min(100, Math.round((bid.quantity / maxBidQty) * 100)) : 0;
            const askBarWidthPct = ask ? Math.min(100, Math.round((ask.quantity / maxAskQty) * 100)) : 0;

            return (
              <div
                key={idx}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  fontSize: "12px",
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                  lineHeight: "22px",
                }}
              >
                {/* Bid Row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 45px 50px", position: "relative" }}>
                  <span style={{ color: "#388bfd" }}>{bid ? bid.price.toFixed(2) : "—"}</span>
                  <span style={{ textAlign: "right", color: "#388bfd" }}>{bid ? bid.orders : "—"}</span>
                  <span
                    style={{
                      textAlign: "right",
                      color: "#388bfd",
                      position: "relative",
                      zIndex: 1,
                    }}
                  >
                    {bid ? bid.quantity : "—"}
                  </span>
                  {/* Visual Quantity Depth Bar behind Qty */}
                  {bid && (
                    <div
                      style={{
                        position: "absolute",
                        right: 0,
                        top: 2,
                        bottom: 2,
                        width: `${bidBarWidthPct}%`,
                        backgroundColor: "rgba(56, 139, 253, 0.22)",
                        borderRadius: "2px",
                        zIndex: 0,
                        pointerEvents: "none",
                      }}
                    />
                  )}
                </div>

                {/* Offer Row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 45px 50px", position: "relative" }}>
                  <span style={{ color: "#ff5252" }}>{ask ? ask.price.toFixed(2) : "—"}</span>
                  <span style={{ textAlign: "right", color: "#ff5252" }}>{ask ? ask.orders : "—"}</span>
                  <span
                    style={{
                      textAlign: "right",
                      color: "#ff5252",
                      position: "relative",
                      zIndex: 1,
                    }}
                  >
                    {ask ? ask.quantity : "—"}
                  </span>
                  {/* Visual Quantity Depth Bar behind Qty */}
                  {ask && (
                    <div
                      style={{
                        position: "absolute",
                        right: 0,
                        top: 2,
                        bottom: 2,
                        width: `${askBarWidthPct}%`,
                        backgroundColor: "rgba(248, 81, 73, 0.22)",
                        borderRadius: "2px",
                        zIndex: 0,
                        pointerEvents: "none",
                      }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Totals Row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            fontSize: "12px",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontWeight: 600,
            marginTop: "6px",
            paddingTop: "4px",
            borderTop: "1px solid #23272e",
          }}
        >
          {/* Bid Total */}
          <div style={{ display: "flex", justifyContent: "space-between", color: "#388bfd" }}>
            <span>Total Bid</span>
            <span data-testid="total-bid-qty">{depthBook.totalBidQty.toLocaleString("en-IN")}</span>
          </div>

          {/* Offer Total */}
          <div style={{ display: "flex", justifyContent: "space-between", color: "#ff5252" }}>
            <span>Total Ask</span>
            <span data-testid="total-ask-qty">{depthBook.totalAskQty.toLocaleString("en-IN")}</span>
          </div>
        </div>
      </div>

      {/* 3. Expand / Collapse Arrow */}
      <div
        data-testid="depth-collapse-toggle"
        role="button"
        aria-label="Toggle market details"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "2px 0 6px 0",
          cursor: "pointer",
        }}
        onClick={() => setShowDetails((prev) => !prev)}
        title={showDetails ? "Collapse details" : "Expand details"}
      >
        <span
          style={{
            fontSize: "12px",
            color: "#8b949e",
            transform: showDetails ? "none" : "rotate(180deg)",
            transition: "transform 0.2s ease",
            userSelect: "none",
          }}
        >
          v
        </span>
      </div>

      {/* 4. Detailed Market Statistics & Day Range */}
      {showDetails && (
        <div style={{ borderTop: "1px solid #23272e", paddingTop: "10px" }}>
          {/* Open & Prev. Close */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "6px",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Open</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {open.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Prev. Close</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {prevClose.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          {/* Low & High */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "10px",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Low</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {low.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>High</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {high.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          {/* Day Range Slider Bar */}
          <div style={{ position: "relative", marginBottom: "14px", padding: "4px 0" }}>
            {/* Background track */}
            <div
              style={{
                height: "3px",
                backgroundColor: "#30363d",
                borderRadius: "2px",
                position: "relative",
              }}
            >
              {/* Highlighted range bar */}
              <div
                style={{
                  position: "absolute",
                  left: `${Math.min(currentSliderPct, 100)}%`,
                  right: 0,
                  height: "3px",
                  backgroundColor: accentColor,
                  borderRadius: "2px",
                }}
              />
              {/* Dot at high right end */}
              <div
                style={{
                  position: "absolute",
                  right: "-2px",
                  top: "-2px",
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  backgroundColor: "#8b949e",
                }}
              />
            </div>

            {/* Current Price Upward Marker ▲ */}
            <div
              style={{
                position: "absolute",
                left: `${currentSliderPct}%`,
                top: "6px",
                transform: "translateX(-50%)",
                fontSize: "8px",
                color: "#8b949e",
                lineHeight: 1,
                userSelect: "none",
              }}
              title={`Current Price: ${ltp.toFixed(2)}`}
            >
              ▲
            </div>
          </div>

          {/* Volume & Avg. Price */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "6px",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Volume</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {volume.toLocaleString("en-IN")}
              </span>
            </div>
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Avg. price</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {avgPrice.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          {/* Lower Circuit & Upper Circuit */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "6px",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Lower circuit</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {lowerCircuit.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>Upper circuit</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {upperCircuit.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          {/* LTQ & LTT */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "6px",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>LTQ</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {ltq}
              </span>
            </div>
            <div style={{ display: "flex", gap: "10px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>LTT</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc", fontSize: "11px" }}>
                {ltt}
              </span>
            </div>
          </div>

          {/* 52W Low & 52W High (% from current price) */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: "6px",
              paddingTop: "6px",
              borderTop: "1px dashed #23272e",
              fontSize: "11px",
            }}
          >
            <div style={{ display: "flex", gap: "6px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>52W Low</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {low52.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                <span style={{ color: diffFrom52Low >= 0 ? "#3fb950" : "#ff5252", marginLeft: "4px" }}>
                  ({diffFrom52Low >= 0 ? "+" : ""}{diffFrom52Low.toFixed(1)}%)
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "6px", width: "48%", justifyContent: "space-between" }}>
              <span style={{ color: "#8b949e" }}>52W High</span>
              <span style={{ fontFamily: "ui-monospace, monospace", color: "#f0f6fc" }}>
                {high52.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                <span style={{ color: diffFrom52High >= 0 ? "#3fb950" : "#ff5252", marginLeft: "4px" }}>
                  ({diffFrom52High >= 0 ? "+" : ""}{diffFrom52High.toFixed(1)}%)
                </span>
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
