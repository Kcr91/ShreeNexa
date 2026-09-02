import React, { useState } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { AlertsLogWidgetSettings, AlertSeverity } from "../../notifications/types";
import { useNotifications } from "../../notifications/NotificationContext";

export const AlertsLogWidget: React.FC<WidgetComponentProps<AlertsLogWidgetSettings>> = ({
  settings,
}) => {
  const {
    notifications,
    unreadCount,
    settings: notifSettings,
    markAsRead,
    markAllAsRead,
    clearAll,
    toggleSound,
    testSound,
    sendNotification,
  } = useNotifications();

  const [activeFilter, setActiveFilter] = useState<"ALL" | "CRITICAL" | "ORDERS" | "RISK">(
    settings.defaultFilter || "ALL"
  );

  const filteredNotifications = notifications.filter((n) => {
    if (activeFilter === "CRITICAL") {
      return n.severity === "CRITICAL" || n.severity === "RISK_BREACH";
    }
    if (activeFilter === "ORDERS") {
      return n.category === "ORDER_FILL" || n.category === "ORDER_REJECT";
    }
    if (activeFilter === "RISK") {
      return n.category === "RISK_BREACH" || n.category === "MARGIN_CALL";
    }
    return true;
  });

  const getSeverityBadge = (severity: AlertSeverity) => {
    switch (severity) {
      case "SUCCESS":
        return { color: "var(--color-up)", bg: "var(--color-up-bg)" };
      case "WARNING":
        return { color: "#faad14", bg: "rgba(250, 173, 20, 0.15)" };
      case "CRITICAL":
      case "RISK_BREACH":
        return { color: "var(--color-down)", bg: "var(--color-down-bg)" };
      case "INFO":
      default:
        return { color: "var(--color-primary)", bg: "var(--bg-active)" };
    }
  };

  const handleSimulateAlert = (type: "FILL" | "REJECT" | "RISK") => {
    if (type === "FILL") {
      sendNotification({
        title: "Order Executed",
        message: "BUY 50 NIFTY 24500 CE filled @ ₹142.50",
        severity: "SUCCESS",
        category: "ORDER_FILL",
      });
    } else if (type === "REJECT") {
      sendNotification({
        title: "Order Rejected",
        message: "MIS Short RELIANCE rejected: Exceeds intraday margin limit",
        severity: "CRITICAL",
        category: "ORDER_REJECT",
      });
    } else {
      sendNotification({
        title: "Risk Limit Breach",
        message: "Max daily account loss threshold (-₹25,000) exceeded. Halting new orders.",
        severity: "RISK_BREACH",
        category: "RISK_BREACH",
      });
    }
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Header Controls Strip */}
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
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <strong>Alerts Log</strong>
          {unreadCount > 0 && (
            <span
              data-testid="unread-alerts-badge"
              style={{
                padding: "2px 6px",
                borderRadius: "10px",
                backgroundColor: "var(--color-primary)",
                color: "var(--text-inverse)",
                fontWeight: 700,
                fontSize: "0.625rem",
              }}
            >
              {unreadCount} NEW
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            data-testid="toggle-sound-btn"
            onClick={toggleSound}
            style={{
              padding: "2px 6px",
              backgroundColor: notifSettings.enableSound ? "var(--bg-active)" : "transparent",
              color: notifSettings.enableSound ? "var(--text-primary)" : "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.6875rem",
              cursor: "pointer",
            }}
          >
            {notifSettings.enableSound ? "🔊 Sound ON" : "🔇 Sound OFF"}
          </button>

          <button
            type="button"
            onClick={() => testSound("ORDER_FILL")}
            style={{
              padding: "2px 6px",
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.6875rem",
              cursor: "pointer",
            }}
          >
            Test Chime
          </button>

          <button
            type="button"
            onClick={markAllAsRead}
            style={{
              padding: "2px 6px",
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.6875rem",
              cursor: "pointer",
            }}
          >
            Mark Read
          </button>

          <button
            type="button"
            onClick={clearAll}
            style={{
              padding: "2px 6px",
              backgroundColor: "transparent",
              color: "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.6875rem",
              cursor: "pointer",
            }}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Filter Tabs & Simulator Strip */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
        <div style={{ display: "flex", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            onClick={() => setActiveFilter("ALL")}
            style={{
              padding: "2px 8px",
              backgroundColor: activeFilter === "ALL" ? "var(--bg-active)" : "transparent",
              color: activeFilter === "ALL" ? "var(--color-primary)" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            All ({notifications.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("CRITICAL")}
            style={{
              padding: "2px 8px",
              backgroundColor: activeFilter === "CRITICAL" ? "var(--bg-active)" : "transparent",
              color: activeFilter === "CRITICAL" ? "var(--color-down)" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Critical
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("ORDERS")}
            style={{
              padding: "2px 8px",
              backgroundColor: activeFilter === "ORDERS" ? "var(--bg-active)" : "transparent",
              color: activeFilter === "ORDERS" ? "var(--color-primary)" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Orders
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("RISK")}
            style={{
              padding: "2px 8px",
              backgroundColor: activeFilter === "RISK" ? "var(--bg-active)" : "transparent",
              color: activeFilter === "RISK" ? "var(--color-down)" : "var(--text-muted)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Risk
          </button>
        </div>

        {/* Quick Simulation Triggers for manual verification */}
        <div style={{ display: "flex", gap: "4px" }}>
          <button
            type="button"
            onClick={() => handleSimulateAlert("FILL")}
            style={{
              padding: "2px 6px",
              backgroundColor: "var(--color-up-bg)",
              color: "var(--color-up)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.625rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Fill
          </button>
          <button
            type="button"
            onClick={() => handleSimulateAlert("RISK")}
            style={{
              padding: "2px 6px",
              backgroundColor: "var(--color-down-bg)",
              color: "var(--color-down)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.625rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Risk Breach
          </button>
        </div>
      </div>

      {/* Audit Log Table */}
      <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.6875rem" }}>
          <thead>
            <tr style={{ backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
              <th style={{ padding: "4px", width: "16px" }}></th>
              <th style={{ padding: "4px", textAlign: "left" }}>Time</th>
              <th style={{ padding: "4px", textAlign: "left" }}>Severity</th>
              <th style={{ padding: "4px", textAlign: "left" }}>Title</th>
              <th style={{ padding: "4px", textAlign: "left" }}>Message</th>
            </tr>
          </thead>
          <tbody>
            {filteredNotifications.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "16px", textAlign: "center", color: "var(--text-muted)" }}>
                  No alerts recorded.
                </td>
              </tr>
            ) : (
              filteredNotifications.map((notif) => {
                const badge = getSeverityBadge(notif.severity);
                return (
                  <tr
                    key={notif.id}
                    data-testid={`alert-row-${notif.id}`}
                    onClick={() => markAsRead(notif.id)}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      backgroundColor: notif.isRead ? "transparent" : "rgba(255, 255, 255, 0.02)",
                      cursor: "pointer",
                    }}
                  >
                    <td style={{ padding: "4px", textAlign: "center" }}>
                      {!notif.isRead && (
                        <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--color-primary)" }} />
                      )}
                    </td>
                    <td style={{ padding: "4px", color: "var(--text-muted)", fontFamily: "var(--font-family-mono)", whiteSpace: "nowrap" }}>
                      {new Date(notif.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: "4px" }}>
                      <span
                        style={{
                          padding: "1px 6px",
                          borderRadius: "3px",
                          backgroundColor: badge.bg,
                          color: badge.color,
                          fontWeight: 700,
                          fontSize: "0.625rem",
                        }}
                      >
                        {notif.severity}
                      </span>
                    </td>
                    <td style={{ padding: "4px", fontWeight: 600, color: "var(--text-primary)" }}>
                      {notif.title}
                    </td>
                    <td style={{ padding: "4px", color: "var(--text-secondary)" }}>
                      {notif.message}
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

export const alertsLogDefinition: WidgetDefinition<AlertsLogWidgetSettings> = {
  id: "alerts-log",
  title: "Alerts & Audit Log",
  description: "Real-time notification manager, risk event alerts, and synthesized sound chime controls.",
  category: "analytics",
  icon: "🔔",
  defaultWidth: 480,
  defaultHeight: 340,
  schema: {
    fields: [
      {
        name: "defaultFilter",
        label: "Default Filter",
        type: "select",
        default: "ALL",
        options: [
          { label: "All Alerts", value: "ALL" },
          { label: "Critical & Risk", value: "CRITICAL" },
          { label: "Order Executions", value: "ORDERS" },
          { label: "Risk Breaches", value: "RISK" },
        ],
      },
      {
        name: "showSoundToggle",
        label: "Show Sound Toggle",
        type: "boolean",
        default: true,
      },
    ],
  },
  component: AlertsLogWidget,
};
