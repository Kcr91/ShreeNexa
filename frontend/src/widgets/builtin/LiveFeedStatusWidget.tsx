import React, { useState, useEffect } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { LiveFeedWidgetSettings, TickData, WebSocketState } from "../../websocket/types";
import { defaultWebSocketClient } from "../../websocket/client";

export const LiveFeedStatusWidget: React.FC<WidgetComponentProps<LiveFeedWidgetSettings>> = ({
  settings,
}) => {
  const [state, setState] = useState<WebSocketState>(defaultWebSocketClient.getState());
  const [latency, setLatency] = useState<number>(defaultWebSocketClient.getLatency());
  const [streamTicks, setStreamTicks] = useState<TickData[]>([]);

  useEffect(() => {
    const unsubState = defaultWebSocketClient.onStateChange((next) => {
      setState(next);
      setLatency(defaultWebSocketClient.getLatency());
    });

    const unsubQuotes = defaultWebSocketClient.onChannel("quotes", (data) => {
      const tick = data as TickData;
      setStreamTicks((prev) => [tick, ...prev.slice(0, (settings.maxStreamHistory || 15) - 1)]);
      setLatency(defaultWebSocketClient.getLatency());
    });

    return () => {
      unsubState();
      unsubQuotes();
    };
  }, [settings.maxStreamHistory]);

  const getStateBadge = () => {
    switch (state) {
      case "CONNECTED":
        return { label: "CONNECTED", color: "var(--color-up)", bg: "var(--color-up-bg)" };
      case "RECONNECTING":
      case "CONNECTING":
        return { label: state, color: "#faad14", bg: "rgba(250, 173, 20, 0.15)" };
      case "ERROR":
        return { label: "ERROR", color: "var(--color-down)", bg: "var(--color-down-bg)" };
      default:
        return { label: "DISCONNECTED", color: "var(--text-muted)", bg: "var(--bg-active)" };
    }
  };

  const badge = getStateBadge();

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Feed Telemetry Strip */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "var(--text-muted)" }}>Feed:</span>
            <span
              data-testid="feed-status-badge"
              style={{
                padding: "2px 8px",
                borderRadius: "4px",
                backgroundColor: badge.bg,
                color: badge.color,
                fontWeight: 700,
              }}
            >
              ● {badge.label}
            </span>
          </div>

          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Latency:</span>
            <strong data-testid="feed-latency-value" style={{ fontFamily: "var(--font-family-mono)", color: "var(--color-primary)" }}>
              {latency}ms
            </strong>
          </div>
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          {state === "CONNECTED" ? (
            <button
              type="button"
              onClick={() => defaultWebSocketClient.simulateDisconnect()}
              style={{
                padding: "2px 8px",
                backgroundColor: "transparent",
                color: "var(--text-muted)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.6875rem",
                cursor: "pointer",
              }}
            >
              Simulate Drop
            </button>
          ) : (
            <button
              type="button"
              onClick={() => defaultWebSocketClient.connect()}
              style={{
                padding: "2px 8px",
                backgroundColor: "var(--color-primary)",
                color: "var(--text-inverse)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.6875rem",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Connect
            </button>
          )}
        </div>
      </div>

      {/* Subscribed Topics Strip */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
          padding: "0 4px",
        }}
      >
        <span>
          Channels:{" "}
          <strong style={{ color: "var(--text-primary)" }}>
            {defaultWebSocketClient.getSubscribedChannels().join(", ")}
          </strong>
        </span>
        <span>
          Symbols:{" "}
          <strong style={{ color: "var(--text-primary)" }}>
            {defaultWebSocketClient.getSubscribedSymbols().join(", ")}
          </strong>
        </span>
      </div>

      {/* Live Tick Streamer Feed */}
      <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.6875rem" }}>
          <thead>
            <tr style={{ backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
              <th style={{ padding: "4px", textAlign: "left" }}>Symbol</th>
              <th style={{ padding: "4px", textAlign: "right" }}>LTP (₹)</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Change (%)</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Volume</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Time</th>
            </tr>
          </thead>
          <tbody>
            {streamTicks.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "12px", textAlign: "center", color: "var(--text-muted)" }}>
                  Waiting for incoming ticks...
                </td>
              </tr>
            ) : (
              streamTicks.map((t, idx) => {
                const isUp = t.change >= 0;
                return (
                  <tr
                    key={`${t.symbol}-${t.timestamp}-${idx}`}
                    data-testid={`stream-tick-${t.symbol}`}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      backgroundColor: idx === 0 ? "rgba(255, 255, 255, 0.02)" : "transparent",
                    }}
                  >
                    <td style={{ padding: "4px", fontWeight: "bold" }}>{t.symbol}</td>
                    <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)", fontWeight: 600 }}>
                      ₹{t.ltp.toLocaleString()}
                    </td>
                    <td
                      style={{
                        padding: "4px",
                        textAlign: "right",
                        fontFamily: "var(--font-family-mono)",
                        color: isUp ? "var(--color-up)" : "var(--color-down)",
                      }}
                    >
                      {isUp ? "+" : ""}
                      {t.changePct}%
                    </td>
                    <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)", color: "var(--text-muted)" }}>
                      {t.volume.toLocaleString()}
                    </td>
                    <td style={{ padding: "4px", textAlign: "right", color: "var(--text-muted)", fontFamily: "var(--font-family-mono)" }}>
                      {new Date(t.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const liveFeedStatusDefinition: WidgetDefinition<LiveFeedWidgetSettings> = {
  id: "live-feed-status",
  title: "Live Feed & Telemetry",
  description: "Real-time WebSocket connection state, latency telemetry, and incoming tick streamer.",
  category: "analytics",
  icon: "📡",
  defaultWidth: 460,
  defaultHeight: 320,
  schema: {
    fields: [
      {
        name: "showTickStream",
        label: "Show Live Tick Stream",
        type: "boolean",
        default: true,
      },
      {
        name: "maxStreamHistory",
        label: "Max Stream Rows",
        type: "number",
        default: 15,
      },
    ],
  },
  component: LiveFeedStatusWidget,
};
