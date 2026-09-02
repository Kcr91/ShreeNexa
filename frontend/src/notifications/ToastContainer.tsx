import React from "react";
import { useNotifications } from "./NotificationContext";
import { AlertSeverity } from "./types";

export const ToastContainer: React.FC = () => {
  const { activeToasts, activeRiskBreaches, dismissToast, dismissRiskBreach } = useNotifications();

  const getSeverityStyle = (severity: AlertSeverity) => {
    switch (severity) {
      case "SUCCESS":
        return {
          border: "1px solid var(--color-up)",
          bg: "var(--bg-surface)",
          icon: "✓",
          color: "var(--color-up)",
        };
      case "WARNING":
        return {
          border: "1px solid #faad14",
          bg: "var(--bg-surface)",
          icon: "⚠️",
          color: "#faad14",
        };
      case "CRITICAL":
        return {
          border: "1px solid var(--color-down)",
          bg: "var(--bg-surface)",
          icon: "❌",
          color: "var(--color-down)",
        };
      case "RISK_BREACH":
        return {
          border: "2px solid var(--color-down)",
          bg: "var(--color-down-bg)",
          icon: "🚨",
          color: "var(--color-down)",
        };
      case "INFO":
      default:
        return {
          border: "1px solid var(--border-default)",
          bg: "var(--bg-surface)",
          icon: "ℹ️",
          color: "var(--color-primary)",
        };
    }
  };

  return (
    <>
      {/* Top Persistent Risk Breach Banner */}
      {activeRiskBreaches.length > 0 && (
        <div
          role="alert"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            backgroundColor: "var(--color-down-bg)",
            borderBottom: "2px solid var(--color-down)",
            color: "var(--color-down)",
            padding: "var(--spacing-2) var(--spacing-4)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            zIndex: 9999,
            fontWeight: 700,
            fontSize: "var(--font-size-xs)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
            <span style={{ fontSize: "1.125rem" }}>🚨</span>
            <span>{activeRiskBreaches[0].title}: {activeRiskBreaches[0].message}</span>
          </div>
          <button
            type="button"
            onClick={() => dismissRiskBreach(activeRiskBreaches[0].id)}
            style={{
              padding: "2px 8px",
              backgroundColor: "var(--color-down)",
              color: "#fff",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.6875rem",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Acknowledge
          </button>
        </div>
      )}

      {/* Floating Bottom-Right Toast Stack */}
      {activeToasts.length > 0 && (
        <div
          aria-live="polite"
          aria-label="Notifications"
          style={{
            position: "fixed",
            bottom: "20px",
            right: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "var(--spacing-2)",
            zIndex: 9998,
            maxWidth: "360px",
            width: "100%",
            pointerEvents: "none",
          }}
        >
          {activeToasts.map((toast) => {
            const style = getSeverityStyle(toast.severity);
            return (
              <div
                key={toast.id}
                data-testid={`toast-${toast.id}`}
                style={{
                  pointerEvents: "auto",
                  backgroundColor: style.bg,
                  border: style.border,
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--spacing-3)",
                  boxShadow: "0 4px 16px rgba(0, 0, 0, 0.4)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "var(--spacing-2)",
                  animation: "slideIn 0.2s ease-out",
                }}
              >
                <div style={{ display: "flex", gap: "var(--spacing-2)", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "1rem" }}>{style.icon}</span>
                  <div>
                    <strong style={{ fontSize: "var(--font-size-xs)", color: style.color, display: "block" }}>
                      {toast.title}
                    </strong>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", display: "block", marginTop: "2px" }}>
                      {toast.message}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  aria-label="Dismiss notification"
                  onClick={() => dismissToast(toast.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    padding: "0 2px",
                  }}
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
};
