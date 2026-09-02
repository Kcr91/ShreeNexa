import React, { useState, useEffect, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  DepthLevelType,
  DepthWatchlistItem,
} from "../../depth/types";
import {
  generateMockDepthBook,
} from "../../depth/engine";

export interface DepthWidgetSettings {
  defaultSymbol?: string;
  defaultSegment?: string;
  defaultLevel?: DepthLevelType;
  defaultMode?: "LADDER" | "WATCHLIST";
}

const DEFAULT_PINNED_WATCHLIST: DepthWatchlistItem[] = [
  {
    symbol: "RELIANCE",
    segment: "NSE_EQ",
    bestBid: 2979.95,
    bestAsk: 2980.05,
    spread: 0.10,
    top5Imbalance: 0.18,
    totalBidQty: 48500,
    totalAskQty: 39200,
    depthLevelType: "LEVEL_20",
    isFallback: false,
  },
  {
    symbol: "HDFCBANK",
    segment: "NSE_EQ",
    bestBid: 1639.95,
    bestAsk: 1640.05,
    spread: 0.10,
    top5Imbalance: -0.05,
    totalBidQty: 62000,
    totalAskQty: 65400,
    depthLevelType: "LEVEL_20",
    isFallback: false,
  },
  {
    symbol: "ICICIBANK",
    segment: "NSE_EQ",
    bestBid: 1214.95,
    bestAsk: 1215.05,
    spread: 0.10,
    top5Imbalance: 0.22,
    totalBidQty: 38900,
    totalAskQty: 29800,
    depthLevelType: "LEVEL_20",
    isFallback: false,
  },
  {
    symbol: "INFY",
    segment: "NSE_EQ",
    bestBid: 1889.95,
    bestAsk: 1890.05,
    spread: 0.10,
    top5Imbalance: -0.12,
    totalBidQty: 28400,
    totalAskQty: 32600,
    depthLevelType: "LEVEL_20",
    isFallback: false,
  },
  {
    symbol: "TCS",
    segment: "NSE_EQ",
    bestBid: 4209.95,
    bestAsk: 4210.05,
    spread: 0.10,
    top5Imbalance: 0.08,
    totalBidQty: 21500,
    totalAskQty: 19800,
    depthLevelType: "LEVEL_20",
    isFallback: false,
  },
  {
    symbol: "BSE_SENSEX",
    segment: "BSE_EQ",
    bestBid: 82499.00,
    bestAsk: 82501.00,
    spread: 2.00,
    top5Imbalance: 0.04,
    totalBidQty: 12500,
    totalAskQty: 11900,
    depthLevelType: "LEVEL_5",
    isFallback: true,
  },
  {
    symbol: "MCX_GOLD",
    segment: "MCX_COMM",
    bestBid: 74198.00,
    bestAsk: 74202.00,
    spread: 4.00,
    top5Imbalance: -0.09,
    totalBidQty: 8400,
    totalAskQty: 9200,
    depthLevelType: "LEVEL_5",
    isFallback: true,
  },
];

export const MarketDepthWidget: React.FC<WidgetComponentProps<DepthWidgetSettings>> = ({
  settings,
}) => {
  const [viewMode, setViewMode] = useState<"LADDER" | "WATCHLIST">(
    settings.defaultMode || "LADDER"
  );
  const [symbol, setSymbol] = useState<string>(settings.defaultSymbol || "RELIANCE");
  const [segment, setSegment] = useState<string>(settings.defaultSegment || "NSE_EQ");
  const [level, setLevel] = useState<DepthLevelType>(settings.defaultLevel || "LEVEL_20");

  const depthBook = useMemo(() => {
    return generateMockDepthBook(symbol, segment, level, 2980.0);
  }, [symbol, segment, level]);

  const [watchlist, setWatchlist] = useState<DepthWatchlistItem[]>(DEFAULT_PINNED_WATCHLIST);

  useEffect(() => {
    fetch("/api/v1/depth/watchlist")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setWatchlist(data);
        }
      })
      .catch(() => {});
  }, []);

  const handleFocusSymbol = (sym: string, seg: string) => {
    setSymbol(sym);
    setSegment(seg);
    setViewMode("LADDER");
  };

  const maxBidQty = Math.max(...depthBook.bids.map((b) => b.quantity), 1);
  const maxAskQty = Math.max(...depthBook.asks.map((a) => a.quantity), 1);

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--bg-surface)",
        color: "var(--text-primary)",
        fontSize: "var(--font-size-sm)",
      }}
    >
      {/* 1. Header & Controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--spacing-2)",
          padding: "var(--spacing-2)",
          backgroundColor: "var(--bg-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            onClick={() => setViewMode("LADDER")}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: viewMode === "LADDER" ? "var(--color-brand)" : "transparent",
              color: viewMode === "LADDER" ? "#fff" : "var(--text-muted)",
              fontWeight: 600,
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Depth Ladder
          </button>
          <button
            type="button"
            onClick={() => setViewMode("WATCHLIST")}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: viewMode === "WATCHLIST" ? "var(--color-brand)" : "transparent",
              color: viewMode === "WATCHLIST" ? "#fff" : "var(--text-muted)",
              fontWeight: 600,
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Depth Watchlist ({watchlist.length})
          </button>
        </div>

        {viewMode === "LADDER" && (
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              style={{
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "var(--bg-input)",
                color: "var(--text-primary)",
                fontSize: "var(--font-size-xs)",
                fontWeight: 700,
              }}
            >
              <option value="RELIANCE">RELIANCE</option>
              <option value="HDFCBANK">HDFCBANK</option>
              <option value="ICICIBANK">ICICIBANK</option>
              <option value="INFY">INFY</option>
              <option value="TCS">TCS</option>
              <option value="BSE_SENSEX">BSE_SENSEX</option>
              <option value="MCX_GOLD">MCX_GOLD</option>
            </select>

            <select
              value={segment}
              onChange={(e) => setSegment(e.target.value)}
              style={{
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "var(--bg-input)",
                color: "var(--text-primary)",
                fontSize: "var(--font-size-xs)",
              }}
            >
              <option value="NSE_EQ">NSE_EQ</option>
              <option value="NSE_FNO">NSE_FNO</option>
              <option value="BSE_EQ">BSE_EQ (5-Level)</option>
              <option value="MCX_COMM">MCX_COMM (5-Level)</option>
            </select>

            {/* Depth Level buttons */}
            <div style={{ display: "flex", gap: "2px" }}>
              <button
                type="button"
                onClick={() => setLevel("LEVEL_5")}
                style={{
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: level === "LEVEL_5" ? "var(--bg-active)" : "transparent",
                  color: level === "LEVEL_5" ? "var(--color-primary)" : "var(--text-muted)",
                  fontSize: "10px",
                  cursor: "pointer",
                }}
              >
                5L
              </button>
              <button
                type="button"
                onClick={() => setLevel("LEVEL_20")}
                style={{
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: level === "LEVEL_20" ? "var(--bg-active)" : "transparent",
                  color: level === "LEVEL_20" ? "var(--color-primary)" : "var(--text-muted)",
                  fontSize: "10px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                20L
              </button>
              <button
                type="button"
                onClick={() => setLevel("LEVEL_200")}
                title="Consumes 1 dedicated depth socket connection"
                style={{
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-subtle)",
                  backgroundColor: level === "LEVEL_200" ? "var(--bg-active)" : "transparent",
                  color: level === "LEVEL_200" ? "var(--color-primary)" : "var(--text-muted)",
                  fontSize: "10px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                200L
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 2. Connection Cost & Segment Limitation Banner */}
      {viewMode === "LADDER" && (
        <div
          style={{
            padding: "4px var(--spacing-2)",
            backgroundColor: "var(--bg-surface)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "11px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
            <span style={{ color: "var(--text-muted)" }}>Socket Allocation:</span>
            <span
              style={{
                padding: "1px 6px",
                borderRadius: "var(--radius-sm)",
                backgroundColor:
                  level === "LEVEL_200" && !depthBook.isFallback
                    ? "rgba(245, 158, 11, 0.15)"
                    : "var(--bg-elevated)",
                color:
                  level === "LEVEL_200" && !depthBook.isFallback
                    ? "#f59e0b"
                    : "var(--text-primary)",
                fontWeight: 600,
              }}
            >
              {depthBook.connectionCost}
            </span>
          </div>

          <div style={{ color: "var(--text-muted)" }}>
            Spread: <strong style={{ color: "var(--text-primary)" }}>₹{depthBook.spread.toFixed(2)}</strong> ({depthBook.spreadPct.toFixed(2)}%)
          </div>
        </div>
      )}

      {/* Segment fallback warning notice */}
      {viewMode === "LADDER" && depthBook.isFallback && (
        <div
          style={{
            padding: "6px var(--spacing-2)",
            backgroundColor: "rgba(245, 158, 11, 0.12)",
            borderBottom: "1px solid rgba(245, 158, 11, 0.3)",
            color: "#f59e0b",
            fontSize: "11px",
            display: "flex",
            alignItems: "center",
            gap: "var(--spacing-1)",
          }}
        >
          <span>⚠️</span>
          <span>
            <strong>5-Level Depth Active:</strong> {depthBook.fallbackReason || "Exchange limitation: Full depth unavailable."}
          </span>
        </div>
      )}

      {/* 3. Main Content Area */}
      {viewMode === "LADDER" ? (
        // Depth Ladder Table
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "right",
              fontSize: "var(--font-size-xs)",
              fontFamily: "var(--font-family-mono)",
            }}
          >
            <thead>
              <tr
                style={{
                  backgroundColor: "var(--bg-elevated)",
                  color: "var(--text-muted)",
                  fontSize: "10px",
                  borderBottom: "1px solid var(--border-subtle)",
                }}
              >
                <th style={{ padding: "4px", textAlign: "left" }}>Orders</th>
                <th style={{ padding: "4px" }}>Cum Qty</th>
                <th style={{ padding: "4px" }}>Bid Qty</th>
                <th style={{ padding: "4px", color: "var(--color-up)" }}>Bid Price</th>
                <th style={{ padding: "4px", color: "var(--color-down)" }}>Ask Price</th>
                <th style={{ padding: "4px" }}>Ask Qty</th>
                <th style={{ padding: "4px" }}>Cum Qty</th>
                <th style={{ padding: "4px", textAlign: "right" }}>Orders</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: Math.max(depthBook.bids.length, depthBook.asks.length) }).map(
                (_, idx) => {
                  const bid = depthBook.bids[idx];
                  const ask = depthBook.asks[idx];
                  const bidBarPct = bid ? (bid.quantity / maxBidQty) * 100 : 0;
                  const askBarPct = ask ? (ask.quantity / maxAskQty) * 100 : 0;

                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                        height: "22px",
                      }}
                    >
                      {/* Bid Side */}
                      <td style={{ padding: "2px 4px", textAlign: "left", opacity: 0.65 }}>
                        {bid?.orders ?? "-"}
                      </td>
                      <td style={{ padding: "2px 4px", opacity: 0.85 }}>
                        {bid?.cumulativeQty?.toLocaleString() ?? "-"}
                      </td>
                      <td
                        style={{
                          padding: "2px 4px",
                          position: "relative",
                          fontWeight: 600,
                        }}
                      >
                        {bid && (
                          <div
                            style={{
                              position: "absolute",
                              right: 0,
                              top: 0,
                              bottom: 0,
                              width: `${bidBarPct}%`,
                              backgroundColor: "var(--color-up-bg)",
                              opacity: 0.4,
                              zIndex: 0,
                            }}
                          />
                        )}
                        <span style={{ position: "relative", zIndex: 1 }}>
                          {bid?.quantity?.toLocaleString() ?? "-"}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "2px 4px",
                          color: "var(--color-up)",
                          fontWeight: 700,
                        }}
                      >
                        {bid?.price?.toFixed(2) ?? "-"}
                      </td>

                      {/* Ask Side */}
                      <td
                        style={{
                          padding: "2px 4px",
                          color: "var(--color-down)",
                          fontWeight: 700,
                        }}
                      >
                        {ask?.price?.toFixed(2) ?? "-"}
                      </td>
                      <td
                        style={{
                          padding: "2px 4px",
                          position: "relative",
                          fontWeight: 600,
                        }}
                      >
                        {ask && (
                          <div
                            style={{
                              position: "absolute",
                              left: 0,
                              top: 0,
                              bottom: 0,
                              width: `${askBarPct}%`,
                              backgroundColor: "var(--color-down-bg)",
                              opacity: 0.4,
                              zIndex: 0,
                            }}
                          />
                        )}
                        <span style={{ position: "relative", zIndex: 1 }}>
                          {ask?.quantity?.toLocaleString() ?? "-"}
                        </span>
                      </td>
                      <td style={{ padding: "2px 4px", opacity: 0.85 }}>
                        {ask?.cumulativeQty?.toLocaleString() ?? "-"}
                      </td>
                      <td style={{ padding: "2px 4px", textAlign: "right", opacity: 0.65 }}>
                        {ask?.orders ?? "-"}
                      </td>
                    </tr>
                  );
                }
              )}
            </tbody>
          </table>
        </div>
      ) : (
        // Depth Watchlist Strip
        <div style={{ flex: 1, overflowY: "auto", padding: "var(--spacing-1)" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "right",
              fontSize: "var(--font-size-xs)",
              fontFamily: "var(--font-family-mono)",
            }}
          >
            <thead>
              <tr
                style={{
                  backgroundColor: "var(--bg-elevated)",
                  color: "var(--text-muted)",
                  fontSize: "10px",
                  borderBottom: "1px solid var(--border-subtle)",
                }}
              >
                <th style={{ padding: "4px", textAlign: "left" }}>Symbol</th>
                <th style={{ padding: "4px" }}>Segment</th>
                <th style={{ padding: "4px", color: "var(--color-up)" }}>Best Bid</th>
                <th style={{ padding: "4px", color: "var(--color-down)" }}>Best Ask</th>
                <th style={{ padding: "4px" }}>Spread</th>
                <th style={{ padding: "4px" }}>Top-5 Imbalance</th>
                <th style={{ padding: "4px" }}>Total Book</th>
                <th style={{ padding: "4px" }}>Depth Level</th>
                <th style={{ padding: "4px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {watchlist.map((item) => (
                <tr
                  key={item.symbol}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                    height: "26px",
                  }}
                >
                  <td style={{ padding: "2px 4px", textAlign: "left", fontWeight: 700 }}>
                    {item.symbol}
                  </td>
                  <td style={{ padding: "2px 4px", opacity: 0.85 }}>{item.segment}</td>
                  <td style={{ padding: "2px 4px", color: "var(--color-up)", fontWeight: 600 }}>
                    {item.bestBid.toFixed(2)}
                  </td>
                  <td style={{ padding: "2px 4px", color: "var(--color-down)", fontWeight: 600 }}>
                    {item.bestAsk.toFixed(2)}
                  </td>
                  <td style={{ padding: "2px 4px" }}>₹{item.spread.toFixed(2)}</td>
                  <td
                    style={{
                      padding: "2px 4px",
                      color:
                        item.top5Imbalance >= 0
                          ? "var(--color-up)"
                          : "var(--color-down)",
                      fontWeight: 600,
                    }}
                  >
                    {item.top5Imbalance >= 0 ? "+" : ""}
                    {(item.top5Imbalance * 100).toFixed(1)}%
                  </td>
                  <td style={{ padding: "2px 4px" }}>
                    {((item.totalBidQty + item.totalAskQty) / 1000).toFixed(1)}k
                  </td>
                  <td style={{ padding: "2px 4px" }}>
                    <span
                      style={{
                        padding: "1px 4px",
                        borderRadius: "2px",
                        backgroundColor: item.isFallback
                          ? "rgba(245, 158, 11, 0.15)"
                          : "var(--bg-elevated)",
                        color: item.isFallback ? "#f59e0b" : "var(--text-primary)",
                        fontSize: "10px",
                        fontWeight: 600,
                      }}
                    >
                      {item.depthLevelType}
                    </span>
                  </td>
                  <td style={{ padding: "2px 4px", textAlign: "center" }}>
                    <button
                      type="button"
                      onClick={() => handleFocusSymbol(item.symbol, item.segment)}
                      style={{
                        padding: "2px 6px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border-subtle)",
                        backgroundColor: "var(--bg-active)",
                        color: "var(--color-primary)",
                        fontSize: "10px",
                        cursor: "pointer",
                      }}
                    >
                      Focus
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. Book Imbalance & Totals Summary Footer */}
      {viewMode === "LADDER" && (
        <div
          style={{
            padding: "var(--spacing-2)",
            backgroundColor: "var(--bg-elevated)",
            borderTop: "1px solid var(--border-subtle)",
            fontSize: "var(--font-size-xs)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "4px",
            }}
          >
            <span style={{ color: "var(--color-up)", fontWeight: 700 }}>
              Total Bids: {depthBook.totalBidQty.toLocaleString()}
            </span>
            <span style={{ fontWeight: 600 }}>
              Imbalance:{" "}
              <strong
                style={{
                  color:
                    depthBook.imbalanceRatio >= 0
                      ? "var(--color-up)"
                      : "var(--color-down)",
                }}
              >
                {depthBook.imbalanceRatio >= 0 ? "+" : ""}
                {(depthBook.imbalanceRatio * 100).toFixed(1)}%
              </strong>
            </span>
            <span style={{ color: "var(--color-down)", fontWeight: 700 }}>
              Total Asks: {depthBook.totalAskQty.toLocaleString()}
            </span>
          </div>

          {/* Imbalance Ratio Bar */}
          <div
            style={{
              height: "6px",
              width: "100%",
              borderRadius: "3px",
              backgroundColor: "var(--bg-input)",
              overflow: "hidden",
              display: "flex",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${
                  (depthBook.totalBidQty /
                    Math.max(1, depthBook.totalBidQty + depthBook.totalAskQty)) *
                  100
                }%`,
                backgroundColor: "var(--color-up)",
              }}
            />
            <div
              style={{
                height: "100%",
                width: `${
                  (depthBook.totalAskQty /
                    Math.max(1, depthBook.totalBidQty + depthBook.totalAskQty)) *
                  100
                }%`,
                backgroundColor: "var(--color-down)",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export const marketDepthDefinition: WidgetDefinition<DepthWidgetSettings> = {
  id: "market-depth",
  title: "Market Depth Ladder & Watchlist",
  description: "20-level standard depth, on-demand 200-level book, and 5-level fallback with connection cost tracking.",
  category: "watchlist",
  icon: "📊",
  defaultWidth: 500,
  defaultHeight: 520,
  schema: {
    fields: [
      {
        name: "defaultSymbol",
        label: "Default Symbol",
        type: "string",
        default: "RELIANCE",
      },
      {
        name: "defaultSegment",
        label: "Default Segment",
        type: "select",
        default: "NSE_EQ",
        options: [
          { label: "NSE Equity", value: "NSE_EQ" },
          { label: "NSE Derivatives", value: "NSE_FNO" },
          { label: "BSE Equity (5-Level)", value: "BSE_EQ" },
          { label: "MCX Commodities (5-Level)", value: "MCX_COMM" },
        ],
      },
      {
        name: "defaultLevel",
        label: "Depth Level",
        type: "select",
        default: "LEVEL_20",
        options: [
          { label: "5-Level", value: "LEVEL_5" },
          { label: "20-Level (Standard)", value: "LEVEL_20" },
          { label: "200-Level (On Demand)", value: "LEVEL_200" },
        ],
      },
      {
        name: "defaultMode",
        label: "Default View",
        type: "select",
        default: "LADDER",
        options: [
          { label: "Depth Ladder", value: "LADDER" },
          { label: "Depth Watchlist", value: "WATCHLIST" },
        ],
      },
    ],
  },
  component: MarketDepthWidget,
};
